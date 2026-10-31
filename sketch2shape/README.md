# Sketch2Shape AI

A local, end-to-end sketch-to-3D application for TechZephyr 4.0, IIT Bhubaneswar.
Draw or upload a sketch, generate actual 3D geometry, orbit the result, and export GLB or OBJ.

## What is implemented

- Brush, eraser, undo, canvas reset, PNG/JPEG/WebP upload, nine selectable sample sketches.
- Optional text prompt; no user text is required for either pipeline.
- EXIF correction, alpha compositing, dark-background handling, content cropping, normalization, contour cleanup.
- **AI mode:** scribble-conditioned Stable Diffusion → TripoSR background isolation and image-to-3D → colored GLB.
- **CPU mode:** distance-field silhouette inflation → marching cubes → colored GLB. This is a genuine volumetric baseline, **not generative AI**. It does not semantically interpret the prompt or recover hidden details.
- Interactive local 3D viewer, GLB and OBJ download, intermediate images, job logs and JSON run report.
- Export validation reopens both formats and checks finite vertices, nonempty faces and nonzero extent in all three axes. Watertightness is reported rather than assumed.
- One inference worker with a bounded queue, upload limits, readable errors, persisted job reports, CLI, and integration tests.

**Verification status:** The included sample and local end-to-end tests exercise CPU reconstruction. AI code is integrated against the official APIs, but has not been executed here: this build machine has CPU-only PyTorch and no installed model weights. Do not present the sample as an AI result. To fulfill the generative AI portion of the brief in your final demonstration, install the AI environment, enable AI mode, and generate and submit an AI run bundle. See `docs/VERIFICATION.md` for measured results.

## Quick start — Windows

Install Python 3.11 (recommended; CPU code also works on 3.13). Open PowerShell in this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Or run `./start.ps1` to create the environment and launch it. If script execution is restricted, use the explicit Python commands above. No API keys are needed. The server binds to this computer only; it has no authentication and is intended for local use.

## Quick start — Linux/macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

CPU reconstruction and the bundled viewer work offline after dependency installation. Runs are stored under `runs/`; remove old runs manually when no longer needed. The app retains your sketches locally. A server restart marks interrupted jobs as failed; generate them again.

## Full AI environment

Use a **separate Python 3.10/3.11 environment**, Git, a compatible NVIDIA CUDA installation and C++ build tools for TripoSR native dependencies. Linux with an NVIDIA GPU is the easiest supported path. Upstream TripoSR reports approximately 6 GB VRAM for its default settings; ControlNet also consumes GPU and system memory. Allow at least 8–12 GB VRAM and 16 GB RAM as a planning target, not a benchmark guarantee. The two stages run in separate processes so GPU memory is released between them. Reserve disk space for several GB of downloaded weights and Python packages. CPU AI execution may be extremely slow.

From the project directory (Linux example):

```bash
python3.11 -m venv .ai-venv
# Install the CUDA-enabled PyTorch build appropriate to your machine first:
# https://pytorch.org/get-started/locally/
git clone https://github.com/VAST-AI-Research/TripoSR.git vendor/TripoSR
.ai-venv/bin/python -m pip install --upgrade pip setuptools wheel
.ai-venv/bin/python -m pip install -r vendor/TripoSR/requirements.txt
.ai-venv/bin/python -m pip install -r requirements-ai.txt
.ai-venv/bin/python -m pip check
export TRIPOSR_DIR="$PWD/vendor/TripoSR"
export AI_PYTHON="$PWD/.ai-venv/bin/python"
.venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

On Windows, use `.ai-venv\Scripts\python.exe` and set environment variables in the same PowerShell window before starting the server:

```powershell
$env:TRIPOSR_DIR = (Resolve-Path vendor/TripoSR).Path
$env:AI_PYTHON = (Resolve-Path .ai-venv/Scripts/python.exe).Path
```

The upstream TripoSR checkout needs to be installed, not just cloned. Its `torchmcubes` compilation requires a compiler/CUDA toolchain compatible with PyTorch. Upstream requirements are not fully pinned; record `git -C vendor/TripoSR rev-parse HEAD` and `pip freeze` in your final submission after a successful AI run. The pinned application dependencies do not make the untested upstream AI environment a guaranteed reproducible installation.

The UI enables AI mode when both configured paths exist. This is a configuration check, not proof that model dependencies or CUDA work. First AI generation automatically downloads Hugging Face weights. If the model hub requests access, accept the model terms and authenticate with the Hugging Face CLI in the AI environment. No secret is included in this project. Optional `HF_TOKEN` follows Hugging Face's standard environment support; never commit it.

Models:

| Component | Model / implementation | Role |
| --- | --- | --- |
| Visual generation | `stable-diffusion-v1-5/stable-diffusion-v1-5` | Refined product-style image |
| Sketch conditioning | `lllyasviel/control_v11p_sd15_scribble` | Preserve stroke structure (white strokes on black) |
| Reconstruction | `stabilityai/TripoSR`, official repository | Geometry, foreground removal, vertex colors |

No remote inference API or paid external service is used. AI model downloads require internet; subsequent execution uses the local Hugging Face cache. ControlNet uses a fixed default description when text is empty. The UI color and depth controls affect CPU mode; describe color/material in the prompt for AI mode. Each job has a seed, but cross-device bit-for-bit reproducibility is not guaranteed.

## Command-line generation

```powershell
.\.venv\Scripts\python.exe -m app.cli examples/vase-sketch.png --output runs/my-vase --color '#77b8ee'
.\.venv\Scripts\python.exe -m app.cli examples/vase-sketch.png --mode ai --prompt 'a blue glazed ceramic vase' --output runs/my-ai-vase
```

Use a new/empty output directory. Each successful run contains:

| File | Purpose |
| --- | --- |
| `input.png` | Actual user input |
| `prepared.png` | Cropped, centered sketch |
| `silhouette.png` | Baseline foreground mask |
| `refined.png` | AI representation, AI runs only |
| `model.glb` | Geometry and vertex colors; preferred deliverable |
| `model.obj` | Geometry-only secondary export |
| `report.json` | Timing, hardware, input hash, options, models, validation |
| `controlnet.log`, `triposr.log` | AI subprocess diagnostics |

GLB uses per-vertex surface color rather than a UV texture atlas. This provides surface appearance while keeping the export self-contained. OBJ deliberately omits appearance; use GLB to preserve it. Models are normalized arbitrary units, without manufacturing scale or guaranteed printable topology.

## Architecture

```text
Browser drawing/upload + optional text
  → FastAPI validation and bounded job queue
  → input cleanup and normalization
  → CPU: silhouette distance field → marching cubes
    OR AI: ControlNet → foreground isolation + TripoSR
  → GLB + OBJ export → reopen and validate
  → interactive model viewer + downloadable run bundle
```

`app/pipeline.py` owns reconstruction and export; `app/refine.py` runs image generation in the AI environment; `app/server.py` provides jobs and downloads; `app/cli.py` offers the same pipeline without a browser. Each AI subprocess has a 30-minute timeout. Job state is process-local with status snapshots on disk; run one Uvicorn worker. Do not use `--workers` greater than one.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r tests/requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests generate fresh, different sketches, validate exported 3D geometry and appearance, handle transparent and empty inputs, and exercise upload → job completion → GLB → downloadable bundle. They do not download or test AI model weights.

## Limitations and troubleshooting

- CPU mode fills closed outlines and inflates them symmetrically. Open strokes become rounded tubes; overlapping contours may merge. It cannot infer chair legs, object categories or unseen surfaces semantically. Use AI mode for the judged generative pipeline.
- AI fidelity is approximate: unusual sketches, thin structures, multiple objects and perspective ambiguity can produce artifacts. A prompt can guide appearance but does not guarantee a match.
- Missing preview: ensure `app/static/vendor/model-viewer.min.js` is present. The viewer is bundled and uses no CDN. Download the GLB and inspect in Blender if browser WebGL is unavailable.
- AI is disabled: verify both absolute environment paths and restart the server.
- AI fails: download the run bundle and inspect the stage logs. Check CUDA compatibility, model access, `pip check`, available RAM/VRAM, and upstream torchmcubes setup.
- Out of memory: close other GPU programs; consider reducing TripoSR `--mc-resolution` in `app/pipeline.py` from 256 to 128. This trades detail for resource use. Lower ControlNet steps in `app/refine.py` for time, although this alone will not resolve every memory issue.
- Empty sketch: use dark strokes on a plain background, make the outline larger, and close the contour.
- 3D printing and production topology: not guaranteed. Watertightness alone does not establish printability, physical scale or structural soundness.

## Submission

See `docs/REQUIREMENTS.md` for requirement mapping and `docs/DEMO.md` for the live demonstration checklist. Include an AI-generated run bundle after you have run the full AI pipeline; the included CPU model proves geometry and app operation but does not prove generative AI execution. Include your final hardware, measured timings, model versions, upstream commit, and dependency lock in that submission.

## Attribution

- [Official TripoSR repository](https://github.com/VAST-AI-Research/TripoSR): MIT source and pretrained model, per upstream README.
- [Diffusers ControlNet documentation](https://huggingface.co/docs/diffusers/en/api/pipelines/controlnet) and [ControlNet weights](https://huggingface.co/lllyasviel/control_v11p_sd15_scribble): review their licenses and model cards.
- [Stable Diffusion v1.5 model card](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5): CreativeML OpenRAIL-M model terms; comply with its use restrictions.
- [Google model-viewer](https://github.com/google/model-viewer), version 4.1.0: Apache-2.0, bundled under `app/static/vendor/` with its license; compiled distribution includes third-party code.
- FastAPI, Uvicorn, Pillow, NumPy, SciPy, scikit-image and trimesh are third-party dependencies under their respective licenses. Model weights are not redistributed.

Original application code is provided under the MIT license in `LICENSE`.
