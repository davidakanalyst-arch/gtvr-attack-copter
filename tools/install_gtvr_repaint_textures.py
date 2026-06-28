from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIRCRAFT_NAME = "gtvr_attack_copter"
REPAINT_NAME = "prototype_tactical"
REPAINT_DISPLAY_NAME = "GTVR Attack Wrap"
CONVERTER_MODEL_NAME = "gtvr_repaint_textures"
DEFAULT_FS4_USER = Path.home() / "Documents" / "Aerofly FS 4"
DEFAULT_COMPILED_REPAINT = (
    ROOT / "tools" / "vendor" / "gtvr_repaint_test_user" / "aircraft" / CONVERTER_MODEL_NAME
)
TEXTURE_FILES = [
    "ext01_fuselage_color.ttx",
    "ext02_fuselage_color.ttx",
    "ext03_fuselage_color.ttx",
]


def patch_option_tmc(repaint_dir: Path, backup_dir: Path) -> None:
    option_path = repaint_dir / "option.tmc"
    if not option_path.exists():
        return

    backup_path = backup_dir / "option.tmc"
    if not backup_path.exists():
        shutil.copy2(option_path, backup_path)

    text = option_path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r"<\[string8\]\[Description\]\[[^\]]+\]>",
        f"<[string8][Description][{REPAINT_DISPLAY_NAME}]>",
        text,
        count=1,
    )
    option_path.write_text(text, encoding="utf-8")


def install(compiled_repaint: Path, fs4_user: Path) -> Path:
    repaint_dir = fs4_user / "aircraft" / AIRCRAFT_NAME / REPAINT_NAME
    if not repaint_dir.exists():
        raise FileNotFoundError(f"Missing live repaint folder: {repaint_dir}")

    for file_name in TEXTURE_FILES:
        source = compiled_repaint / file_name
        if not source.exists():
            raise FileNotFoundError(f"Missing converted repaint texture: {source}")

    backup_dir = repaint_dir.parent / f"_{REPAINT_NAME}_pre_gtvr_generated_repaint"
    backup_dir.mkdir(parents=True, exist_ok=True)

    for file_name in TEXTURE_FILES:
        target = repaint_dir / file_name
        backup = backup_dir / file_name
        if target.exists() and not backup.exists():
            shutil.copy2(target, backup)
        shutil.copy2(compiled_repaint / file_name, target)

    patch_option_tmc(repaint_dir, backup_dir)
    return backup_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Install converted GTVR tactical repaint textures.")
    parser.add_argument("--compiled-repaint", type=Path, default=DEFAULT_COMPILED_REPAINT)
    parser.add_argument("--fs4-user", type=Path, default=DEFAULT_FS4_USER)
    args = parser.parse_args()

    backup_dir = install(args.compiled_repaint, args.fs4_user)
    print(f"Installed GTVR repaint textures into {REPAINT_NAME}.")
    print(f"Original repaint files backed up at: {backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
