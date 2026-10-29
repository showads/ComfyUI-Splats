# Example workflows

Open `video_to_splat.json` in ComfyUI. Change the **Splats: Load Video Path** node to the path of your saved MP4 and change the project name for every new run.

1. **Splats: Setup Dependencies**: enable the checkbox to install missing *CPU* COLMAP and FFmpeg using apt when running as root (RunPod). Leave disabled to use existing tools. This does **not** install Brush or CUDA COLMAP.
2. **Splats: Load Video Path**: select the MP4 by absolute path. This starter example uses a filepath, not a native ComfyUI VIDEO connection.
3. **Splats: Prepare Video**: samples 64 frames and creates a project.
4. **Splats: Reconstruct (COLMAP)**: run CPU SIFT first, then try GPU only after installing a CUDA COLMAP build.
5. **Splats: Train (Brush)**: requires the Brush binary configured at `COMFYUI_SPLATS_BRUSH` (default `/workspace/brush/target/release/brush`).

**Important:** This workflow is an example, not yet verified against a live ComfyUI instance. The setup node cannot guarantee a no-SSH fresh-pod install of Brush/CUDA. See main README.
