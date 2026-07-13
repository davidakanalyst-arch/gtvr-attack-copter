from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEV_AIRCRAFT_NAME = "gtvr_wraith_dev"
ROTORS_AIRCRAFT_NAME = "gtvr_wraith_rotors"
ROTORS_DISPLAY_NAME = "GTVR Wraith Rotors"
ROTORS_ICAO = "GTWR"
ROTORS_PILOT = "pilot_jason"

LOCAL_PACKAGES = ROOT / "local-aircraft-packages"
DEV_PACKAGE_DIR = LOCAL_PACKAGES / DEV_AIRCRAFT_NAME
ROTORS_PACKAGE_DIR = LOCAL_PACKAGES / ROTORS_AIRCRAFT_NAME
DEFAULT_FS4_USER = Path.home() / "Documents" / "Aerofly FS 4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def replace_one(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not patch {label}.")
    return updated


def assert_package_name(path: Path, expected_name: str) -> None:
    if path.name != expected_name:
        raise RuntimeError(f"Unexpected aircraft package path: {path}")


def rename_aircraft_files(package_dir: Path) -> None:
    for child in list(package_dir.iterdir()):
        if not child.is_file():
            continue
        if not child.name.startswith(DEV_AIRCRAFT_NAME):
            continue
        new_name = f"{ROTORS_AIRCRAFT_NAME}{child.name[len(DEV_AIRCRAFT_NAME):]}"
        child.rename(package_dir / new_name)


def patch_rotors_tmc(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = replace_one(
        text,
        r"<\[stringt8c\]\[ICAO\]\[[^\]]+\]>",
        f"<[stringt8c][ICAO][{ROTORS_ICAO}]>",
        "ICAO",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[DisplayName\]\[[^\]]+\]>",
        f"<[string8][DisplayName][{ROTORS_DISPLAY_NAME}]>",
        "DisplayName",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[DisplayNameFull\]\[[^\]]+\]>",
        f"<[string8][DisplayNameFull][{ROTORS_DISPLAY_NAME}]>",
        "DisplayNameFull",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[Pilot\]\[[^\]]+\]>",
        f"<[string8][Pilot][{ROTORS_PILOT}]>",
        "Pilot",
    )
    path.write_text(text, encoding="utf-8")


def write_rotors_marker(package_dir: Path) -> None:
    for marker_name in ("_GTVR_WRAITH_DEV.txt", "_GTVR_WRAITH_EC135_CORE.txt"):
        marker = package_dir / marker_name
        if marker.exists():
            marker.unlink()
    (package_dir / "_GTVR_WRAITH_ROTORS.txt").write_text(
        "\n".join(
            [
                ROTORS_DISPLAY_NAME,
                "",
                f"Copied from {DEV_AIRCRAFT_NAME}.",
                "Separate installed aircraft package for rotor visual experiments.",
                f"Identity: {ROTORS_AIRCRAFT_NAME}, {ROTORS_ICAO}, {ROTORS_DISPLAY_NAME}.",
                f"Pilot remains {ROTORS_PILOT}.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def validate_rotors_package(package_dir: Path, dev_tmb_hash: str | None = None) -> None:
    assert_package_name(package_dir, ROTORS_AIRCRAFT_NAME)

    required = [
        package_dir / f"{ROTORS_AIRCRAFT_NAME}.tmc",
        package_dir / f"{ROTORS_AIRCRAFT_NAME}.tmb",
        package_dir / f"{ROTORS_AIRCRAFT_NAME}.tmq",
        package_dir / f"{ROTORS_AIRCRAFT_NAME}_clean.tmd",
        package_dir / f"{ROTORS_AIRCRAFT_NAME}_cold.tmd",
        package_dir / f"{ROTORS_AIRCRAFT_NAME}_landing.tmd",
        package_dir / f"{ROTORS_AIRCRAFT_NAME}_start.tmd",
        package_dir / f"{ROTORS_AIRCRAFT_NAME}_takeoff.tmd",
        package_dir / "controls.tmd",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Rotors package is missing required files: " + ", ".join(missing))

    dev_named_files = [path.name for path in package_dir.iterdir() if path.name.startswith(DEV_AIRCRAFT_NAME)]
    if dev_named_files:
        raise RuntimeError("Rotors package still contains dev-named files: " + ", ".join(dev_named_files))

    tmc_text = (package_dir / f"{ROTORS_AIRCRAFT_NAME}.tmc").read_text(
        encoding="utf-8",
        errors="replace",
    )
    expected_fragments = [
        f"<[stringt8c][ICAO][{ROTORS_ICAO}]>",
        f"<[string8][DisplayName][{ROTORS_DISPLAY_NAME}]>",
        f"<[string8][DisplayNameFull][{ROTORS_DISPLAY_NAME}]>",
        f"<[string8][Pilot][{ROTORS_PILOT}]>",
    ]
    for fragment in expected_fragments:
        if fragment not in tmc_text:
            raise RuntimeError(f"Rotors TMC validation failed, missing: {fragment}")
    if "GTVR Wraith Dev" in tmc_text or "GTWD" in tmc_text:
        raise RuntimeError("Rotors TMC still contains dev identity text.")

    rotors_tmb_hash = sha256(package_dir / f"{ROTORS_AIRCRAFT_NAME}.tmb")
    if dev_tmb_hash and rotors_tmb_hash != dev_tmb_hash:
        raise RuntimeError("Rotors TMB hash does not match the source dev TMB.")


def create_local_copy(force_local: bool) -> Path:
    assert_package_name(DEV_PACKAGE_DIR, DEV_AIRCRAFT_NAME)
    assert_package_name(ROTORS_PACKAGE_DIR, ROTORS_AIRCRAFT_NAME)
    if not DEV_PACKAGE_DIR.exists():
        raise FileNotFoundError(f"Missing dev package: {DEV_PACKAGE_DIR}")

    dev_tmb = DEV_PACKAGE_DIR / f"{DEV_AIRCRAFT_NAME}.tmb"
    if not dev_tmb.exists():
        raise FileNotFoundError(f"Missing dev TMB: {dev_tmb}")
    dev_tmb_hash = sha256(dev_tmb)

    if ROTORS_PACKAGE_DIR.exists():
        if not force_local:
            raise FileExistsError(f"Rotors package already exists, rerun with --force-local: {ROTORS_PACKAGE_DIR}")
        shutil.rmtree(ROTORS_PACKAGE_DIR)

    shutil.copytree(DEV_PACKAGE_DIR, ROTORS_PACKAGE_DIR)
    rename_aircraft_files(ROTORS_PACKAGE_DIR)
    patch_rotors_tmc(ROTORS_PACKAGE_DIR / f"{ROTORS_AIRCRAFT_NAME}.tmc")
    write_rotors_marker(ROTORS_PACKAGE_DIR)
    validate_rotors_package(ROTORS_PACKAGE_DIR, dev_tmb_hash)
    return ROTORS_PACKAGE_DIR


def install_rotors_package(user_root: Path, force_install: bool) -> Path:
    source_dir = ROTORS_PACKAGE_DIR
    aircraft_root = user_root / "aircraft"
    target_dir = aircraft_root / ROTORS_AIRCRAFT_NAME
    dev_target_dir = aircraft_root / DEV_AIRCRAFT_NAME

    assert_package_name(source_dir, ROTORS_AIRCRAFT_NAME)
    assert_package_name(target_dir, ROTORS_AIRCRAFT_NAME)
    if target_dir.resolve() == dev_target_dir.resolve():
        raise RuntimeError(f"Refusing to install rotors package over dev aircraft: {dev_target_dir}")
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing local rotors package: {source_dir}")
    validate_rotors_package(source_dir)

    if target_dir.exists():
        if not force_install:
            raise FileExistsError(f"Rotors install already exists, rerun with --force-install: {target_dir}")
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    validate_rotors_package(target_dir)
    return target_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a separate GTVR Wraith Rotors aircraft copy from the current dev package.",
    )
    parser.add_argument("--force", action="store_true", help="Replace both local and installed rotors package outputs.")
    parser.add_argument("--force-local", action="store_true", help="Replace local-aircraft-packages rotors output.")
    parser.add_argument("--install", action="store_true", help="Install the rotors package to Aerofly FS4.")
    parser.add_argument("--force-install", action="store_true", help="Replace the existing rotors FS4 install.")
    parser.add_argument(
        "--install-existing-local",
        action="store_true",
        help="Skip copying from dev locally and install the existing local rotors package.",
    )
    parser.add_argument("--user-root", type=Path, default=DEFAULT_FS4_USER)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    force_local = args.force or args.force_local
    force_install = args.force or args.force_install

    try:
        if args.install_existing_local:
            validate_rotors_package(ROTORS_PACKAGE_DIR)
            copied = ROTORS_PACKAGE_DIR
            print(f"Using existing local rotors package: {copied}")
        else:
            copied = create_local_copy(force_local)
            print(f"Created local rotors package: {copied}")

        if args.install:
            installed = install_rotors_package(args.user_root, force_install)
            print(f"Installed rotors package: {installed}")
    except (FileExistsError, FileNotFoundError, RuntimeError) as error:
        print(f"error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
