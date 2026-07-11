from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import build_gtvr_wraith_dev as dev
import build_gtvr_wraith_ec135_core as core


ROOT = Path(__file__).resolve().parents[1]

TEXT_AIRCRAFT_NAME = "gtvr_wraith_text"
TEXT_DISPLAY_NAME = "GTVR Wraith Text"
TEXT_ICAO = "GTWT"
TEXT_PILOT = "pilot_jason"

STABLE_AIRCRAFT_NAME = "gtvr_wraith_ec135_core"
DEV_AIRCRAFT_NAME = "gtvr_wraith_dev"
DEFAULT_FS4_USER = Path.home() / "Documents" / "Aerofly FS 4"

STOCK_DR400 = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator\aircraft\dr400")
TEXT_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_text_source" / "aircraft"
TEXT_SOURCE_DIR = TEXT_SOURCE_ROOT / TEXT_AIRCRAFT_NAME
TEXT_BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_text_build_user"
TEXT_LAUNCH_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_text_launch"
TEXT_PACKAGE_DIR = ROOT / "local-aircraft-packages" / TEXT_AIRCRAFT_NAME
TEXT_SOURCE_STAMP = TEXT_SOURCE_DIR / "_GTVR_WRAITH_TEXT_SOURCE_STAMP.txt"

DR400_ROOT_NAME = "dr400"
DR400_MAP_TEXTURE = dev.CENTER_MAP_TEXTURE
DR400_CENTER_MAP_GEOMETRY = "GPSDisp"
TEXT_MARKER = "_GTVR_WRAITH_TEXT.txt"

ROTOR_TEST_PIVOT = "0.2 0.0 2.55"


def configure_dev_geometry_for_text() -> None:
    """Point the accepted Wraith dev geometry generator at the text-test source tree."""

    dev.DEV_AIRCRAFT_NAME = TEXT_AIRCRAFT_NAME
    dev.DEV_DISPLAY_NAME = TEXT_DISPLAY_NAME
    dev.DEV_ICAO = TEXT_ICAO
    dev.DEV_PILOT = TEXT_PILOT
    dev.DEV_SOURCE_ROOT = TEXT_SOURCE_ROOT
    dev.DEV_SOURCE_DIR = TEXT_SOURCE_DIR
    dev.DEV_BUILD_USER = TEXT_BUILD_USER
    dev.DEV_LAUNCH_USER = TEXT_LAUNCH_USER
    dev.DEV_PACKAGE_DIR = TEXT_PACKAGE_DIR
    dev.DEV_SOURCE_STAMP = TEXT_SOURCE_STAMP
    dev.configure_core_for_dev()


def extract_geometry_names(tmd_path: Path) -> list[str]:
    text = tmd_path.read_text(encoding="utf-8", errors="replace")
    names: set[str] = set()
    for match in re.finditer(r"<\[string8\]\[Geometry(?:List)?\]\[([^\]]*)\]>", text, flags=re.DOTALL):
        for token in re.split(r"\s+", match.group(1).strip()):
            if token:
                names.add(token)
    return sorted(names)


def merge_patch_maps(*patch_maps: dict[str, core.Patch]) -> dict[str, core.Patch]:
    merged: dict[str, core.Patch] = {}
    for patch_map in patch_maps:
        for material_name, source in patch_map.items():
            target = merged.setdefault(material_name, core.Patch(material_name))
            vertex_offset = len(target.vertices) // 8
            target.vertices.extend(source.vertices)
            target.indices.extend(index + vertex_offset for index in source.indices)
            target.face_attributes.extend(source.face_attributes)
    return merged


def dummy_geometry() -> dict[str, core.Patch]:
    patch = core.Patch("gtvr_cockpit_black")
    points = [
        (0.0, 0.0, -0.25),
        (0.004, 0.0, -0.25),
        (0.0, 0.004, -0.25),
        (0.0, 0.0, -0.246),
    ]
    for point in points:
        patch.vertices.extend([point[0], point[1], point[2], 0.0, 0.0, 1.0, 0.5, 0.5])
    for face in ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)):
        patch.indices.extend(face)
        patch.face_attributes.append(0)
    return {patch.material_name: patch}


def converted_tmb() -> Path:
    return TEXT_BUILD_USER / "aircraft" / TEXT_AIRCRAFT_NAME / f"{TEXT_AIRCRAFT_NAME}.tmb"


def prepare_source(args: argparse.Namespace) -> None:
    configure_dev_geometry_for_text()

    donor_tmd = STOCK_DR400 / f"{DR400_ROOT_NAME}.tmd"
    if not donor_tmd.exists():
        raise FileNotFoundError(f"Missing DR400 donor TMD: {donor_tmd}")

    if TEXT_SOURCE_DIR.exists():
        shutil.rmtree(TEXT_SOURCE_DIR)
    TEXT_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    core.ensure_runtime_resources(TEXT_SOURCE_ROOT)

    materials, body, tail_rotor, visual_gear, _source_faces, imported_faces = dev.build_body_for_dev(args)
    visible_fuselage = merge_patch_maps(body, visual_gear)
    center_map_surface = dev._current_stock_display_geometries.get("DisplayNDL")
    if not center_map_surface:
        raise RuntimeError("Wraith centre map surface was not generated.")

    donor_geometries = extract_geometry_names(donor_tmd)
    dummy = dummy_geometry()
    geometries: dict[str, dict[str, core.Patch]] = {}
    for geometry_name in donor_geometries:
        if geometry_name == "Fuselage":
            geometries[geometry_name] = core.copy_patch_map(visible_fuselage)
        elif geometry_name == DR400_CENTER_MAP_GEOMETRY:
            geometries[geometry_name] = core.copy_patch_map(center_map_surface)
        else:
            geometries[geometry_name] = core.copy_patch_map(dummy)

    core.write_aircraft_source_tmc(TEXT_SOURCE_DIR / f"{TEXT_AIRCRAFT_NAME}.tmc")
    core.write_minimal_tmd(TEXT_SOURCE_DIR / f"{TEXT_AIRCRAFT_NAME}.tmd", sorted(geometries))
    tgi_path = TEXT_SOURCE_DIR / f"{TEXT_AIRCRAFT_NAME}.tgi"
    core.write_tgi(tgi_path, materials, geometries)
    patched_materials, surface_slots = dev.patch_dev_tgi_material_shaders(tgi_path)
    core.write_model_tmc(TEXT_SOURCE_DIR / "model.tmc", materials, geometries, args.max_texture_size)
    core.write_root_converter_config(TEXT_SOURCE_ROOT / "config.tmc", TEXT_SOURCE_ROOT, TEXT_BUILD_USER)
    TEXT_SOURCE_STAMP.write_text(
        "\n".join(
            [
                "GTVR Wraith Text source prepared.",
                f"aircraft={TEXT_AIRCRAFT_NAME}",
                f"display={TEXT_DISPLAY_NAME}",
                f"donor=text DR400 graph at {STOCK_DR400}",
                "center_map=DR400 native texture_animation_map_display is targeted at the Wraith centre map texture",
                f"dr400_geometry_names={len(donor_geometries)}",
                f"imported_faces={imported_faces}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote text Wraith source: {TEXT_SOURCE_DIR}")
    print(f"DR400 geometry names emitted: {len(geometries)}")
    if patched_materials:
        print(f"Text cockpit materials: forced {patched_materials} generated interior/control shaders.")
    if surface_slots:
        print(f"Text cockpit materials: added {surface_slots} explicit specular/reflection slots.")


def run_converter(timeout: float) -> int:
    command = [
        sys.executable,
        str(ROOT / "tools" / "run_aerofly_converter.py"),
        TEXT_AIRCRAFT_NAME,
        str(TEXT_SOURCE_ROOT),
        "--userfolder",
        str(TEXT_LAUNCH_USER),
        "--timeout",
        str(timeout),
    ]
    print(f"Running full Aerofly converter for {TEXT_DISPLAY_NAME}:")
    print(" ".join(command))
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


def assert_fresh_converted_tmb(allow_stale_tmb: bool) -> None:
    if allow_stale_tmb:
        return
    tmb_path = converted_tmb()
    if not tmb_path.exists():
        raise FileNotFoundError(f"Missing text converter output: {tmb_path}")
    if not TEXT_SOURCE_STAMP.exists():
        raise FileNotFoundError(f"Missing text source stamp: {TEXT_SOURCE_STAMP}")
    if tmb_path.stat().st_mtime < TEXT_SOURCE_STAMP.stat().st_mtime:
        raise RuntimeError(
            f"Refusing to assemble stale text TMB: {tmb_path} is older than {TEXT_SOURCE_STAMP}. "
            "Run --convert or pass --allow-stale-tmb intentionally."
        )


def patch_tmc(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"<\[stringt8c\]\[ICAO\]\[[^\]]*\]>", f"<[stringt8c][ICAO][{TEXT_ICAO}]>", text, count=1)
    text = re.sub(r"<\[string8\]\[DisplayName\]\[[^\]]*\]>", f"<[string8][DisplayName][{TEXT_DISPLAY_NAME}]>", text, count=1)
    text = re.sub(
        r"<\[string8\]\[DisplayNameFull\]\[[^\]]*\]>",
        f"<[string8][DisplayNameFull][{TEXT_DISPLAY_NAME}]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[string8\]\[Tags\]\[[^\]]*\]>",
        "<[string8][Tags][ airplane helicopter experimental military text-map ]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[string8\]\[Pilot\]\[[^\]]*\]>",
        f"<[string8][Pilot][{TEXT_PILOT}]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[list_vector4_float64\]\[ContactSpheres\]\[[^\]]*\]>",
        f"<[list_vector4_float64][ContactSpheres][ {core.LOW_CONTACT_SPHERES} ]>",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def replace_block(text: str, header: str, replacements: dict[str, str]) -> str:
    start = text.find(header)
    if start == -1:
        raise ValueError(f"Could not find TMD block: {header}")
    next_block = re.search(r"\n\s{12}<\[[^\]]+\]\[[^\]]+\]\[\]", text[start + len(header) :])
    if next_block is None:
        raise ValueError(f"Could not find end of TMD block: {header}")
    end = start + len(header) + next_block.start()
    block = text[start:end]
    for old, new in replacements.items():
        if old not in block:
            raise ValueError(f"Could not patch {header}; missing: {old}")
        block = block.replace(old, new, 1)
    return text[:start] + block + text[end:]


def patch_tmd_for_center_map(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("Robin DR 400", TEXT_DISPLAY_NAME)
    text = text.replace("Robin DR400", TEXT_DISPLAY_NAME)
    text = text.replace("DR400", TEXT_DISPLAY_NAME)

    text = replace_block(
        text,
        "<[texture_animation][DisplayTexture][]",
        {"<[string8][TextureName][display_light]>": f"<[string8][TextureName][{DR400_MAP_TEXTURE}]>"},
    )
    text = text.replace(
        "<[tmvector2d][TargetPosition][    9  477 ]>",
        "<[tmvector2d][TargetPosition][    0    0 ]>",
        1,
    )
    text = text.replace("<[tmvector2d][TargetSize]    [  600  392 ]>", "<[tmvector2d][TargetSize]    [ 1024 1024 ]>", 2)
    text = text.replace(
        "<[tmvector2d][TargetScale]   [ 1024 1024 ]>",
        "<[tmvector2d][TargetScale]   [ 1024 1024 ]>",
        2,
    )
    text = text.replace(
        "<[tmvector3d][Color]         [ 0.7 0.7 0.7 ]>",
        "<[tmvector3d][Color]         [ 1.0 1.0 1.0 ]>",
        1,
    )

    # Flight viability gate: the map-capable text route is only worth pursuing if it can be
    # made to lift like a rotorcraft.  Keep this deliberately blunt and reversible: rotate the
    # DR400 propeller/engine axis upward, enlarge it to main-rotor scale, and give the piston
    # graph enough power to prove whether a hover/lift path exists before polishing displays.
    text = replace_block(
        text,
        "<[rigidbody][PropellerBody][]",
        {
            "<[float64][Mass][10.0]>": "<[float64][Mass][24.0]>",
            "<[tmvector3d][InertiaLength][ 0.2 0.2 1.60 ]>": "<[tmvector3d][InertiaLength][ 4.8 4.8 0.2 ]>",
            "<[tmvector3d][R0][ 1.97347 0.0 0.53221 ]>": f"<[tmvector3d][R0][ {ROTOR_TEST_PIVOT} ]>",
        },
    )
    text = replace_block(
        text,
        "<[multibody_joint][PropellerJoint][]",
        {
            "<[tmvector3d][R0][ 1.97347 0.0 0.53221 ]>": f"<[tmvector3d][R0][ {ROTOR_TEST_PIVOT} ]>",
            "<[tmvector3d][X0][ 1.0 0.0 0.0 ]>": "<[tmvector3d][X0][ 0.0 0.0 1.0 ]>",
            "<[float64][InitialVelocity][63.0]>": "<[float64][InitialVelocity][90.0]>",
        },
    )
    text = replace_block(
        text,
        "<[jointtorque][DriveShaft][]",
        {"<[tmvector3d][Z0][ 1.0 0.0 0.0 ]>": "<[tmvector3d][Z0][ 0.0 0.0 1.0 ]>"},
    )
    text = replace_block(
        text,
        "<[propeller][Propeller][]",
        {
            "<[tmvector3d][R0][ 1.97 0.00023 0.53225 ]>": f"<[tmvector3d][R0][ {ROTOR_TEST_PIVOT} ]>",
            "<[tmvector3d][X0][ 1.0 0.0 0.0 ]>": "<[tmvector3d][X0][ 0.0 0.0 1.0 ]>",
            "<[tmvector3d][Y0][ 0.0 1.0 0.0 ]>": "<[tmvector3d][Y0][ 1.0 0.0 0.0 ]>",
            "<[tmvector3d][Z0][ 0.0 0.0 1.0 ]>": "<[tmvector3d][Z0][ 0.0 1.0 0.0 ]>",
            "<[uint32][NumberBlades][2]>": "<[uint32][NumberBlades][4]>",
            "<[float64][Radius]      [0.9398]>": "<[float64][Radius]      [4.8]>",
            "<[float64][Pitch]       [1.6256]>": "<[float64][Pitch]       [1.05]>",
            "<[float64][CutOut]      [0.2]>": "<[float64][CutOut]      [0.08]>",
        },
    )
    text = replace_block(
        text,
        "<[engine2][Engine][]",
        {
            "<[float64][Friction][40.0]>": "<[float64][Friction][20.0]>",
            "<[float64][RatedRotationSpeed][282.7]>": "<[float64][RatedRotationSpeed][90.0]>",
            "<[float64][RatedPower][119200.0]>": "<[float64][RatedPower][520000.0]>",
        },
    )
    text = replace_block(
        text,
        "<[rotatingbodygraphics][Spinner][]",
        {
            "<[tmvector3d][Axis][ 1.0 0.0 0.0 ]>": "<[tmvector3d][Axis][ 0.0 0.0 1.0 ]>",
            "<[tmvector3d][Pivot][ 1.97 0.00023 0.53225 ]>": f"<[tmvector3d][Pivot][ {ROTOR_TEST_PIVOT} ]>",
        },
    )
    text = replace_block(
        text,
        "<[graphics_propeller_blade][PropellerBlade][]",
        {
            "<[tmvector3d][Axis][ 1.0 0.0 0.0 ]>": "<[tmvector3d][Axis][ 0.0 0.0 1.0 ]>",
            "<[tmvector3d][Pivot][ 1.97 0.00023 0.53225 ]>": f"<[tmvector3d][Pivot][ {ROTOR_TEST_PIVOT} ]>",
            "<[float64][Radius][0.955575]>": "<[float64][Radius][4.8]>",
        },
    )
    text = replace_block(
        text,
        "<[propellergraphics][Propeller][]",
        {
            "<[tmvector3d][Axis][ 1.0 0.0 0.0 ]>": "<[tmvector3d][Axis][ 0.0 0.0 1.0 ]>",
            "<[tmvector3d][Pivot][ 1.97 0.00023 0.53225 ]>": f"<[tmvector3d][Pivot][ {ROTOR_TEST_PIVOT} ]>",
            "<[uint32][BladeNumber][2]>": "<[uint32][BladeNumber][4]>",
            "<[float64][Radius][0.955575]>": "<[float64][Radius][4.8]>",
            "<[float64][BladePitch][-0.5]>": "<[float64][BladePitch][0.15]>",
        },
    )

    path.write_text(text, encoding="utf-8")


def rename_dr400_root_files(package_dir: Path) -> None:
    rename_pairs = {
        f"{DR400_ROOT_NAME}.tmc": f"{TEXT_AIRCRAFT_NAME}.tmc",
        f"{DR400_ROOT_NAME}.tmd": f"{TEXT_AIRCRAFT_NAME}.tmd",
        f"{DR400_ROOT_NAME}_clean.tmd": f"{TEXT_AIRCRAFT_NAME}_clean.tmd",
        f"{DR400_ROOT_NAME}_cold.tmd": f"{TEXT_AIRCRAFT_NAME}_cold.tmd",
        f"{DR400_ROOT_NAME}_doors.tmd": f"{TEXT_AIRCRAFT_NAME}_doors.tmd",
        f"{DR400_ROOT_NAME}_flaps.tmd": f"{TEXT_AIRCRAFT_NAME}_flaps.tmd",
        f"{DR400_ROOT_NAME}_landing.tmd": f"{TEXT_AIRCRAFT_NAME}_landing.tmd",
        f"{DR400_ROOT_NAME}_start.tmd": f"{TEXT_AIRCRAFT_NAME}_start.tmd",
        f"{DR400_ROOT_NAME}_takeoff.tmd": f"{TEXT_AIRCRAFT_NAME}_takeoff.tmd",
    }
    for old_name, new_name in rename_pairs.items():
        old_path = package_dir / old_name
        if old_path.exists():
            old_path.rename(package_dir / new_name)
    donor_tmb = package_dir / f"{DR400_ROOT_NAME}.tmb"
    if donor_tmb.exists():
        donor_tmb.unlink()


def assemble_package(_: argparse.Namespace) -> None:
    if not STOCK_DR400.exists():
        raise FileNotFoundError(f"Stock DR400 not found: {STOCK_DR400}")
    source_tmb = converted_tmb()
    if not source_tmb.exists():
        raise FileNotFoundError(f"Missing converted text TMB: {source_tmb}")

    if TEXT_PACKAGE_DIR.exists():
        shutil.rmtree(TEXT_PACKAGE_DIR)
    shutil.copytree(STOCK_DR400, TEXT_PACKAGE_DIR, ignore=shutil.ignore_patterns(".git", ".github"))
    rename_dr400_root_files(TEXT_PACKAGE_DIR)

    shutil.copy2(source_tmb, TEXT_PACKAGE_DIR / f"{TEXT_AIRCRAFT_NAME}.tmb")
    for texture in source_tmb.parent.glob("*.ttx"):
        shutil.copy2(texture, TEXT_PACKAGE_DIR / texture.name)

    patch_tmc(TEXT_PACKAGE_DIR / f"{TEXT_AIRCRAFT_NAME}.tmc")
    patch_tmd_for_center_map(TEXT_PACKAGE_DIR / f"{TEXT_AIRCRAFT_NAME}.tmd")
    (TEXT_PACKAGE_DIR / TEXT_MARKER).write_text(
        "\n".join(
            [
                TEXT_DISPLAY_NAME,
                "",
                "Experimental text-TMD Wraith map test package.",
                "Donor graph: stock DR400 text TMD, selected because its native moving-map renderer is readable.",
                "Visual model: generated Wraith shell/cockpit compiled against DR400 geometry names.",
                "Center map: DR400 texture_animation_map_display renders directly into the Wraith centre map texture.",
                "This package is intentionally separate from gtvr_wraith_dev and stable.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Assembled text package: {TEXT_PACKAGE_DIR}")


def install_package(user_root: Path, force_install: bool) -> Path:
    source_dir = TEXT_PACKAGE_DIR
    target_dir = user_root / "aircraft" / TEXT_AIRCRAFT_NAME
    forbidden = [
        user_root / "aircraft" / DEV_AIRCRAFT_NAME,
        user_root / "aircraft" / STABLE_AIRCRAFT_NAME,
    ]
    if target_dir.name != TEXT_AIRCRAFT_NAME:
        raise RuntimeError(f"Refusing to install text package to unexpected folder: {target_dir}")
    for forbidden_dir in forbidden:
        if target_dir.resolve() == forbidden_dir.resolve():
            raise RuntimeError(f"Refusing to install text package over protected aircraft: {forbidden_dir}")
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing assembled text package: {source_dir}")
    if target_dir.exists():
        if not force_install:
            raise FileExistsError(f"Text install already exists, rerun with --force-install: {target_dir}")
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    return target_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Build/install the experimental {TEXT_DISPLAY_NAME} text-TMD target.")
    dev.add_core_args(parser)
    parser.add_argument("--prepare-source", action="store_true")
    parser.add_argument("--convert", action="store_true", help=f"Run the full Aerofly converter for {TEXT_AIRCRAFT_NAME}.")
    parser.add_argument("--assemble-package", action="store_true")
    parser.add_argument("--install", action="store_true", help=f"Install only to the {TEXT_AIRCRAFT_NAME} FS4 folder.")
    parser.add_argument("--full", action="store_true", help=f"Prepare, convert, assemble and install {TEXT_AIRCRAFT_NAME}.")
    parser.add_argument("--force-install", action="store_true", help=f"Replace the existing {TEXT_AIRCRAFT_NAME} install.")
    parser.add_argument("--allow-stale-tmb", action="store_true", help="Allow assembling without a fresh text converter run.")
    parser.add_argument("--user-root", type=Path, default=DEFAULT_FS4_USER)
    parser.add_argument("--converter-timeout", type=float, default=180.0)
    return parser


def main() -> int:
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
        print(f"Recommended {TEXT_DISPLAY_NAME} iteration:")
        print("  python tools\\build_gtvr_wraith_text.py --full --force-install")
        return 0

    try:
        if args.prepare_source:
            prepare_source(args)
        if args.convert:
            result = run_converter(args.converter_timeout)
            if result != 0:
                return result
        if args.assemble_package:
            assert_fresh_converted_tmb(args.allow_stale_tmb)
            assemble_package(args)
        if args.install:
            installed = install_package(args.user_root, args.force_install)
            print(f"Installed {TEXT_DISPLAY_NAME} package: {installed}")
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
