# Demonstration and submission

1. Start the server and open the local app.
2. Explain the pipeline: sketch → ControlNet refinement → foreground removal → TripoSR → validated exports.
3. Select AI mode on the configured GPU machine. Draw or upload a fresh judge-supplied sketch.
4. Leave the prompt empty for one run to demonstrate that text is optional.
5. Generate and show the original sketch, normalized image, refinement and resulting model.
6. Orbit the model to show actual depth, inspect its shape and surface colors.
7. Download GLB and open it in Blender or another independent 3D viewer.
8. Download the run bundle and show timings, hardware, disclosed models and validation.
9. Explain single-view ambiguity, hardware needs, approximation and any artifacts honestly.
10. Submit source, README, dependency versions, model access information, one AI sample input and exported output, run report, and the actual upstream TripoSR commit.

Use CPU mode to demonstrate offline geometric reconstruction or diagnose the interface. Identify it explicitly as a non-AI baseline. Never substitute the included CPU sample for a live AI run.
