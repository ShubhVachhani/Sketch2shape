# Verification — 31 October 2026

## Actually executed

- Windows 11, Intel64 Family 6 Model 142 Stepping 12 processor, 8 logical CPUs, Python 3.13.2.
- PyTorch 2.12.1+cpu; CUDA unavailable. No GPU AI run performed.
- Three automated tests passed in 7.357 seconds. They exercised two fresh geometry cases, export reopening, vertex appearance, 3D extents and closed surfaces; transparent input and empty-sketch rejection; API upload, asynchronous completion, invalid input, GLB download, run bundle, static app and viewer asset delivery.
- JavaScript syntax check passed.
- Local Uvicorn HTTP server started successfully at 127.0.0.1:8000.
- Browser sample generation completed with 97,744 triangles in 2.4 seconds. The colored volume rendered in the embedded viewer. Download links and intermediate images appeared.
- Included CLI sample: 43,834 vertices, 87,664 triangles, watertight, nonzero 3D extents, vertex colors. Measured total pipeline time 1.685 seconds, excluding Python startup. See `examples/cpu-vase/report.json`.

The application requirements reflect the package versions used in these local checks. Tests used existing host packages and additional dependencies placed in a workspace dependency directory; a fresh virtual environment installation has not been independently tested. Model-viewer 4.1.0 is bundled locally.

## Remaining verification

The ControlNet and TripoSR stages are implemented using the documented interfaces. Their model downloads, native dependency compilation, inference, runtime, GPU memory use, geometric fidelity and texture/color quality have **not** been verified on this machine. AI setup and an actual successful AI run remain necessary before claiming all generative-AI requirements are demonstrated. AI requirements are pinned for the image refinement stage; upstream TripoSR dependencies still require a lock captured in the successful GPU environment.

No manufacturing, architectural, animation-topology or exact-hidden-surface guarantees are made. The CPU model is a silhouette-derived symmetric volume, not a semantic reconstruction or AI-generated artifact.
