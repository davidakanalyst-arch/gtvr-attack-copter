from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIRCRAFT_NAME = "gtvr_attack_copter"
OVERLAY_NAME = "gtvr_attack_shell"
DEFAULT_FS4_USER = Path.home() / "Documents" / "Aerofly FS 4"
DEFAULT_COMPILED_OVERLAY = (
    ROOT / "tools" / "vendor" / "gtvr_overlay_test_user" / "aircraft" / OVERLAY_NAME
)
OVERLAY_FILES = [
    f"{OVERLAY_NAME}.tmb",
    "matte_graphite_color.ttx",
    "canopy_glass_color.ttx",
    "dark_metal_color.ttx",
    "olive_panel_color.ttx",
    "warning_red_color.ttx",
]


def copy_overlay(compiled_overlay: Path, fs4_user: Path) -> list[Path]:
    targets = [
        fs4_user / "objects" / OVERLAY_NAME,
        fs4_user / "aircraft" / AIRCRAFT_NAME / "objects" / OVERLAY_NAME,
    ]

    for file_name in OVERLAY_FILES:
        source = compiled_overlay / file_name
        if not source.exists():
            raise FileNotFoundError(f"Missing compiled overlay file: {source}")

    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        for file_name in OVERLAY_FILES:
            shutil.copy2(compiled_overlay / file_name, target / file_name)

    return targets


def patch_aircraft_tmc(fs4_user: Path) -> Path:
    tmc_path = fs4_user / "aircraft" / AIRCRAFT_NAME / f"{AIRCRAFT_NAME}.tmc"
    if not tmc_path.exists():
        raise FileNotFoundError(f"Missing live aircraft TMC: {tmc_path}")

    backup_path = tmc_path.with_name(f"{tmc_path.name}.pre_gtvr_pilot_overlay.bak")
    if not backup_path.exists():
        shutil.copy2(tmc_path, backup_path)

    text = tmc_path.read_text(encoding="utf-8-sig", errors="replace")
    updated = re.sub(
        r"<\[string8\]\[Pilot\]\[[^\]]+\]>",
        f"<[string8][Pilot][{OVERLAY_NAME}]>",
        text,
        count=1,
    )
    if updated == text:
        raise ValueError(f"Pilot field not found in {tmc_path}")

    tmc_path.write_text(updated, encoding="utf-8")
    return backup_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the compiled GTVR shell as an Aerofly pilot-slot object.")
    parser.add_argument("--compiled-overlay", type=Path, default=DEFAULT_COMPILED_OVERLAY)
    parser.add_argument("--fs4-user", type=Path, default=DEFAULT_FS4_USER)
    args = parser.parse_args()

    targets = copy_overlay(args.compiled_overlay, args.fs4_user)
    backup = patch_aircraft_tmc(args.fs4_user)

    print("Installed overlay object folders:")
    for target in targets:
        print(f"  {target}")
    print(f"Backed up original TMC at: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
