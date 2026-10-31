# Sample sketch library

Choose a sketch from the selector beside **Load sample** in the app. The PNG inputs are also in this folder: vase, bottle, mug, mushroom, rocket, fish, lamp, chair and house.

These are original, synthetic line-art inputs, not generated 3D results or a training dataset. They are supplied for manual exploration and demonstrations. CPU mode inflates silhouettes and cannot understand structural holes, perspective or functional interiors. Chair, house and mug sketches illustrate these limitations; use the configured AI mode for semantic reconstruction and assess its output independently.

Run `python examples/create_samples.py` from the project root to recreate the eight added sketches and copy all nine into the local app. The existing vase remains the original reference fixture.
