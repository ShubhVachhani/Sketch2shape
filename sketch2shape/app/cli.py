import argparse
import json
from pathlib import Path
from PIL import Image
from .pipeline import generate

def main():
    p = argparse.ArgumentParser(description='Generate actual 3D geometry from a sketch.')
    p.add_argument('image', type=Path); p.add_argument('--output', type=Path, default=Path('runs/cli'))
    p.add_argument('--mode', choices=['cpu','ai'], default='cpu'); p.add_argument('--prompt', default='')
    p.add_argument('--color', default='#77b8ee'); p.add_argument('--depth', type=float, default=.45)
    p.add_argument('--seed', type=int, default=42)
    args = p.parse_args()
    # Do not overwrite prior experiment results.
    if args.output.exists() and any(args.output.iterdir()): p.error('Output directory must be empty or new.')
    with Image.open(args.image) as image:
        report = generate(image, args.output.resolve(), mode=args.mode, prompt=args.prompt,
                          color=args.color, depth=args.depth, seed=args.seed,
                          update=lambda s,m: print(f'[{s}] {m}', flush=True))
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
