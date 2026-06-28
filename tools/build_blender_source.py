from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLENDER_SCRIPT = ROOT / "blender" / "create_gtvr_attack_copter_scene.py"


def find_blender() -> str | None:
    from_path = shutil.which("blender")
    if from_path:
        return from_path

    candidates = [
        Path(r"C:\Program Files\Blender Foundation"),
        Path(r"C:\Program Files (x86)\Blender Foundation"),
        Path.home() / "AppData" / "Local" / "Programs",
    ]
    for root in candidates:
        if not root.exists():
            continue
        for blender_exe in root.rglob("blender.exe"):
            return str(blender_exe)
    return None


def main() -> int:
    blender = find_blender()
    if not blender:
        print("Blender was not found.")
        print("Install Blender, then rerun:")
        print(r"python tools\build_blender_source.py")
        print("")
        print("The script will create:")
        print(r"blender\gtvr_attack_copter_shell.blend")
        print(r"exports\gtvr_attack_copter_shell_named.obj")
        return 2

    subprocess.run(
        [blender, "--background", "--python", str(BLENDER_SCRIPT)],
        cwd=ROOT,
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

