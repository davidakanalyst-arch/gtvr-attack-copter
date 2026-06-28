from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXE_PATTERNS = [
    "aircraft_converter.exe",
    "aerofly_fs_2_aircraft_converter.exe",
    "aerofly_fs_4_aircraft_converter.exe",
    "content_converter.exe",
    "aerofly_fs_2_content_converter.exe",
    "aerofly_fs_4_content_converter.exe",
]

SEARCH_ROOTS = [
    ROOT,
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path(r"C:\Program Files"),
    Path(r"C:\Program Files (x86)"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
    Path(r"C:\Program Files (x86)\Steam\steamapps\common"),
]


def find_converter() -> list[Path]:
    found: list[Path] = []
    lowered = {pattern.lower() for pattern in EXE_PATTERNS}
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        try:
            for path in root.rglob("*.exe"):
                if path.name.lower() in lowered or "aerofly" in str(path).lower() and "converter" in path.name.lower():
                    found.append(path)
        except (PermissionError, OSError):
            continue
    return sorted(set(found))


def main() -> int:
    matches = find_converter()
    if not matches:
        print("No Aerofly aircraft/content converter executable found.")
        print("")
        print("Geometry replacement is blocked until the Aerofly SDK converter is installed or placed in this repo.")
        print("Expected names include:")
        for pattern in EXE_PATTERNS:
            print(f"  - {pattern}")
        return 2

    print("Found possible Aerofly converter executable(s):")
    for match in matches:
        print(f"  {match}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

