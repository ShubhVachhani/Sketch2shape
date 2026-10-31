# Problem statement coverage

| Requirement | Implementation / evidence |
| --- | --- |
| In-app sketching | Brush, eraser, undo, reset, pointer/touch canvas |
| Upload | PNG, JPEG, WebP, decoded content validation |
| Optional text | Both modes run without user text; AI uses a generic default |
| Preprocessing | Orientation, transparency, normalization, cropping, dark background, cleanup |
| Computer vision | Stroke extraction, morphology, silhouette distance field |
| Generative AI | ControlNet scribble-conditioned image generation, integrated but not locally executed |
| Preserve input | CPU directly reconstructs mask; AI always conditions on sketch, not text alone |
| Foreground preparation | TripoSR upstream rembg preprocessing |
| Reconstruction | CPU marching cubes baseline; official TripoSR AI adapter |
| Actual 3D | Positive extents in every axis; nonempty triangle mesh, no flat image plane |
| Appearance | Vertex-colored GLB; AI reconstructs colors from image |
| Preview | Bundled model-viewer, orbit, zoom, automatic rotation |
| Export | GLB with appearance, OBJ geometry-only |
| Validation | Reopen exports, check finite vertices, faces, extents; report watertightness |
| Source / setup | README, pinned app requirements, separate AI instructions |
| Timing / hardware | Per-run report plus measured local verification |
| Output artifact | Included CPU sample GLB/OBJ and input; AI example still requires GPU execution |
| Fresh judge input | Upload/draw routes execute reconstruction for every new job |
| Model disclosure | README model IDs, licenses, external repositories |
| Reproducibility | CPU tested here; full AI environment needs installation, validation and lock capture |

The brief has inconsistent wording around whether one input method is sufficient. Both drawing and upload are implemented. The project must not be described as fully verified against the AI requirements until a successful AI run is produced.
