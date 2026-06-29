from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GTVR_AIRCRAFT_NAME = "gtvr_attack_copter"
EC135_AIRCRAFT_NAME = "ec135"
GTVR_OLIVE_REPAINT_NAME = "prototype_tactical"
GTVR_DESERT_REPAINT_NAME = "prototype_desert"
EC135_BLACK_REPAINT_NAME = "gtvr_attack_black"
EC135_DESERT_REPAINT_NAME = "gtvr_attack_desert"
GTVR_OLIVE_DISPLAY_NAME = "GTVR Attack Camo"
BLACK_DISPLAY_NAME = "GTVR Attack Black"
DESERT_DISPLAY_NAME = "GTVR Attack Desert"
CONVERTER_MODEL_NAME = "gtvr_repaint_textures"
DEFAULT_FS4_USER = Path.home() / "Documents" / "Aerofly FS 4"
DEFAULT_STOCK_EC135 = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator\aircraft\ec135"
)
DEFAULT_COMPILED_REPAINT = (
    ROOT / "tools" / "vendor" / "gtvr_repaint_test_user" / "aircraft" / CONVERTER_MODEL_NAME
)
DEFAULT_COMPILED_PREVIEWS = (
    ROOT / "tools" / "vendor" / "gtvr_menu_preview_user" / "aircraft" / "gtvr_menu_preview"
)
COLOR_TEXTURE_FILES = [
    "ext01_fuselage_color.ttx",
    "ext02_fuselage_color.ttx",
    "ext03_fuselage_color.ttx",
]
PREVIEW_FILES = ["preview.ttx", "preview_small.ttx"]
CUSTOM_PREVIEW_FILES = {
    "black": ("black_preview_color.ttx", "black_preview_small_color.ttx"),
    "camo": ("camo_preview_color.ttx", "camo_preview_small_color.ttx"),
    "desert": ("desert_preview_color.ttx", "desert_preview_small_color.ttx"),
}


def validate_compiled_repaint(compiled_repaint: Path) -> None:
    for file_name in COLOR_TEXTURE_FILES:
        source = compiled_repaint / file_name
        if not source.exists():
            raise FileNotFoundError(f"Missing converted repaint file: {source}")


def backup_file(path: Path, backup_dir: Path, backup_name: str | None = None) -> None:
    if not path.exists():
        return

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / (backup_name or path.name)
    if not backup_path.exists():
        shutil.copy2(path, backup_path)


def patch_option_tmc(repaint_dir: Path, backup_dir: Path, display_name: str) -> None:
    option_path = repaint_dir / "option.tmc"
    if not option_path.exists():
        return

    backup_file(option_path, backup_dir, "option.tmc.backup")

    text = option_path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r"<\[string8\]\[Description\]\[[^\]]+\]>",
        f"<[string8][Description][{display_name}]>",
        text,
        count=1,
    )
    option_path.write_text(text, encoding="utf-8")


def copy_converted_files(compiled_repaint: Path, target_dir: Path, backup_dir: Path) -> None:
    for file_name in COLOR_TEXTURE_FILES:
        target = target_dir / file_name
        backup_file(target, backup_dir)
        shutil.copy2(compiled_repaint / file_name, target)


def restore_original_previews(target_dir: Path, backup_dir: Path) -> None:
    for file_name in PREVIEW_FILES:
        target = target_dir / file_name
        backup = backup_dir / file_name
        if not backup.exists():
            backup_file(target, backup_dir)
        if backup.exists():
            shutil.copy2(backup, target)


def copy_preview_files(source_dir: Path, target_dir: Path, backup_dir: Path) -> None:
    for file_name in PREVIEW_FILES:
        source = source_dir / file_name
        if not source.exists():
            raise FileNotFoundError(f"Missing preview source file: {source}")

        target = target_dir / file_name
        backup_file(target, backup_dir)
        shutil.copy2(source, target)


def copy_custom_preview_files(compiled_previews: Path, variant: str, target_dir: Path, backup_dir: Path) -> bool:
    large_name, small_name = CUSTOM_PREVIEW_FILES[variant]
    source_files = [compiled_previews / large_name, compiled_previews / small_name]
    if not all(path.exists() for path in source_files):
        return False

    for source, target_name in zip(source_files, PREVIEW_FILES):
        target = target_dir / target_name
        backup_file(target, backup_dir)
        shutil.copy2(source, target)
    return True


def gtvr_black_preview_dir(fs4_user: Path) -> Path:
    return fs4_user / "aircraft" / GTVR_AIRCRAFT_NAME


def stock_camo_preview_dir(stock_ec135: Path) -> Path:
    return stock_ec135 / "german_army"


def disable_backup_repaint_options(aircraft_dir: Path) -> None:
    for option_path in aircraft_dir.glob("_*/option.tmc"):
        disabled_path = option_path.with_name("option.tmc.backup")
        counter = 1
        while disabled_path.exists():
            disabled_path = option_path.with_name(f"option.tmc.backup.{counter}")
            counter += 1
        option_path.rename(disabled_path)


def install_gtvr_olive(compiled_repaint: Path, compiled_previews: Path, fs4_user: Path) -> Path:
    repaint_dir = fs4_user / "aircraft" / GTVR_AIRCRAFT_NAME / GTVR_OLIVE_REPAINT_NAME
    if not repaint_dir.exists():
        raise FileNotFoundError(f"Missing live GTVR olive repaint folder: {repaint_dir}")

    backup_dir = repaint_dir.parent / f"_{GTVR_OLIVE_REPAINT_NAME}_pre_gtvr_generated_repaint"
    copy_converted_files(compiled_repaint, repaint_dir, backup_dir)
    if not copy_custom_preview_files(compiled_previews, "camo", repaint_dir, backup_dir):
        restore_original_previews(repaint_dir, backup_dir)
    patch_option_tmc(repaint_dir, backup_dir, GTVR_OLIVE_DISPLAY_NAME)
    disable_backup_repaint_options(repaint_dir.parent)
    return backup_dir


def install_gtvr_black(compiled_repaint: Path, compiled_previews: Path, fs4_user: Path) -> Path:
    aircraft_dir = fs4_user / "aircraft" / GTVR_AIRCRAFT_NAME
    if not aircraft_dir.exists():
        raise FileNotFoundError(f"Missing live GTVR aircraft folder: {aircraft_dir}")

    backup_dir = aircraft_dir / "_root_black_pre_gtvr_generated_repaint"
    copy_converted_files(compiled_repaint, aircraft_dir, backup_dir)
    if not copy_custom_preview_files(compiled_previews, "black", aircraft_dir, backup_dir):
        restore_original_previews(aircraft_dir, backup_dir)
    patch_option_tmc(aircraft_dir, backup_dir, BLACK_DISPLAY_NAME)
    disable_backup_repaint_options(aircraft_dir)
    return backup_dir


def ensure_gtvr_desert_repaint_folder(fs4_user: Path) -> Path:
    aircraft_dir = fs4_user / "aircraft" / GTVR_AIRCRAFT_NAME
    source_repaint = aircraft_dir / GTVR_OLIVE_REPAINT_NAME
    repaint_dir = aircraft_dir / GTVR_DESERT_REPAINT_NAME
    if not source_repaint.exists():
        raise FileNotFoundError(f"Missing GTVR source repaint folder: {source_repaint}")

    if not repaint_dir.exists():
        shutil.copytree(source_repaint, repaint_dir)
    return repaint_dir


def install_gtvr_desert(compiled_repaint: Path, compiled_previews: Path, fs4_user: Path) -> Path:
    repaint_dir = ensure_gtvr_desert_repaint_folder(fs4_user)
    backup_dir = repaint_dir.parent / f"_{GTVR_DESERT_REPAINT_NAME}_pre_gtvr_generated_repaint"
    copy_converted_files(compiled_repaint, repaint_dir, backup_dir)
    if not copy_custom_preview_files(compiled_previews, "desert", repaint_dir, backup_dir):
        copy_preview_files(repaint_dir.parent / GTVR_OLIVE_REPAINT_NAME, repaint_dir, backup_dir)
    patch_option_tmc(repaint_dir, backup_dir, DESERT_DISPLAY_NAME)
    disable_backup_repaint_options(repaint_dir.parent)
    return backup_dir


def ensure_ec135_repaint_folder(fs4_user: Path, stock_ec135: Path, repaint_name: str) -> Path:
    stock_repaint = stock_ec135 / "german_army"
    if not stock_repaint.exists():
        raise FileNotFoundError(f"Missing stock EC135 German Army repaint folder: {stock_repaint}")

    repaint_dir = fs4_user / "aircraft" / EC135_AIRCRAFT_NAME / repaint_name
    if not repaint_dir.exists():
        repaint_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stock_repaint, repaint_dir)
    return repaint_dir


def install_ec135_black(compiled_repaint: Path, compiled_previews: Path, fs4_user: Path, stock_ec135: Path) -> Path:
    repaint_dir = ensure_ec135_repaint_folder(fs4_user, stock_ec135, EC135_BLACK_REPAINT_NAME)
    backup_dir = repaint_dir.parent / f"_{EC135_BLACK_REPAINT_NAME}_pre_gtvr_generated_repaint"
    copy_converted_files(compiled_repaint, repaint_dir, backup_dir)
    if not copy_custom_preview_files(compiled_previews, "black", repaint_dir, backup_dir):
        copy_preview_files(gtvr_black_preview_dir(fs4_user), repaint_dir, backup_dir)
    patch_option_tmc(repaint_dir, backup_dir, BLACK_DISPLAY_NAME)
    return backup_dir


def install_ec135_desert(compiled_repaint: Path, compiled_previews: Path, fs4_user: Path, stock_ec135: Path) -> Path:
    repaint_dir = ensure_ec135_repaint_folder(fs4_user, stock_ec135, EC135_DESERT_REPAINT_NAME)
    backup_dir = repaint_dir.parent / f"_{EC135_DESERT_REPAINT_NAME}_pre_gtvr_generated_repaint"
    copy_converted_files(compiled_repaint, repaint_dir, backup_dir)
    if not copy_custom_preview_files(compiled_previews, "desert", repaint_dir, backup_dir):
        copy_preview_files(stock_camo_preview_dir(stock_ec135), repaint_dir, backup_dir)
    patch_option_tmc(repaint_dir, backup_dir, DESERT_DISPLAY_NAME)
    return backup_dir


def install(compiled_repaint: Path, compiled_previews: Path, fs4_user: Path, stock_ec135: Path, variant: str) -> list[Path]:
    validate_compiled_repaint(compiled_repaint)
    if variant == "olive":
        return [install_gtvr_olive(compiled_repaint, compiled_previews, fs4_user)]
    if variant == "black":
        return [
            install_gtvr_black(compiled_repaint, compiled_previews, fs4_user),
            install_ec135_black(compiled_repaint, compiled_previews, fs4_user, stock_ec135),
        ]
    if variant == "desert":
        return [
            install_gtvr_desert(compiled_repaint, compiled_previews, fs4_user),
            install_ec135_desert(compiled_repaint, compiled_previews, fs4_user, stock_ec135),
        ]
    raise ValueError(f"Unsupported repaint variant: {variant}")


def repair_previews(fs4_user: Path, stock_ec135: Path, compiled_previews: Path) -> list[Path]:
    gtvr_dir = fs4_user / "aircraft" / GTVR_AIRCRAFT_NAME
    gtvr_root_backup = gtvr_dir / "_root_black_pre_gtvr_generated_repaint"
    gtvr_olive_dir = gtvr_dir / GTVR_OLIVE_REPAINT_NAME
    gtvr_olive_backup = gtvr_dir / f"_{GTVR_OLIVE_REPAINT_NAME}_pre_gtvr_generated_repaint"
    gtvr_desert_dir = gtvr_dir / GTVR_DESERT_REPAINT_NAME
    gtvr_desert_backup = gtvr_dir / f"_{GTVR_DESERT_REPAINT_NAME}_pre_gtvr_generated_repaint"
    ec135_black_dir = fs4_user / "aircraft" / EC135_AIRCRAFT_NAME / EC135_BLACK_REPAINT_NAME
    ec135_backup = ec135_black_dir.parent / f"_{EC135_BLACK_REPAINT_NAME}_pre_gtvr_generated_repaint"
    ec135_desert_dir = fs4_user / "aircraft" / EC135_AIRCRAFT_NAME / EC135_DESERT_REPAINT_NAME
    ec135_desert_backup = ec135_desert_dir.parent / f"_{EC135_DESERT_REPAINT_NAME}_pre_gtvr_generated_repaint"

    if not copy_custom_preview_files(compiled_previews, "black", gtvr_dir, gtvr_root_backup):
        restore_original_previews(gtvr_dir, gtvr_root_backup)
    if not copy_custom_preview_files(compiled_previews, "camo", gtvr_olive_dir, gtvr_olive_backup):
        restore_original_previews(gtvr_olive_dir, gtvr_olive_backup)
    if gtvr_desert_dir.exists():
        if not copy_custom_preview_files(compiled_previews, "desert", gtvr_desert_dir, gtvr_desert_backup):
            copy_preview_files(gtvr_olive_dir, gtvr_desert_dir, gtvr_desert_backup)
    if not copy_custom_preview_files(compiled_previews, "black", ec135_black_dir, ec135_backup):
        copy_preview_files(gtvr_black_preview_dir(fs4_user), ec135_black_dir, ec135_backup)
    if ec135_desert_dir.exists():
        if not copy_custom_preview_files(compiled_previews, "desert", ec135_desert_dir, ec135_desert_backup):
            copy_preview_files(stock_camo_preview_dir(stock_ec135), ec135_desert_dir, ec135_desert_backup)
    return [gtvr_root_backup, gtvr_olive_backup, gtvr_desert_backup, ec135_backup, ec135_desert_backup]


def main() -> int:
    parser = argparse.ArgumentParser(description="Install converted GTVR attack repaint textures.")
    parser.add_argument("--compiled-repaint", type=Path, default=DEFAULT_COMPILED_REPAINT)
    parser.add_argument("--compiled-previews", type=Path, default=DEFAULT_COMPILED_PREVIEWS)
    parser.add_argument("--fs4-user", type=Path, default=DEFAULT_FS4_USER)
    parser.add_argument("--stock-ec135", type=Path, default=DEFAULT_STOCK_EC135)
    parser.add_argument("--variant", choices=["olive", "black", "desert"], default="olive")
    parser.add_argument("--repair-previews", action="store_true")
    args = parser.parse_args()

    if args.repair_previews:
        backup_dirs = repair_previews(args.fs4_user, args.stock_ec135, args.compiled_previews)
        print("Repaired GTVR and EC135 attack repaint preview files.")
    else:
        backup_dirs = install(args.compiled_repaint, args.compiled_previews, args.fs4_user, args.stock_ec135, args.variant)
        print(f"Installed {args.variant} GTVR attack repaint files.")

    for backup_dir in backup_dirs:
        print(f"Original files backed up at: {backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
