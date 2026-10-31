from __future__ import annotations
import io
import json
import os
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid
import zipfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from .pipeline import generate, ai_config

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv('S2S_DATA_DIR', str(ROOT/'runs'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='Sketch2Shape AI', version='1.0.0')
executor = ThreadPoolExecutor(max_workers=1)
lock = threading.Lock()
jobs = {}
Image.MAX_IMAGE_PIXELS = 20_000_000

def status_path(job): return DATA/job/'status.json'
def set_status(job, **values):
    with lock:
        jobs[job].update(values)
        path = status_path(job)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(jobs[job]), encoding='utf-8')
        temp.replace(path)

def work(job, image, options):
    try:
        report = generate(image, DATA/job, update=lambda stage, message: set_status(job, status=stage, message=message), **options)
        set_status(job, status='complete', message='Your model is ready', report=report)
    except Exception as exc:
        set_status(job, status='failed', message=str(exc))

@app.get('/api/config')
def config():
    return {'ai': ai_config(), 'max_upload_mb': 10, 'modes': ['cpu','ai']}

@app.post('/api/jobs', status_code=202)
async def create_job(image: UploadFile = File(...), mode: str = Form('cpu'), prompt: str = Form(''),
                     color: str = Form('#77b8ee'), depth: float = Form(.45), seed: int = Form(42)):
    if mode not in ('cpu','ai') or len(prompt) > 1000 or not .1 <= depth <= 1 or not 0 <= seed <= 2147483647:
        raise HTTPException(422, 'Invalid mode, prompt, depth, or seed.')
    import re
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', color): raise HTTPException(422, 'Invalid color.')
    if mode == 'ai' and not ai_config()['available']: raise HTTPException(422, ai_config()['reason'])
    content = await image.read(10*1024*1024+1)
    if len(content) > 10*1024*1024: raise HTTPException(413, 'Image must be smaller than 10 MB.')
    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in ('PNG','JPEG','WEBP'): raise ValueError('Use PNG, JPEG, or WebP.')
            if source.width*source.height > 20_000_000: raise ValueError('Image exceeds 20 megapixels.')
            source.load(); decoded = source.convert('RGBA')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, f'Cannot read sketch: {exc}') from exc
    with lock:
        if sum(j['status'] not in ('complete','failed') for j in jobs.values()) >= 3:
            raise HTTPException(429, 'The local queue is full. Wait for a model to finish.')
        job = uuid.uuid4().hex
        (DATA/job).mkdir()
        jobs[job] = {'id': job, 'status': 'queued', 'message': 'Waiting for the generation worker'}
    set_status(job)
    executor.submit(work, job, decoded, dict(mode=mode, prompt=prompt, color=color, depth=depth, seed=seed))
    return {'id': job}

def folder_for(job):
    if len(job) != 32 or any(c not in '0123456789abcdef' for c in job): raise HTTPException(404)
    folder = DATA/job
    if not folder.is_dir(): raise HTTPException(404)
    return folder

@app.get('/api/jobs/{job}')
def get_job(job: str):
    folder = folder_for(job)
    with lock:
        if job in jobs: return dict(jobs[job])
    path = folder/'status.json'
    if not path.is_file(): raise HTTPException(404)
    saved = json.loads(path.read_text(encoding='utf-8'))
    if saved['status'] not in ('complete','failed'):
        saved.update(status='failed', message='Server restarted during this job. Please generate again.')
    return saved

@app.get('/api/jobs/{job}/files/{name}')
def file(job: str, name: str):
    folder = folder_for(job)
    if name not in {'model.glb','model.obj','input.png','prepared.png','silhouette.png','refined.png','report.json'}:
        raise HTTPException(404)
    path = folder/name
    if not path.is_file(): raise HTTPException(404)
    return FileResponse(path, filename=name, media_type='model/gltf-binary' if name.endswith('.glb') else None)

@app.get('/api/jobs/{job}/bundle')
def bundle(job: str):
    folder = folder_for(job)
    if get_job(job)['status'] not in ('complete','failed'): raise HTTPException(409, 'Job still running.')
    target = folder/'result.zip'
    with lock:
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in folder.rglob('*'):
                if path.is_file() and path != target: archive.write(path, path.relative_to(folder))
    return FileResponse(target, filename=f'sketch2shape-{job[:8]}.zip')

app.mount('/', StaticFiles(directory=ROOT/'app'/'static', html=True), name='frontend')
