"""Non-destructive filtering of standard 3D Gaussian Splat PLY files."""
from pathlib import Path
import numpy as np
from plyfile import PlyData, PlyElement


def cleanup(source, destination, min_opacity=0.05, max_axis=0.0,
            max_anisotropy=0.0, crop_center=(0, 0, 0), crop_half_size=(0, 0, 0)):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Output must differ from original PLY")
    ply = PlyData.read(str(source))
    if "vertex" not in ply:
        raise ValueError("PLY lacks vertex element")
    vertex = ply["vertex"].data
    names = set(vertex.dtype.names or [])
    required = {"x", "y", "z", "opacity", "scale_0", "scale_1", "scale_2"}
    if not required.issubset(names):
        raise ValueError(f"Expected Gaussian-splat PLY fields, missing {required - names}")
    xyz = np.column_stack([vertex[n] for n in ("x", "y", "z")])
    scales_log = np.column_stack([vertex[f"scale_{i}"] for i in range(3)])
    # Standard 3DGS uses opacity logits and log-scales, not linear values.
    opacity = 1 / (1 + np.exp(-np.clip(vertex["opacity"].astype(np.float64), -80, 80)))
    scales = np.exp(np.clip(scales_log.astype(np.float64), -80, 80))
    mask = np.isfinite(xyz).all(axis=1) & np.isfinite(scales).all(axis=1)
    mask &= opacity >= min_opacity
    if max_axis > 0:
        mask &= np.max(scales, axis=1) <= max_axis
    if max_anisotropy > 0:
        ratio = np.max(scales, axis=1) / np.maximum(np.min(scales, axis=1), 1e-12)
        mask &= ratio <= max_anisotropy
    half = np.asarray(crop_half_size, dtype=np.float64)
    if np.any(half > 0):
        center = np.asarray(crop_center, dtype=np.float64)
        mask &= (np.abs(xyz - center) <= np.where(half > 0, half, np.inf)).all(axis=1)
    selected = vertex[mask]
    if not len(selected):
        raise ValueError("Filters removed every Gaussian; relax thresholds.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Preserve every vertex attribute (SH coefficients, rotations, etc).
    elements = [PlyElement.describe(selected, "vertex")]
    for element in ply.elements:
        if element.name != "vertex":
            elements.append(element)
    PlyData(elements, text=False).write(str(destination))
    return {"input": len(vertex), "output": len(selected), "removed": int((~mask).sum())}
