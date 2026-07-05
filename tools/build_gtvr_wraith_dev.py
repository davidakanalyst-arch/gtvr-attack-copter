from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import build_gtvr_wraith_ec135_core as core


ROOT = Path(__file__).resolve().parents[1]

STABLE_AIRCRAFT_NAME = "gtvr_wraith_ec135_core"
DEV_AIRCRAFT_NAME = "gtvr_wraith_dev"
DEV_DISPLAY_NAME = "GTVR Wraith Dev"
DEV_ICAO = "GTWD"

DEV_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_dev_source" / "aircraft"
DEV_SOURCE_DIR = DEV_SOURCE_ROOT / DEV_AIRCRAFT_NAME
DEV_BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_dev_build_user"
DEV_LAUNCH_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_dev_launch"
DEV_PACKAGE_DIR = ROOT / "local-aircraft-packages" / DEV_AIRCRAFT_NAME
DEV_SOURCE_STAMP = DEV_SOURCE_DIR / "_GTVR_WRAITH_DEV_SOURCE_STAMP.txt"

DEFAULT_FS4_USER = Path.home() / "Documents" / "Aerofly FS 4"

_ORIGINAL_PATCH_TMC = core.patch_tmc


def patch_dev_tmc(path: Path) -> None:
    _ORIGINAL_PATCH_TMC(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("<[stringt8c][ICAO][GTWE]>", f"<[stringt8c][ICAO][{DEV_ICAO}]>", 1)
    path.write_text(text, encoding="utf-8")


def configure_core_for_dev() -> None:
    core.AIRCRAFT_NAME = DEV_AIRCRAFT_NAME
    core.DISPLAY_NAME = DEV_DISPLAY_NAME
    core.SOURCE_ROOT = DEV_SOURCE_ROOT
    core.SOURCE_DIR = DEV_SOURCE_DIR
    core.BUILD_USER = DEV_BUILD_USER
    core.PACKAGE_DIR = DEV_PACKAGE_DIR
    core.patch_tmc = patch_dev_tmc
    assert_dev_paths()


def assert_dev_paths() -> None:
    checked_paths = [
        core.SOURCE_ROOT,
        core.SOURCE_DIR,
        core.BUILD_USER,
        core.PACKAGE_DIR,
        DEV_LAUNCH_USER,
    ]
    for path in checked_paths:
        if STABLE_AIRCRAFT_NAME in path.parts:
            raise RuntimeError(f"Dev builder path points at stable output: {path}")
    if core.PACKAGE_DIR.name != DEV_AIRCRAFT_NAME:
        raise RuntimeError(f"Unexpected dev package directory: {core.PACKAGE_DIR}")
    if core.SOURCE_DIR.name != DEV_AIRCRAFT_NAME:
        raise RuntimeError(f"Unexpected dev source directory: {core.SOURCE_DIR}")


def converted_tmb() -> Path:
    return DEV_BUILD_USER / "aircraft" / DEV_AIRCRAFT_NAME / f"{DEV_AIRCRAFT_NAME}.tmb"


def write_source_stamp() -> None:
    DEV_SOURCE_STAMP.write_text(
        "\n".join(
            [
                "GTVR Wraith Dev source prepared.",
                f"aircraft={DEV_AIRCRAFT_NAME}",
                f"display={DEV_DISPLAY_NAME}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def assert_fresh_converted_tmb(allow_stale_tmb: bool) -> None:
    if allow_stale_tmb:
        return

    tmb_path = converted_tmb()
    if not tmb_path.exists():
        raise FileNotFoundError(
            f"Missing dev converter output: {tmb_path}. "
            "Run --convert or the printed Aerofly converter command before assembling."
        )
    if not DEV_SOURCE_STAMP.exists():
        raise FileNotFoundError(
            f"Missing dev source stamp: {DEV_SOURCE_STAMP}. "
            "Run --prepare-source before assembling, or pass --allow-stale-tmb intentionally."
        )
    if tmb_path.stat().st_mtime < DEV_SOURCE_STAMP.stat().st_mtime:
        raise RuntimeError(
            f"Refusing to assemble stale dev TMB: {tmb_path} is older than {DEV_SOURCE_STAMP}. "
            "Run the full converter with --convert, or pass --allow-stale-tmb intentionally."
        )


def run_converter(timeout: float) -> int:
    command = [
        sys.executable,
        str(ROOT / "tools" / "run_aerofly_converter.py"),
        DEV_AIRCRAFT_NAME,
        str(DEV_SOURCE_ROOT),
        "--userfolder",
        str(DEV_LAUNCH_USER),
        "--timeout",
        str(timeout),
    ]
    print("Running full Aerofly converter for GTVR Wraith Dev:")
    print(" ".join(command))
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


def write_dev_package_marker() -> None:
    stable_marker = DEV_PACKAGE_DIR / "_GTVR_WRAITH_EC135_CORE.txt"
    if stable_marker.exists():
        stable_marker.unlink()
    (DEV_PACKAGE_DIR / "_GTVR_WRAITH_DEV.txt").write_text(
        "\n".join(
            [
                DEV_DISPLAY_NAME,
                "",
                "Dev-only EC135-core Wraith iteration package.",
                "The package keeps EC135 controls, flight model, sounds, TMQ and state files.",
                "Only the dev aircraft identity and compiled visual TMB are replaced.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def install_dev_package(user_root: Path, force_install: bool) -> Path:
    source_dir = DEV_PACKAGE_DIR
    target_dir = user_root / "aircraft" / DEV_AIRCRAFT_NAME
    stable_dir = user_root / "aircraft" / STABLE_AIRCRAFT_NAME

    if target_dir.name != DEV_AIRCRAFT_NAME:
        raise RuntimeError(f"Refusing to install dev package to unexpected folder: {target_dir}")
    if target_dir.resolve() == stable_dir.resolve():
        raise RuntimeError(f"Refusing to install dev package over stable aircraft: {stable_dir}")
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing assembled dev package: {source_dir}")
    if target_dir.exists():
        if not force_install:
            raise FileExistsError(f"Dev install already exists, rerun with --force-install: {target_dir}")
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    return target_dir


def add_core_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--preset", choices=sorted(core.PRESETS), default="uh60")
    parser.add_argument("--msfs-dir", type=Path, default=core.DEFAULT_MSFS_HELI_DIR)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--gltf")
    parser.add_argument("--max-faces", type=int, default=core.DEFAULT_MAX_FACES)
    parser.add_argument("--max-texture-size", type=int, default=1024)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--skip-node-regex", default=core.DEFAULT_BODY_SKIP_NODE_REGEX)
    parser.add_argument("--skip-material-regex", default=core.DEFAULT_SKIP_MATERIAL_REGEX)
    parser.add_argument("--visual-ground-z", type=float, default=core.VISUAL_TARGET_GROUND_Z)
    parser.add_argument("--visual-body-lift", type=float, default=core.VISUAL_BODY_LIFT)
    parser.add_argument("--visual-gear-min-z", type=float, default=core.VISUAL_GEAR_MIN_Z)
    parser.add_argument("--rear-visual-gear-x", type=float, default=core.REAR_FUSELAGE_GEAR_X)
    parser.add_argument("--rear-visual-gear-z-offset", type=float, default=core.REAR_VISUAL_GEAR_Z_OFFSET)
    parser.add_argument("--visual-x-offset", type=float, default=core.VISUAL_X_OFFSET)
    parser.add_argument("--visual-y-offset", type=float, default=core.VISUAL_Y_OFFSET)
    parser.add_argument("--low-non-tire-z-cutoff", type=float, default=core.LOW_NON_TIRE_Z_CUTOFF)
    parser.add_argument("--no-yaw-180", dest="yaw_180", action="store_false")
    parser.set_defaults(yaw_180=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dev-only build/install pipeline for GTVR Wraith Dev.",
    )
    add_core_args(parser)
    parser.add_argument("--prepare-source", action="store_true")
    parser.add_argument("--convert", action="store_true", help="Run the full Aerofly converter for the dev source.")
    parser.add_argument("--assemble-package", action="store_true")
    parser.add_argument("--install", action="store_true", help="Install only to the gtvr_wraith_dev FS4 folder.")
    parser.add_argument("--full", action="store_true", help="Prepare, convert, assemble and install the dev package.")
    parser.add_argument("--force-install", action="store_true", help="Replace the existing gtvr_wraith_dev install.")
    parser.add_argument("--allow-stale-tmb", action="store_true", help="Allow assembling without a fresh dev converter run.")
    parser.add_argument("--user-root", type=Path, default=DEFAULT_FS4_USER)
    parser.add_argument("--converter-timeout", type=float, default=180.0)
    return parser


def main() -> int:
    configure_core_for_dev()
    parser = build_parser()
    args = parser.parse_args()

    if args.full:
        args.prepare_source = True
        args.convert = True
        args.assemble_package = True
        args.install = True

    requested_actions = [args.prepare_source, args.convert, args.assemble_package, args.install]
    if not any(requested_actions):
        parser.print_help()
        print("")
        print("Recommended dev iteration:")
        print("  python tools\\build_gtvr_wraith_dev.py --full --force-install")
        return 0

    try:
        if args.prepare_source:
            core.prepare_source(args)
            write_source_stamp()

        if args.convert:
            result = run_converter(args.converter_timeout)
            if result != 0:
                return result

        if args.assemble_package:
            assert_fresh_converted_tmb(args.allow_stale_tmb)
            core.assemble_package(args)
            write_dev_package_marker()

        if args.install:
            installed = install_dev_package(args.user_root, args.force_install)
            print(f"Installed dev package: {installed}")
    except (FileExistsError, FileNotFoundError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
