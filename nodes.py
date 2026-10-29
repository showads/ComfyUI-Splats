"""ComfyUI-Splats: modular, explicit video/SfM/Brush nodes."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(os.environ.get("COMFYUI_SPLATS_ROOT", "/workspace/comfyui-splats/projects")).resolve()
COLMAP = os.environ.get("COMFYUI_SPLATS_COLMAP", "colmap")
BRUSH = os.environ.get("COMFYUI_SPLATS_BRUSH", "/workspace/brush/target/release/brush")
SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$")


def _project(name: str) -> Path:
    if not SAFE_NAME.fullmatch(name):
        raise ValueError("Project must be 1–80 chars: letters, digits, hyphens and underscores.")
    return ROOT / name


def _run(args, log: Path, *, env=None):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(map(str, args)) + "\n")
        f.flush()
        p = subprocess.run([str(a) for a in args], stdout=f, stderr=subprocess.STDOUT,
                           env=env, check=False)
        if p.returncode:
            raise RuntimeError(f"Command failed ({p.returncode}); inspect {log}")


def _binary(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"Missing executable: {name}. See README install instructions.")
    return path


class SplatsLoadVideoPath:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"path": ("STRING", {"default": "/workspace/orbit.mp4"})}}
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    FUNCTION = "load"
    CATEGORY = "Splats"
    def load(self, path):
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(p)
        return (str(p),)


class SplatsPrepareVideo:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "project_name": ("STRING", {"default": "orbit_01"}),
            "target_frames": ("INT", {"default": 64, "min": 8, "max": 500}),
        }, "optional": {"video": ("VIDEO",), "video_path": ("STRING", {"default": ""})}}
    RETURN_TYPES = ("SPLATS_DATASET", "STRING")
    RETURN_NAMES = ("dataset", "image_directory")
    FUNCTION = "prepare"
    CATEGORY = "Splats"

    def prepare(self, project_name, target_frames, video=None, video_path=""):
        folder = _project(project_name)
        if folder.exists():
            raise FileExistsError(f"Project already exists: {folder}; choose a new name.")
        path = None
        if video is not None:
            # ComfyUI VIDEO exposes save_to for container-native video handling.
            folder.mkdir(parents=True, exist_ok=False)
            path = folder / "orbit.mp4"
            try:
                video.save_to(str(path), format="mp4", codec="h264")
            except TypeError:
                # Depending on ComfyUI version, save_to accepts a format object.
                raise RuntimeError("This ComfyUI VIDEO implementation does not support save_to(path, format='mp4', codec='h264'). Use video_path for now.")
        elif video_path.strip():
            path = Path(video_path).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(path)
            folder.mkdir(parents=True, exist_ok=False)
        else:
            raise ValueError("Connect a VIDEO input or provide video_path.")
        images = folder / "images"
        images.mkdir()
        ffprobe = _binary("ffprobe")
        ffmpeg = _binary("ffmpeg")
        info = subprocess.check_output([ffprobe, "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True)
        duration = float(info.strip())
        if duration <= 0:
            raise ValueError("Invalid video duration")
        fps = target_frames / duration
        _run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", path,
              "-vf", f"fps={fps:.8f}", "-fps_mode", "vfr",
              images / "frame_%04d.png"], folder / "prepare.log")
        count = len(list(images.glob("frame_*.png")))
        if count < 8:
            raise RuntimeError(f"Too few extracted frames ({count}).")
        (folder / "metadata.json").write_text(json.dumps(
            {"video": str(path), "duration_s": duration, "frames": count}, indent=2))
        return (str(folder), str(images))


class SplatsReconstruct:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "dataset": ("SPLATS_DATASET",),
            "use_gpu_sift": ("BOOLEAN", {"default": False}),
            "camera_model": (["SIMPLE_PINHOLE", "PINHOLE", "SIMPLE_RADIAL"],),
        }}
    RETURN_TYPES = ("SPLATS_SCENE", "STRING")
    RETURN_NAMES = ("scene", "statistics_path")
    FUNCTION = "reconstruct"
    CATEGORY = "Splats"

    def reconstruct(self, dataset, use_gpu_sift, camera_model):
        folder = Path(dataset).resolve()
        if folder.parent != ROOT or not (folder / "images").is_dir():
            raise ValueError("Dataset must be a prepared project in COMFYUI_SPLATS_ROOT")
        colmap = _binary(COLMAP)
        database = folder / "database.db"
        sparse = folder / "sparse"
        if database.exists() or sparse.exists():
            raise FileExistsError("COLMAP outputs already exist; create a fresh project.")
        sparse.mkdir()
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        _run([colmap, "feature_extractor", "--database_path", database,
            "--image_path", folder / "images", "--ImageReader.camera_model",
            camera_model, "--ImageReader.single_camera", "1",
            "--SiftExtraction.use_gpu", str(int(use_gpu_sift))], folder / "colmap.log", env=env)
        _run([colmap, "exhaustive_matcher", "--database_path", database,
            "--SiftMatching.use_gpu", str(int(use_gpu_sift))], folder / "colmap.log", env=env)
        _run([colmap, "mapper", "--database_path", database,
            "--image_path", folder / "images", "--output_path", sparse],
             folder / "colmap.log", env=env)
        models = sorted((p for p in sparse.iterdir() if (p / "images.bin").is_file()))
        if not models:
            raise RuntimeError("No COLMAP reconstruction produced; inspect colmap.log")
        # Prefer reconstruction with most registered frames, if more than one exists.
        stats = folder / "colmap_stats.txt"
        scored = []
        for model in models:
            output = subprocess.check_output([colmap, "model_analyzer",
                "--path", str(model)], env=env, text=True, stderr=subprocess.STDOUT)
            match = re.search(r"Registered images:\s*(\d+)", output)
            scored.append((int(match.group(1)) if match else 0, model, output))
        _, best, output = max(scored, key=lambda x: x[0])
        stats.write_text(output)
        if best.name != "0":
            # Brush accepts sparse/<id> but preserve chosen scene explicitly.
            (folder / "selected_model.txt").write_text(str(best))
        return (str(folder), str(stats))


class SplatsTrainBrush:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "scene": ("SPLATS_SCENE",),
            "iterations": ("INT", {"default": 30000, "min": 500, "max": 200000}),
            "export_every": ("INT", {"default": 5000, "min": 100, "max": 50000}),
            "max_resolution": ("INT", {"default": 1920, "min": 256, "max": 8192}),
        }}
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("latest_ply", "export_directory")
    FUNCTION = "train"
    CATEGORY = "Splats"

    def train(self, scene, iterations, export_every, max_resolution):
        folder = Path(scene).resolve()
        if folder.parent != ROOT or not (folder / "sparse").is_dir():
            raise ValueError("Scene is not a managed splat project.")
        brush = _binary(BRUSH)
        output = folder / "brush-output"
        if output.exists():
            raise FileExistsError(f"Brush output exists: {output}. Refusing to overwrite.")
        output.mkdir()
        # Brush's export-path is relative to the dataset parent.
        _run([brush, folder, "--total-train-iters", iterations,
            "--max-resolution", max_resolution, "--export-every", export_every,
            "--export-path", f"./{folder.name}/brush-output/",
            "--export-name", "splat_{iter}.ply"], folder / "brush.log")
        candidates = list(output.glob("*.ply"))
        if not candidates:
            raise RuntimeError(f"Brush completed without exporting a PLY: {folder / 'brush.log'}")
        latest = max(candidates, key=lambda p: int(re.search(r"(\d+)\.ply$", p.name).group(1))
                     if re.search(r"(\d+)\.ply$", p.name) else -1)
        return (str(latest), str(output))


NODE_CLASS_MAPPINGS = {
    "SplatsLoadVideoPath": SplatsLoadVideoPath,
    "SplatsPrepareVideo": SplatsPrepareVideo,
    "SplatsReconstruct": SplatsReconstruct,
    "SplatsTrainBrush": SplatsTrainBrush,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SplatsLoadVideoPath": "Splats: Load Video Path",
    "SplatsPrepareVideo": "Splats: Prepare Video",
    "SplatsReconstruct": "Splats: Reconstruct (COLMAP)",
    "SplatsTrainBrush": "Splats: Train (Brush)",
}
