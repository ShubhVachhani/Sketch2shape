"""Run in the separate AI Python environment to avoid TripoSR dependency conflicts."""
import argparse
import gc
import os
import torch
from PIL import Image, ImageOps
from diffusers import ControlNetModel, StableDiffusionControlNetPipeline, UniPCMultistepScheduler

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True); p.add_argument('--output', required=True)
    p.add_argument('--prompt', default=''); p.add_argument('--seed', type=int, default=42)
    a = p.parse_args()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    dtype = torch.float16 if device == 'cuda' else torch.float32
    controlnet = ControlNetModel.from_pretrained('lllyasviel/control_v11p_sd15_scribble', torch_dtype=dtype)
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        'stable-diffusion-v1-5/stable-diffusion-v1-5', controlnet=controlnet, torch_dtype=dtype)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.enable_attention_slicing()
    if device == 'cuda':
        pipe.enable_model_cpu_offload()
    else:
        pipe.to('cpu')
    # Scribble ControlNet expects bright strokes on black, unlike the input canvas.
    condition = ImageOps.invert(Image.open(a.input).convert('L')).point(lambda x: 255 if x > 65 else 0).convert('RGB')
    result = pipe(prompt=('A single object matching this sketch, ' + (a.prompt or 'a plausible solid object') +
                          ', product photograph, isolated on plain white background, complete object, centered'),
                  negative_prompt='multiple objects, cropped, text, watermark, cluttered background',
                  image=condition, num_inference_steps=30, controlnet_conditioning_scale=1.15,
                  guidance_scale=7.5, generator=torch.Generator(device='cpu').manual_seed(a.seed))
    if result.nsfw_content_detected and any(result.nsfw_content_detected):
        raise RuntimeError('Image generation was filtered. Revise the sketch or prompt.')
    result.images[0].save(a.output)
    del pipe; gc.collect()
    if device == 'cuda': torch.cuda.empty_cache()

if __name__ == '__main__': main()
