import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import numpy as np
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app.pipeline import generate, prepare, validate_file
from app.server import app
import time

def sketch(kind='vase'):
    image=Image.new('RGB',(512,512),'white'); draw=ImageDraw.Draw(image)
    if kind=='vase': draw.polygon([(200,70),(312,70),(296,180),(375,290),(340,430),(172,430),(137,290),(216,180)], outline='black',width=5)
    else: draw.ellipse((120,60,390,450),outline='black',width=5)
    return image

class PipelineTests(unittest.TestCase):
    def test_fresh_sketches_generate_different_closed_volumes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            first=generate(sketch(),root/'a')
            second=generate(sketch('oval'),root/'b',color='#ff3355')
            for folder, report in [(root/'a',first),(root/'b',second)]:
                self.assertGreater(report['validation']['triangles'],100)
                self.assertTrue(report['validation']['watertight'])
                self.assertGreater(min(report['validation']['extents']),.01)
                self.assertIn('vertex',report['validation']['appearance'])
                validate_file(folder/'model.obj')
            self.assertNotEqual((root/'a/model.glb').read_bytes(),(root/'b/model.glb').read_bytes())
            self.assertEqual(first['models'],[])

    def test_empty_rejected_and_transparency_supported(self):
        with self.assertRaises(ValueError): prepare(Image.new('RGB',(200,200),'white'))
        image=Image.new('RGBA',(200,200),(0,0,0,0))
        ImageDraw.Draw(image).ellipse((30,30,170,170),outline='black',width=5)
        _, mask=prepare(image)
        self.assertGreater(mask.sum(),100)

    def test_api_run_download_and_invalid_upload(self):
        with TestClient(app) as client:
            bad=client.post('/api/jobs',files={'image':('x.png',b'not an image','image/png')})
            self.assertEqual(bad.status_code,422)
            self.assertEqual(client.get('/api/jobs/not-a-job').status_code,404)
            buf=io.BytesIO();sketch().save(buf,format='PNG')
            response=client.post('/api/jobs',files={'image':('fresh.png',buf.getvalue(),'image/png')})
            self.assertEqual(response.status_code,202)
            job=response.json()['id']
            for _ in range(200):
                data=client.get('/api/jobs/'+job).json()
                if data['status'] in ('complete','failed'):break
                time.sleep(.1)
            self.assertEqual(data['status'],'complete',data)
            self.assertEqual(client.get(f'/api/jobs/{job}/files/model.glb').content[:4],b'glTF')
            bundle=client.get(f'/api/jobs/{job}/bundle')
            with zipfile.ZipFile(io.BytesIO(bundle.content)) as z:
                self.assertIn('report.json',z.namelist())
                self.assertIn('input.png',z.namelist())
            self.assertEqual(client.get('/').status_code,200)
            self.assertEqual(client.get('/vendor/model-viewer.min.js').status_code,200)

if __name__=='__main__': unittest.main()
