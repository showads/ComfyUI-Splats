# ComfyUI-Splats

Experimental H3/video → COLMAP → Brush → Gaussian splat pipeline for ComfyUI.

## Current scope (initial milestone)

- **Splats: Prepare Video**: convert a ComfyUI VIDEO or video filepath into timestamp-sampled PNGs.
- **Splats: Reconstruct**: COLMAP feature extraction, exhaustive matching, mapper and statistics.
- **Splats: Train Brush**: external Brush executable, PLY exports at intervals.
- **Splats: Load Video Path**: convenience input when the video is already saved.

Outputs are saved under `/workspace/comfyui-splats/projects` by default on RunPod (override with `COMFYUI_SPLATS_ROOT`). Existing project folders are never automatically overwritten.

This is an experimental integration. GPU SIFT requires a CUDA-enabled COLMAP build; the Ubuntu apt COLMAP package may be CPU-only. Brush requires a compatible graphics/Vulkan runtime. No installers run at ComfyUI import.

## Install

Clone into `ComfyUI/custom_nodes/ComfyUI-Splats`, then restart ComfyUI. `ffmpeg`, `ffprobe`, `colmap`, and `brush` must be installed separately. The Brush binary can be configured with `COMFYUI_SPLATS_BRUSH`; `COMFYUI_SPLATS_COLMAP` likewise overrides COLMAP.

Run `python scripts/check_environment.py` to inspect dependencies. On Ubuntu, CPU COLMAP can usually be installed with `apt-get update && apt-get install -y colmap ffmpeg`. For CUDA SIFT, install a compatible CUDA-enabled COLMAP separately.

## Example graph

`H3 VIDEO → Splats: Prepare Video → Splats: Reconstruct → Splats: Train Brush`

Use `Splats: Load Video Path` instead of the H3 VIDEO output for a pre-existing MP4. Prepare Video also supports explicit file paths.

## Limitations / roadmap

This milestone uses synchronous subprocesses (a long job occupies a ComfyUI queue slot), with logs written to each project. It does not yet include the embedded 3D splat viewer, installation manager, cancellation controls or progress streaming. Those are planned as separate milestones. Camera mapping is mostly CPU; CUDA SIFT accelerates feature extraction and matching when supported.

Safety: paths and project names are validated, processes are launched without a shell, and no software is installed automatically.
