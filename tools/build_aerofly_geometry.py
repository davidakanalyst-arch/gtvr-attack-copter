from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from find_aerofly_converter import find_converter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_OBJ = ROOT / "source-model" / "gtvr_attack_copter_shell.obj"
LOCAL_AIRCRAFT = Path.home() / "Documents" / "Aerofly FS 4" / "aircraft" / "gtvr_attack_copter"
TARGET_TMB = LOCAL_AIRCRAFT / "gtvr_attack_copter.tmb"


def main() -> int:
    converters = find_converter()
    if not converters:
        print("Cannot build Aerofly geometry: no converter executable found.")
        print("")
        print("The current in-game model is still:")
        print(f"  {TARGET_TMB}")
        print("")
        print("The source shell waiting to be converted is:")
        print(f"  {SOURCE_OBJ}")
        print("")
        print("Install or place the Aerofly aircraft/content converter, then rerun:")
        print(r"  python tools\build_aerofly_geometry.py")
        return 2

    converter = converters[0]
    print(f"Found converter candidate: {converter}")
    print("")
    print("I am not invoking it automatically yet because Aerofly converter command-line")
    print("arguments vary by SDK version. Once we inspect the converter help/output,")
    print("this script should become the one-command geometry build.")

    try:
        subprocess.run([str(converter), "--help"], cwd=ROOT, check=False)
    except OSError as exc:
        print(f"Could not execute converter candidate: {exc}")
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

