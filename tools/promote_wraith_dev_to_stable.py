from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEV_AIRCRAFT_NAME = "gtvr_wraith_dev"
STABLE_AIRCRAFT_NAME = "gtvr_wraith_ec135_core"
STABLE_DISPLAY_NAME = "GTVR Wraith"
STABLE_ICAO = "GTWE"
STABLE_PILOT = "pilot_jason"

CONTACT_SPHERES = (
    "( 1.896 1.128 -1.667 0.05) "
    "( 1.896 -1.128 -1.667 0.05) "
    "(-0.876 1.128 -1.668 0.05) "
    "(-0.876 -1.128 -1.668 0.05)"
)

LOCAL_PACKAGES = ROOT / "local-aircraft-packages"
DEV_PACKAGE_DIR = LOCAL_PACKAGES / DEV_AIRCRAFT_NAME
STABLE_PACKAGE_DIR = LOCAL_PACKAGES / STABLE_AIRCRAFT_NAME
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


def patch_stable_tmc(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = replace_one(
        text,
        r"<\[list_vector4_float64\]\[ContactSpheres\]\[[^\]]+\]>",
        f"<[list_vector4_float64][ContactSpheres][ {CONTACT_SPHERES} ]>",
        "contact spheres",
    )
    text = replace_one(
        text,
        r"<\[stringt8c\]\[ICAO\]\[[^\]]+\]>",
        f"<[stringt8c][ICAO][{STABLE_ICAO}]>",
        "ICAO",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[DisplayName\]\[[^\]]+\]>",
        f"<[string8][DisplayName][{STABLE_DISPLAY_NAME}]>",
        "DisplayName",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[DisplayNameFull\]\[[^\]]+\]>",
        f"<[string8][DisplayNameFull][{STABLE_DISPLAY_NAME}]>",
        "DisplayNameFull",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[Pilot\]\[[^\]]+\]>",
        f"<[string8][Pilot][{STABLE_PILOT}]>",
        "Pilot",
    )
    path.write_text(text, encoding="utf-8")


def rename_aircraft_files(package_dir: Path) -> None:
    for child in list(package_dir.iterdir()):
        if not child.is_file():
            continue
        if not child.name.startswith(DEV_AIRCRAFT_NAME):
            continue
        new_name = f"{STABLE_AIRCRAFT_NAME}{child.name[len(DEV_AIRCRAFT_NAME):]}"
        child.rename(package_dir / new_name)


def write_stable_marker(package_dir: Path) -> None:
    dev_marker = package_dir / "_GTVR_WRAITH_DEV.txt"
    if dev_marker.exists():
        dev_marker.unlink()
    (package_dir / "_GTVR_WRAITH_EC135_CORE.txt").write_text(
        "\n".join(
            [
                STABLE_DISPLAY_NAME,
                "",
                f"Promoted from {DEV_AIRCRAFT_NAME}.",
                "Keeps EC135 controls, flight model, sounds, TMQ and state files.",
                "Includes the current Wraith visual shell, matte black inward shell faces, and pilot/window alignment.",
                f"Stable identity remains {STABLE_AIRCRAFT_NAME}, {STABLE_ICAO}, {STABLE_DISPLAY_NAME}.",
                f"Pilot remains {STABLE_PILOT}.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def assert_package_name(path: Path, expected_name: str) -> None:
    if path.name != expected_name:
        raise RuntimeError(f"Unexpected aircraft package path: {path}")


def validate_stable_package(package_dir: Path, dev_tmb_hash: str | None = None) -> None:
    assert_package_name(package_dir, STABLE_AIRCRAFT_NAME)

    required = [
        package_dir / f"{STABLE_AIRCRAFT_NAME}.tmc",
        package_dir / f"{STABLE_AIRCRAFT_NAME}.tmb",
        package_dir / f"{STABLE_AIRCRAFT_NAME}.tmq",
        package_dir / f"{STABLE_AIRCRAFT_NAME}_clean.tmd",
        package_dir / f"{STABLE_AIRCRAFT_NAME}_cold.tmd",
        package_dir / f"{STABLE_AIRCRAFT_NAME}_landing.tmd",
        package_dir / f"{STABLE_AIRCRAFT_NAME}_start.tmd",
        package_dir / f"{STABLE_AIRCRAFT_NAME}_takeoff.tmd",
        package_dir / "gtvr_inner_matte_black.ttx",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Stable package is missing required files: " + ", ".join(missing))

    dev_named_files = [path.name for path in package_dir.iterdir() if path.name.startswith(DEV_AIRCRAFT_NAME)]
    if dev_named_files:
        raise RuntimeError("Stable package still contains dev-named files: " + ", ".join(dev_named_files))

    tmc_text = (package_dir / f"{STABLE_AIRCRAFT_NAME}.tmc").read_text(encoding="utf-8", errors="replace")
    expected_fragments = [
        f"<[stringt8c][ICAO][{STABLE_ICAO}]>",
        f"<[string8][DisplayName][{STABLE_DISPLAY_NAME}]>",
        f"<[string8][DisplayNameFull][{STABLE_DISPLAY_NAME}]>",
        f"<[string8][Pilot][{STABLE_PILOT}]>",
        f"<[list_vector4_float64][ContactSpheres][ {CONTACT_SPHERES} ]>",
    ]
    for fragment in expected_fragments:
        if fragment not in tmc_text:
            raise RuntimeError(f"Stable TMC validation failed, missing: {fragment}")
    if DEV_AIRCRAFT_NAME in tmc_text or "GTVR Wraith Dev" in tmc_text or "GTWD" in tmc_text:
        raise RuntimeError("Stable TMC still contains dev identity text.")

    stable_tmb_hash = sha256(package_dir / f"{STABLE_AIRCRAFT_NAME}.tmb")
    if dev_tmb_hash and stable_tmb_hash != dev_tmb_hash:
        raise RuntimeError("Stable TMB hash does not match the promoted dev TMB.")


def promote_local(force_local: bool) -> Path:
    assert_package_name(DEV_PACKAGE_DIR, DEV_AIRCRAFT_NAME)
    assert_package_name(STABLE_PACKAGE_DIR, STABLE_AIRCRAFT_NAME)
    if not DEV_PACKAGE_DIR.exists():
        raise FileNotFoundError(f"Missing dev package: {DEV_PACKAGE_DIR}")

    dev_tmb = DEV_PACKAGE_DIR / f"{DEV_AIRCRAFT_NAME}.tmb"
    if not dev_tmb.exists():
        raise FileNotFoundError(f"Missing dev TMB: {dev_tmb}")
    dev_tmb_hash = sha256(dev_tmb)

    if STABLE_PACKAGE_DIR.exists():
        if not force_local:
            raise FileExistsError(f"Stable package already exists, rerun with --force-local: {STABLE_PACKAGE_DIR}")
        shutil.rmtree(STABLE_PACKAGE_DIR)

    shutil.copytree(DEV_PACKAGE_DIR, STABLE_PACKAGE_DIR)
    rename_aircraft_files(STABLE_PACKAGE_DIR)
    patch_stable_tmc(STABLE_PACKAGE_DIR / f"{STABLE_AIRCRAFT_NAME}.tmc")
    write_stable_marker(STABLE_PACKAGE_DIR)
    validate_stable_package(STABLE_PACKAGE_DIR, dev_tmb_hash)
    return STABLE_PACKAGE_DIR


def install_stable_package(user_root: Path, force_install: bool) -> Path:
    source_dir = STABLE_PACKAGE_DIR
    target_dir = user_root / "aircraft" / STABLE_AIRCRAFT_NAME
    dev_target_dir = user_root / "aircraft" / DEV_AIRCRAFT_NAME

    assert_package_name(source_dir, STABLE_AIRCRAFT_NAME)
    assert_package_name(target_dir, STABLE_AIRCRAFT_NAME)
    if target_dir.resolve() == dev_target_dir.resolve():
        raise RuntimeError(f"Refusing to install stable package over dev aircraft: {dev_target_dir}")
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing promoted stable package: {source_dir}")
    validate_stable_package(source_dir)

    if target_dir.exists():
        if not force_install:
            raise FileExistsError(f"Stable install already exists, rerun with --force-install: {target_dir}")
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    validate_stable_package(target_dir)
    return target_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promote the current GTVR Wraith Dev package to the stable GTVR Wraith package.",
    )
    parser.add_argument("--force", action="store_true", help="Replace both local and installed stable package outputs.")
    parser.add_argument("--force-local", action="store_true", help="Replace local-aircraft-packages stable output.")
    parser.add_argument("--install", action="store_true", help="Install the promoted stable package to Aerofly FS4.")
    parser.add_argument("--force-install", action="store_true", help="Replace the existing stable FS4 install.")
    parser.add_argument(
        "--install-existing-local",
        action="store_true",
        help="Skip copying from dev locally and install the already promoted local stable package.",
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
            validate_stable_package(STABLE_PACKAGE_DIR)
            promoted = STABLE_PACKAGE_DIR
            print(f"Using existing promoted stable package: {promoted}")
        else:
            promoted = promote_local(force_local)
            print(f"Promoted dev package to local stable package: {promoted}")

        if args.install:
            installed = install_stable_package(args.user_root, force_install)
            print(f"Installed stable package: {installed}")
    except (FileExistsError, FileNotFoundError, RuntimeError) as error:
        print(f"error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
