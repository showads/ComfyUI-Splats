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

## Example workflow and opt-in setup

Load [example_workflows/video_to_splat.json](example_workflows/video_to_splat.json) into ComfyUI. It connects a **video filepath** node to Prepare Video, Reconstruct and Train Brush. A native H3 VIDEO wire is supported as an optional input on Prepare Video, but this example uses a saved MP4 path for broader compatibility.

The **Splats: Setup Dependencies** node can install missing FFmpeg and CPU COLMAP using apt on root-enabled Ubuntu/RunPod containers. Enable `install_missing` to authorize that action; otherwise it only checks prerequisites. It is wired into Prepare Video to run first. Installation may need network access, root permissions and compatible OS packages; CUDA-enabled COLMAP and Brush are not automatically installed. To avoid SSH entirely on a fresh pod, a prebuilt RunPod image/template with those tools is the reliable next milestone.

**Known limitation:** this workflow and the ComfyUI native VIDEO adapter have not yet been smoke-tested in a running ComfyUI instance.

## Cleaning noisy splats (experimental)

Install Python dependencies into the **ComfyUI Python environment**: `pip install -r requirements.txt` (or `uv pip install --python /path/to/comfyui/python -r requirements.txt`).

The **Splats: Clean PLY (Non-destructive)** node loads a standard 3DGS Gaussian PLY and exports `*_cleaned.ply` without changing the original. Controls:

- `min_opacity`: sigmoid of the stored opacity logit, 0–1; start around 0.05–0.15.
- `max_axis`: upper limit on Gaussian world-space standard deviation (largest axis). Zero disables. Scene units are arbitrary; inspect your PLY before setting.
- `max_anisotropy`: upper limit on ratio of largest to smallest Gaussian axis. Zero disables.
- `crop_center_*` and `crop_half_*`: axis-aligned crop box; half-size zero on an axis means no crop on that axis.

This is a **static export filter**, not yet a live viewer control or draggable 3D crop box. It does not repair inaccurate camera poses or reconstruct missing geometry. The source PLY remains untouched. It supports conventional 3D Gaussian PLY fields, not arbitrary splat encodings. You can compare Brush's 5k/10k/30k PLY files by changing the input path.

Planned follow-ups: in-viewer interactive filtering/crop, checkpoint gallery, COLMAP camera visualization, and foreground-masked Brush training. Masked training needs verification against the selected Brush version and is not implemented yet.
