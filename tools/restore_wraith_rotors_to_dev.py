from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROTORS_NAME = "gtvr_wraith_rotors"
DEV_NAME = "gtvr_wraith_dev"
DEV_DISPLAY_NAME = "GTVR Wraith Dev"
DEV_ICAO = "GTWD"
DEV_PILOT = "pilot_jason"
LOCAL_AIRCRAFT_ROOT = ROOT / "local-aircraft-packages"
LOCAL_ROTORS = LOCAL_AIRCRAFT_ROOT / ROTORS_NAME
LOCAL_DEV = LOCAL_AIRCRAFT_ROOT / DEV_NAME
DEFAULT_USER_ROOT = Path.home() / "Documents" / "Aerofly FS 4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def replace_one(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not patch {label} in restored dev TMC.")
    return updated


def assert_aircraft_child(path: Path, aircraft_root: Path, expected_name: str) -> None:
    if path.name != expected_name or path.parent.resolve() != aircraft_root.resolve():
        raise RuntimeError(f"Refusing unexpected aircraft path: {path}")


def rename_rotors_files(package_dir: Path) -> None:
    for child in list(package_dir.iterdir()):
        if child.is_file() and child.name.startswith(ROTORS_NAME):
            suffix = child.name[len(ROTORS_NAME) :]
            child.rename(package_dir / f"{DEV_NAME}{suffix}")


def patch_dev_identity(package_dir: Path) -> None:
    tmc = package_dir / f"{DEV_NAME}.tmc"
    text = tmc.read_text(encoding="utf-8", errors="replace")
    text = replace_one(
        text,
        r"<\[stringt8c\]\[ICAO\]\[[^\]]+\]>",
        f"<[stringt8c][ICAO][{DEV_ICAO}]>",
        "ICAO",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[DisplayName\]\[[^\]]+\]>",
        f"<[string8][DisplayName][{DEV_DISPLAY_NAME}]>",
        "DisplayName",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[DisplayNameFull\]\[[^\]]+\]>",
        f"<[string8][DisplayNameFull][{DEV_DISPLAY_NAME}]>",
        "DisplayNameFull",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[Pilot\]\[[^\]]+\]>",
        f"<[string8][Pilot][{DEV_PILOT}]>",
        "Pilot",
    )
    tmc.write_text(text, encoding="utf-8")

    for marker_name in ("_GTVR_WRAITH_ROTORS.txt", "_GTVR_WRAITH_EC135_CORE.txt"):
        marker = package_dir / marker_name
        if marker.exists():
            marker.unlink()
    (package_dir / "_GTVR_WRAITH_DEV.txt").write_text(
        "\n".join(
            [
                DEV_DISPLAY_NAME,
                "",
                "Restored directly from the preserved GTVR Wraith Rotors aircraft copy.",
                "The geometry, controls, states and options match the rotors copy.",
                "Only the folder, aircraft filenames, ICAO and display name use the dev identity.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def validate_dev(package_dir: Path, rotors_tmb_hash: str) -> None:
    required = [
        package_dir / f"{DEV_NAME}.tmc",
        package_dir / f"{DEV_NAME}.tmb",
        package_dir / f"{DEV_NAME}.tmq",
        package_dir / f"{DEV_NAME}_clean.tmd",
        package_dir / f"{DEV_NAME}_cold.tmd",
        package_dir / f"{DEV_NAME}_landing.tmd",
        package_dir / f"{DEV_NAME}_start.tmd",
        package_dir / f"{DEV_NAME}_takeoff.tmd",
        package_dir / "controls.tmd",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Restored dev package is missing: " + ", ".join(missing))

    rotors_named = [path.name for path in package_dir.iterdir() if path.name.startswith(ROTORS_NAME)]
    if rotors_named:
        raise RuntimeError("Restored dev still contains rotors-named files: " + ", ".join(rotors_named))
    if sha256(package_dir / f"{DEV_NAME}.tmb") != rotors_tmb_hash:
        raise RuntimeError("Restored dev TMB does not match the rotors source TMB.")

    text = (package_dir / f"{DEV_NAME}.tmc").read_text(encoding="utf-8", errors="replace")
    for fragment in (
        f"<[stringt8c][ICAO][{DEV_ICAO}]>",
        f"<[string8][DisplayName][{DEV_DISPLAY_NAME}]>",
        f"<[string8][DisplayNameFull][{DEV_DISPLAY_NAME}]>",
        f"<[string8][Pilot][{DEV_PILOT}]>",
    ):
        if fragment not in text:
            raise RuntimeError(f"Restored dev identity is missing: {fragment}")


def restore_local(force: bool) -> tuple[Path, str]:
    assert_aircraft_child(LOCAL_ROTORS, LOCAL_AIRCRAFT_ROOT, ROTORS_NAME)
    assert_aircraft_child(LOCAL_DEV, LOCAL_AIRCRAFT_ROOT, DEV_NAME)
    staging = LOCAL_AIRCRAFT_ROOT / f".{DEV_NAME}.rotors_restore_tmp"
    assert_aircraft_child(staging, LOCAL_AIRCRAFT_ROOT, f".{DEV_NAME}.rotors_restore_tmp")

    rotors_tmb = LOCAL_ROTORS / f"{ROTORS_NAME}.tmb"
    if not rotors_tmb.exists():
        raise FileNotFoundError(f"Missing local rotors package: {rotors_tmb}")
    rotors_tmb_hash = sha256(rotors_tmb)
    if LOCAL_DEV.exists() and not force:
        raise FileExistsError(f"Local dev package exists; rerun with --force: {LOCAL_DEV}")

    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(LOCAL_ROTORS, staging)
    rename_rotors_files(staging)
    patch_dev_identity(staging)
    validate_dev(staging, rotors_tmb_hash)

    if LOCAL_DEV.exists():
        shutil.rmtree(LOCAL_DEV)
    staging.rename(LOCAL_DEV)
    validate_dev(LOCAL_DEV, rotors_tmb_hash)
    return LOCAL_DEV, rotors_tmb_hash


def install_dev(user_root: Path, rotors_tmb_hash: str, force: bool) -> Path:
    aircraft_root = (user_root / "aircraft").resolve()
    target = aircraft_root / DEV_NAME
    staging = aircraft_root / f".{DEV_NAME}.rotors_restore_tmp"
    assert_aircraft_child(target, aircraft_root, DEV_NAME)
    assert_aircraft_child(staging, aircraft_root, f".{DEV_NAME}.rotors_restore_tmp")
    if target.exists() and not force:
        raise FileExistsError(f"Installed dev package exists; rerun with --force-install: {target}")

    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(LOCAL_DEV, staging)
    validate_dev(staging, rotors_tmb_hash)
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)
    validate_dev(target, rotors_tmb_hash)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore the preserved Wraith Rotors copy over Wraith Dev.")
    parser.add_argument("--force", action="store_true", help="Replace both local and installed dev outputs.")
    parser.add_argument("--install", action="store_true", help="Install the restored dev package to Aerofly FS 4.")
    parser.add_argument("--force-install", action="store_true", help="Replace the installed dev aircraft.")
    parser.add_argument("--user-root", type=Path, default=DEFAULT_USER_ROOT)
    args = parser.parse_args()

    try:
        restored, rotors_tmb_hash = restore_local(args.force)
        print(f"Restored local rotors copy to dev: {restored}")
        if args.install:
            installed = install_dev(args.user_root, rotors_tmb_hash, args.force or args.force_install)
            print(f"Installed restored dev package: {installed}")
    except (FileExistsError, FileNotFoundError, RuntimeError) as error:
        print(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
