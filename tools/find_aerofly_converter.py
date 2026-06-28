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


def is_converter_candidate(path: Path) -> bool:
    name = path.name.lower()
    if any(skip in name for skip in ("setup", "unins", "install")):
        return False
    lowered_path = str(path).lower()
    return name in {pattern.lower() for pattern in EXE_PATTERNS} or (
        "aerofly" in lowered_path and "converter" in name
    )


def sort_key(path: Path) -> tuple[int, str]:
    lowered_path = str(path).lower()
    name = path.name.lower()
    score = 0
    if name == "aerofly_fs_4_aircraft_converter.exe":
        score -= 20
    if "bin64" in lowered_path:
        score -= 10
    if "content" in name:
        score += 5
    return (score, lowered_path)


def find_converter() -> list[Path]:
    found: list[Path] = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        try:
            for path in root.rglob("*.exe"):
                if is_converter_candidate(path):
                    found.append(path)
        except (PermissionError, OSError):
            continue
    return sorted(set(found), key=sort_key)


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
