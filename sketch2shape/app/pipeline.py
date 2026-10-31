"""Sketch preprocessing, genuine volumetric reconstruction, AI adapter, and validation."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time

import numpy as np
from PIL import Image, ImageOps, ImageFilter
from scipy import ndimage as ndi
from skimage.measure import marching_cubes
import trimesh

ROOT = Path(__file__).resolve().parents[1]

def prepare(image: Image.Image, size: int = 192):
    image = ImageOps.exif_transpose(image).convert('RGBA')
    background = Image.new('RGBA', image.size, 'white')
    background.alpha_composite(image)
    image = ImageOps.contain(background.convert('RGB'), (1024, 1024))
    gray = np.asarray(ImageOps.grayscale(image))
    # Accommodate white strokes on a dark canvas.
    border = np.concatenate([gray[0], gray[-1], gray[:, 0], gray[:, -1]])
    if np.median(border) < 100:
        image = ImageOps.invert(image)
        gray = 255 - gray
    strokes = gray < 190
    if strokes.sum() < 12:
        raise ValueError('The sketch is empty. Draw a dark, closed outline on a light background.')
    y, x = np.where(strokes)
    crop = image.crop((max(0, x.min()-8), max(0, y.min()-8), min(image.width, x.max()+9), min(image.height, y.max()+9)))
    square = Image.new('RGB', (512, 512), 'white')
    crop.thumbnail((420, 420), Image.Resampling.LANCZOS)
    square.paste(crop, ((512-crop.width)//2, (512-crop.height)//2))
    small = np.asarray(square.resize((size, size)).convert('L'))
    ink = small < 190
    closed = ndi.binary_closing(ink, iterations=2)
    filled = ndi.binary_fill_holes(closed)
    # Open strokes remain as tubes, never substitute a library object.
    mask = ndi.binary_dilation(filled, iterations=1)
    labels, count = ndi.label(mask)
    if count:
        areas = np.bincount(labels.ravel()); areas[0] = 0
        keep = np.flatnonzero(areas >= max(6, areas.max() * .003))
        mask = np.isin(labels, keep)
    if mask.sum() < 16:
        raise ValueError('Too little sketch content after cleanup. Use a larger outline.')
    return square, mask

def cpu_mesh(mask, color, depth):
    """Rounded solid with local thickness inferred from distance to outline."""
    distance = ndi.distance_transform_edt(mask)
    radius = np.sqrt(distance / max(1, distance.max())) * (mask.shape[0] * depth / 2)
    z = np.linspace(-mask.shape[0]*depth/2-3, mask.shape[0]*depth/2+3, 64)
    field = radius[:, :, None] - np.abs(z)[None, None, :]
    field[~mask, :] = -2
    field = ndi.gaussian_filter(field.astype(np.float32), .7)
    vertices, faces, _, _ = marching_cubes(field, level=0, spacing=(1, 1, float(z[1]-z[0])))
    # Image row -> world up; depth -> world Z.
    vertices = vertices[:, [1, 0, 2]]
    vertices[:, 1] *= -1
    vertices -= (vertices.max(0) + vertices.min(0)) / 2
    vertices *= 2 / np.ptp(vertices, axis=0).max()
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    trimesh.repair.fix_normals(mesh)
    rgb = np.array([int(color[i:i+2], 16) for i in (1, 3, 5)])
    mesh.visual.vertex_colors = np.tile(np.r_[rgb, 255], (len(vertices), 1))
    return mesh

def ai_config():
    repo = os.getenv('TRIPOSR_DIR', '')
    python = os.getenv('AI_PYTHON', '')
    return {'available': bool(repo and python and (Path(repo) / 'run.py').is_file() and Path(python).is_file()),
            'reason': 'Set TRIPOSR_DIR and AI_PYTHON to an installed TripoSR checkout and Python executable.'}

def run_command(command, log):
    # No shell expansion; all user input is passed as literal arguments.
    with log.open('w', encoding='utf-8') as out:
        try:
            completed = subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, timeout=1800, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('AI stage exceeded 30 minutes. Inspect the job log and reduce resolution.') from exc
    if completed.returncode:
        raise RuntimeError(f'AI stage failed. Inspect {log.name} in the downloaded job bundle.')

def validate_file(path):
    scene = trimesh.load(path, force='scene')
    meshes = list(scene.geometry.values())
    if not meshes or not sum(len(m.faces) for m in meshes):
        raise ValueError('Export contains no triangle geometry.')
    if any(not np.isfinite(m.vertices).all() for m in meshes):
        raise ValueError('Export has non-finite vertex coordinates.')
    extents = np.ptp(np.vstack([m.vertices for m in meshes]), axis=0)
    if np.min(extents) < 1e-5:
        raise ValueError('Export is flat; a volumetric model is required.')
    return {'vertices': sum(len(m.vertices) for m in meshes), 'triangles': sum(len(m.faces) for m in meshes),
            'extents': extents.tolist(), 'watertight': all(m.is_watertight for m in meshes),
            'appearance': [m.visual.kind for m in meshes]}

def generate(image, folder: Path, mode='cpu', prompt='', color='#77b8ee', depth=.45, seed=42, update=lambda *x: None):
    if mode not in ('cpu', 'ai'):
        raise ValueError('Unknown generation mode.')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Color must be a six-digit hex color.')
    if not .1 <= depth <= 1.0:
        raise ValueError('Depth must be between 0.1 and 1.0.')
    folder.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter(); times = {}
    image.save(folder / 'input.png')
    update('preparing', 'Cleaning and normalizing the sketch')
    normalized, mask = prepare(image)
    normalized.save(folder / 'prepared.png')
    Image.fromarray(mask.astype('uint8') * 255).save(folder / 'silhouette.png')
    times['preprocess_seconds'] = time.perf_counter() - start
    stage = time.perf_counter()
    if mode == 'ai':
        if not ai_config()['available']:
            raise ValueError(ai_config()['reason'])
        update('refining', 'ControlNet is interpreting the sketch; first use downloads model weights')
        run_command([os.environ['AI_PYTHON'], str(ROOT/'app'/'refine.py'), '--input', str(folder/'prepared.png'),
                     '--output', str(folder/'refined.png'), '--prompt', prompt, '--seed', str(seed)], folder/'controlnet.log')
        times['refinement_seconds'] = time.perf_counter()-stage; stage = time.perf_counter()
        update('reconstructing', 'TripoSR is reconstructing geometry and surface colors')
        run_command([os.environ['AI_PYTHON'], str(Path(os.environ['TRIPOSR_DIR'])/'run.py'),
                     str(folder/'refined.png'), '--output-dir', str(folder/'triposr'),
                     '--model-save-format', 'glb', '--mc-resolution', '256', '--device', os.getenv('AI_DEVICE','cuda:0')], folder/'triposr.log')
        generated = folder/'triposr'/'0'/'mesh.glb'
        if not generated.is_file():
            raise RuntimeError('TripoSR did not produce the expected mesh.glb.')
        mesh = trimesh.load(generated, force='scene')
    else:
        update('reconstructing', 'Inferring a rounded volume from the actual sketch silhouette')
        mesh = cpu_mesh(mask, color, depth)
    times['reconstruction_seconds'] = time.perf_counter()-stage
    update('validating', 'Exporting and reopening GLB and OBJ to check geometry')
    mesh.export(folder/'model.glb')
    # OBJ is geometry-only; GLB is the authoritative appearance-preserving deliverable.
    obj_mesh = mesh.to_geometry() if isinstance(mesh, trimesh.Scene) else mesh
    obj_mesh.export(folder/'model.obj', include_color=False, include_texture=False)
    validation = validate_file(folder/'model.glb')
    validate_file(folder/'model.obj')
    times['total_seconds'] = time.perf_counter()-start
    report = {'mode': mode, 'prompt': prompt, 'seed': seed, 'color': color, 'depth': depth,
              'timings': times, 'validation': validation,
              'input_sha256': hashlib.sha256((folder/'input.png').read_bytes()).hexdigest(),
              'hardware': {'platform': platform.platform(), 'processor': platform.processor(), 'cpu_count': os.cpu_count()},
              'models': ['stable-diffusion-v1-5/stable-diffusion-v1-5', 'lllyasviel/control_v11p_sd15_scribble', 'stabilityai/TripoSR'] if mode == 'ai' else [],
              'limitations': 'AI unseen surfaces are inferred. CPU mode is silhouette inflation, not generative AI; prompt semantics are not interpreted in CPU mode. OBJ export is geometry-only; use GLB for appearance.'}
    (folder/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
