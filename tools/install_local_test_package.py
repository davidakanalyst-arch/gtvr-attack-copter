from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_FS4_STEAM = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator"
)
DEFAULT_FS4_USER = Path.home() / "Documents" / "Aerofly FS 4"

SOURCE_AIRCRAFT = "ec135"
TARGET_AIRCRAFT = "gtvr_attack_copter"
STOCK_OPTION_FOLDERS = ["adac", "drf", "german_army", "police", "sheriff"]
TACTICAL_REPAINT_SOURCE = "german_army"
TACTICAL_REPAINT_TARGET = "prototype_tactical"


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError(f"Expected text not found: {old}")
    return text.replace(old, new, 1)


def patch_tmc(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = replace_once(text, "<[string8][DisplayName][EC135]>", "<[string8][DisplayName][GTVR Attack Copter]>")
    text = replace_once(
        text,
        "<[string8][DisplayNameFull][Eurocopter EC135-T1]>",
        "<[string8][DisplayNameFull][GTVR Attack Copter Prototype]>",
    )
    text = replace_once(
        text,
        "<[stringt8c][ICAO][EC35]>",
        "<[stringt8c][ICAO][GTAC]>",
    )
    text = replace_once(
        text,
        "<[uint32] [Year]                 [1994]>",
        "<[uint32] [Year]                 [2026]>",
    )
    text = replace_once(
        text,
        "<[string8][Tags][ helicopter turboshaft vertical_takeoff ]>",
        "<[string8][Tags][ helicopter turboshaft vertical_takeoff military prototype ]>",
    )

    start = text.find("<[list_localized_text][Descriptions][]")
    end = text.find("        <[float64][MaximumTaxiMass]", start)
    if start != -1 and end != -1:
        description = """<[list_localized_text][Descriptions][]
            <[localized_text][element][0]
                <[string8u][Language][en]>
                <[string8][Text][GTVR Attack Copter is a private local prototype for Aerofly FS 4. This first build preserves the EC135-style glass cockpit and handling baseline while the original tactical exterior shell is developed.]>
            >
        >
"""
        text = text[:start] + description + text[end:]

    path.write_text(text, encoding="utf-8")


def patch_option(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("<[string8][Description][Black]>", "<[string8][Description][Prototype Black]>")
    path.write_text(text, encoding="utf-8")


def rename_main_files(target_dir: Path) -> None:
    for suffix in [".tmc", ".tmb", ".tmq"]:
        old = target_dir / f"{SOURCE_AIRCRAFT}{suffix}"
        new = target_dir / f"{TARGET_AIRCRAFT}{suffix}"
        if old.exists():
            old.rename(new)

    for state in ["clean", "cold", "landing", "start", "takeoff"]:
        old = target_dir / f"{SOURCE_AIRCRAFT}_{state}.tmd"
        new = target_dir / f"{TARGET_AIRCRAFT}_{state}.tmd"
        if old.exists():
            old.rename(new)


def remove_stock_options(target_dir: Path) -> None:
    for folder_name in STOCK_OPTION_FOLDERS:
        folder = target_dir / folder_name
        if folder.exists():
            shutil.rmtree(folder)


def apply_tactical_repaint(target_dir: Path) -> None:
    repaint_dir = target_dir / TACTICAL_REPAINT_SOURCE
    if not repaint_dir.exists():
        raise FileNotFoundError(f"Expected tactical repaint folder missing: {repaint_dir}")

    tactical_dir = target_dir / TACTICAL_REPAINT_TARGET
    shutil.copytree(repaint_dir, tactical_dir)

    option_path = tactical_dir / "option.tmc"
    option_text = option_path.read_text(encoding="utf-8", errors="replace")
    option_text = option_text.replace(
        "<[string8][Description][German Army]>",
        "<[string8][Description][Prototype Tactical]>",
    )
    option_path.write_text(option_text, encoding="utf-8")


def write_marker_files(target_dir: Path, source_dir: Path) -> None:
    (target_dir / "_GTVR_PROTOTYPE.txt").write_text(
        "\n".join(
            [
                "GTVR Attack Copter local prototype",
                "",
                f"Created from local Aerofly FS 4 source aircraft: {source_dir}",
                "Purpose: private local testing while the original exterior shell is developed.",
                "",
                "Do not commit this copied aircraft folder to the repo.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def copy_source_model(target_dir: Path, repo_root: Path) -> None:
    source_model = repo_root / "source-model"
    if not source_model.exists():
        return
    target_source = target_dir / "_gtvr_source_model"
    if target_source.exists():
        shutil.rmtree(target_source)
    shutil.copytree(source_model, target_source)


def install(force: bool, steam_root: Path, user_root: Path) -> Path:
    source_dir = steam_root / "aircraft" / SOURCE_AIRCRAFT
    target_dir = user_root / "aircraft" / TARGET_AIRCRAFT

    if not source_dir.exists():
        raise FileNotFoundError(f"Source aircraft folder not found: {source_dir}")

    if target_dir.exists():
        if not force:
            raise FileExistsError(f"Target already exists, rerun with --force: {target_dir}")
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)

    tmc_path = target_dir / f"{SOURCE_AIRCRAFT}.tmc"
    if not tmc_path.exists():
        raise FileNotFoundError(f"Expected copied TMC missing: {tmc_path}")
    patch_tmc(tmc_path)
    patch_option(target_dir / "option.tmc")
    apply_tactical_repaint(target_dir)
    rename_main_files(target_dir)
    remove_stock_options(target_dir)

    repo_root = Path(__file__).resolve().parents[1]
    copy_source_model(target_dir, repo_root)
    write_marker_files(target_dir, source_dir)

    return target_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the local GTVR Attack Copter FS4 prototype.")
    parser.add_argument("--force", action="store_true", help="Replace an existing local prototype folder.")
    parser.add_argument("--steam-root", type=Path, default=DEFAULT_FS4_STEAM)
    parser.add_argument("--user-root", type=Path, default=DEFAULT_FS4_USER)
    args = parser.parse_args()

    target = install(args.force, args.steam_root, args.user_root)
    print(f"Installed local prototype: {target}")


if __name__ == "__main__":
    main()
