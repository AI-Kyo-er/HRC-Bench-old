"""Small deterministic scene assets; generated meshes live on the project data disk."""
from pathlib import Path
import numpy as np


def mug_mesh(asset_directory: Path) -> Path:
    import trimesh
    destination = asset_directory / "pilot/mug.obj"
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    wall = trimesh.creation.annulus(r_min=0.028, r_max=0.035, height=0.105, sections=48)
    bottom = trimesh.creation.cylinder(radius=0.028, height=0.007, sections=48)
    bottom.apply_translation([0, 0, -0.049])
    vertices, faces = [], []
    ring_steps, tube_steps = 40, 10
    for i in range(ring_steps):
        theta = 2 * np.pi * i / ring_steps
        for j in range(tube_steps):
            phi = 2 * np.pi * j / tube_steps
            radial = 0.027 + 0.005 * np.cos(phi)
            vertices.append([0.043 + radial * np.cos(theta), 0.005 * np.sin(phi), radial * np.sin(theta)])
    for i in range(ring_steps):
        for j in range(tube_steps):
            a = i * tube_steps + j
            b = ((i + 1) % ring_steps) * tube_steps + j
            c = ((i + 1) % ring_steps) * tube_steps + (j + 1) % tube_steps
            d = i * tube_steps + (j + 1) % tube_steps
            faces.extend([[a, b, c], [a, c, d]])
    handle = trimesh.Trimesh(vertices=vertices, faces=faces)
    trimesh.util.concatenate([wall, bottom, handle]).export(destination)
    return destination
