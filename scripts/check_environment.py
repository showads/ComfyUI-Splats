#!/usr/bin/env python3
import os
import shutil
import subprocess

tools = {
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "colmap": os.getenv("COMFYUI_SPLATS_COLMAP", "colmap"),
    "brush": os.getenv("COMFYUI_SPLATS_BRUSH", "/workspace/brush/target/release/brush"),
}
for label, name in tools.items():
    path = shutil.which(name)
    print(f"{label:8} {path or 'MISSING'}")
    if path and label == "colmap":
        p = subprocess.run([path, "help"], capture_output=True, text=True)
        print((p.stdout or p.stderr).splitlines()[:2])
