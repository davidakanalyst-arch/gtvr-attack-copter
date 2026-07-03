from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from build_gtvr_source_project import (
    MATERIALS,
    Patch,
    SOURCE_OBJ,
    build_patches,
    clone_patch_map,
    ensure_runtime_resources,
    parse_obj,
    write_model_tmc,
    write_minimal_tmd,
    write_png,
    write_root_converter_config,
    write_tgi,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DONOR = Path.home() / "Documents" / "Aerofly FS 4" / "aircraft" / "bleriot"
AIRCRAFT_NAME = "gtvr_wraith_heli"
DISPLAY_NAME = "GTVR Wraith Heli"
SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_frankenheli_source" / "aircraft"
SOURCE_DIR = SOURCE_ROOT / AIRCRAFT_NAME
BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_frankenheli_build_user"
PACKAGE_DIR = ROOT / "local-aircraft-packages" / AIRCRAFT_NAME


FUSELAGE_NAMES = {
    "PanneauxFuselage",
    "CadreFuselage",
    "Frame1",
    "Frame2",
    "Noir",
    "EntoilageFixe",
    "EntoilageArmatures",
}
MAIN_ROTOR_NAMES = {
    "Blades",
    "Propellerdisk",
    "Propcenter",
    "Propscrew",
    "Propscrew01",
    "Propplate",
    "HeliceColor",
}
TAIL_ROTOR_NAMES = {
    "Rudder",
    "Ruddercoverage",
    "Elevator",
    "Elevatorcoverage",
}
LEFT_SKID_NAMES = {
    "LeftGear",
    "LeftGearString",
    "LeftGearsupport",
    "LeftGearmuff",
    "LeftGearLink",
    "LeftGearspring",
    "LeftGearspring2",
    "LeftWheel",
    "Lefttire",
}
RIGHT_SKID_NAMES = {
    "RightGear",
    "RightGearString",
    "RightGearsupport",
    "RightGearmuff",
    "RightGearLink",
    "RightGearspring",
    "RightGearspring2",
    "RightWheel",
    "Righttire",
}


def extract_geometry_names(tmd_path: Path) -> list[str]:
    text = tmd_path.read_text(encoding="utf-8", errors="replace")
    names: set[str] = set()
    for match in re.finditer(r"<\[string8\]\[Geometry(?:List)?\]\[([^\]]*)\]>", text, flags=re.DOTALL):
        for token in re.split(r"\s+", match.group(1).strip()):
            token = token.strip()
            if token:
                names.add(token)
    return sorted(names)


def dummy_geometry() -> dict[str, Patch]:
    patch = Patch("dark_metal")
    points = [
        (0.0, 0.0, -0.18),
        (0.04, 0.0, -0.18),
        (0.0, 0.04, -0.18),
        (0.0, 0.0, -0.14),
    ]
    faces = [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)]
    for point in points:
        patch.vertices.extend([point[0], point[1], point[2], 0.0, 0.0, 1.0, 0.0, 0.0])
    for face in faces:
        patch.indices.extend(face)
        patch.face_attributes.append(0)
    return {"dark_metal": patch}


def patch_block(text: str, header: str, replacements: dict[str, str]) -> str:
    start = text.find(header)
    if start == -1:
        raise ValueError(f"Could not find TMD block: {header}")
    end = text.find("\n            >", start)
    if end == -1:
        raise ValueError(f"Could not find end of TMD block: {header}")
    end += len("\n            >")
    block = text[start:end]
    for old, new in replacements.items():
        if old not in block:
            raise ValueError(f"Could not patch {header}; missing: {old}")
        block = block.replace(old, new, 1)
    return text[:start] + block + text[end:]


def patch_tmc(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    replacements = {
        "<[stringt8c][ICAO][BL11]>": "<[stringt8c][ICAO][GTWH]>",
        "<[float64][MaximumTakeoffMass]   [300.0]>": "<[float64][MaximumTakeoffMass]   [520.0]>",
        "<[uint32] [MaximumPersonsOnBoard][1]>": "<[uint32] [MaximumPersonsOnBoard][2]>",
        "<[float64][WingSpan]             [8.4]>": "<[float64][WingSpan]             [9.8]>",
        "<[uint32] [Year]                 [1909]>": "<[uint32] [Year]                 [2026]>",
        "<[float64][MaximumAltitude]      [1000.0]>": "<[float64][MaximumAltitude]      [2500.0]>",
        "<[float64][CruiseAltitude]       [200.0]>": "<[float64][CruiseAltitude]       [600.0]>",
        "<[float64][EnginePower]          [19000.0]>": "<[float64][EnginePower]          [180000.0]>",
        "<[float64][MaximumAirspeed]      [22.5]>": "<[float64][MaximumAirspeed]      [65.0]>",
        "<[float64][MaximumSpeed]         [22.5]>": "<[float64][MaximumSpeed]         [65.0]>",
        "<[float64][MinimumAirspeed]      [13.0]>": "<[float64][MinimumAirspeed]      [0.0]>",
        "<[float64][ApproachAirspeed]     [15.0]>": "<[float64][ApproachAirspeed]     [20.0]>",
        "<[float64][CruiseAirspeed]       [18.0]>": "<[float64][CruiseAirspeed]       [45.0]>",
        "<[float64][CruiseSpeed]          [18.0]>": "<[float64][CruiseSpeed]          [45.0]>",
        "<[string8][Tags][ airplane historical piston gear tailgear ]>": "<[string8][Tags][ airplane helicopter piston experimental military gear tailgear vertical_takeoff ]>",
        "<[string8][Pilot][pilot_peter]>": "<[string8][Pilot][pilot_jason]>",
    }
    for old, new in replacements.items():
        text = text.replace(old, new, 1)

    text = re.sub(
        r"<\[string8\]\[DisplayName\]\[[^\]]*\]>",
        f"<[string8][DisplayName][{DISPLAY_NAME}]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[string8\]\[DisplayNameFull\]\[[^\]]*\]>",
        f"<[string8][DisplayNameFull][{DISPLAY_NAME} Experimental Rotorcraft]>",
        text,
        count=1,
    )

    start = text.find("<[list_localized_text][Descriptions][]")
    end = text.find("        <[float64][MaximumTakeoffMass]", start)
    if start != -1 and end != -1:
        description = f"""<[list_localized_text][Descriptions][]
            <[localized_text][element][0]
                <[string8u][Language][en]>
                <[string8][Text][{DISPLAY_NAME} is a private GTVR experimental military rotorcraft for Aerofly FS 4. This build uses an open, readable fixed-wing aircraft graph as a donor and redirects its compiled geometry to an original armed helicopter shell with upward rotor thrust experiments.]>
            >
        >
"""
        text = text[:start] + description + text[end:]

    path.write_text(text, encoding="utf-8")


def patch_tmd(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("Blériot XI", DISPLAY_NAME)

    text = patch_block(
        text,
        "<[camera][CameraFollow][]",
        {
            "<[tmvector3d][R0][ -13.6 0.0 1.7 ]>": "<[tmvector3d][R0][ -10.0 0.0 3.0 ]>",
            "<[tmvector3d][Direction][1.0 0.0 0.0]>": "<[tmvector3d][Direction][0.96 0.0 -0.28]>",
        },
    )
    text = patch_block(
        text,
        "<[camera_head][CameraPilot][]",
        {
            "<[tmvector3d][R0][ -0.99 -0.07 0.78 ]>": "<[tmvector3d][R0][ 3.35 -0.42 0.75 ]>",
            "<[tmvector3d][Direction][ 1.0 0.0 0.0 ]>": "<[tmvector3d][Direction][ 0.98 0.0 -0.18 ]>",
        },
    )
    text = patch_block(
        text,
        "<[rigidbody][PropellerBody][]",
        {
            "<[float64][Mass][10.0]>": "<[float64][Mass][24.0]>",
            "<[tmvector3d][InertiaLength][ 0.2 2.01 0.2 ]>": "<[tmvector3d][InertiaLength][ 4.8 4.8 0.2 ]>",
            "<[tmvector3d][R0][1.0 0.0 0.0]>": "<[tmvector3d][R0][0.2 0.0 2.55]>",
        },
    )
    text = patch_block(
        text,
        "<[multibody_joint][PropellerJoint][]",
        {
            "<[tmvector3d][X0][ 1.0 0.0 0.0]>": "<[tmvector3d][X0][ 0.0 0.0 1.0]>",
            "<[tmvector3d][R0][1.0 0.0 0.0]>": "<[tmvector3d][R0][0.2 0.0 2.55]>",
            "<[float64][InitialVelocity][12.0]>": "<[float64][InitialVelocity][45.0]>",
        },
    )
    text = patch_block(
        text,
        "<[propeller][Propeller][]",
        {
            "<[tmvector3d][R0][1.0 0.0 0.0]>": "<[tmvector3d][R0][0.2 0.0 2.55]>",
            "<[tmvector3d][X0][1.0 0.0 0.0]>": "<[tmvector3d][X0][0.0 0.0 1.0]>",
            "<[tmvector3d][Y0][0.0 1.0 0.0]>": "<[tmvector3d][Y0][1.0 0.0 0.0]>",
            "<[tmvector3d][Z0][0.0 0.0 1.0]>": "<[tmvector3d][Z0][0.0 1.0 0.0]>",
            "<[float64][Radius][1.04]>": "<[float64][Radius][4.8]>",
            "<[float64][Pitch][1.52000]>": "<[float64][Pitch][1.05]>",
            "<[float64][CutOut][0.2]>": "<[float64][CutOut][0.08]>",
        },
    )
    text = patch_block(
        text,
        "<[jointtorque][DriveShaft][]",
        {"<[tmvector3d][Z0][1.0 0.0 0.0]>": "<[tmvector3d][Z0][0.0 0.0 1.0]>"},
    )
    text = patch_block(
        text,
        "<[engine][Engine][]",
        {
            "<[float64][Friction][50.0]>": "<[float64][Friction][20.0]>",
            "<[float64][RatedRotationSpeed][140.0]>": "<[float64][RatedRotationSpeed][90.0]>",
            "<[float64][RatedPower][19000]>": "<[float64][RatedPower][180000]>",
        },
    )

    rotor_graphics = {
        "<[tmvector3d][Axis][1.0 0.0 0.0]>": "<[tmvector3d][Axis][0.0 0.0 1.0]>",
        "<[tmvector3d][Pivot][0.9763 -0.0923 0.04045]>": "<[tmvector3d][Pivot][0.2 0.0 2.55]>",
    }
    text = patch_block(text, "<[rotatingbodygraphics][Spinner][]", rotor_graphics)
    text = patch_block(
        text,
        "<[graphics_propeller_blade][PropellerBlade][]",
        {
            "<[tmvector3d][Axis][ 1.0 0.0 0.0 ]>": "<[tmvector3d][Axis][ 0.0 0.0 1.0 ]>",
            "<[tmvector3d][Pivot][0.9763 -0.0923 0.04045]>": "<[tmvector3d][Pivot][0.2 0.0 2.55]>",
            "<[float64][Radius][1.005840]>": "<[float64][Radius][4.8]>",
        },
    )
    text = patch_block(
        text,
        "<[propellergraphics][Propeller][]",
        {
            "<[tmvector3d][Axis][1.0 0.0 0.0]>": "<[tmvector3d][Axis][0.0 0.0 1.0]>",
            "<[tmvector3d][Pivot][0.9763 -0.0923 0.04045]>": "<[tmvector3d][Pivot][0.2 0.0 2.55]>",
            "<[float64][Radius][1.005840]>": "<[float64][Radius][4.8]>",
            "<[uint32][BladeNumber][2]>": "<[uint32][BladeNumber][4]>",
        },
    )

    path.write_text(text, encoding="utf-8")


def write_aircraft_source_tmc(path: Path) -> None:
    text = f"""<[file][][]
    <[modelinformation][][]
        <[int32][Version][230]>
        <[list_vector4_float64][ContactSpheres][ (0.285 0.702 -1.004 0.352) (0.277 -0.874 -1.004 0.352) (-3.886 -0.056 -0.729 0.262) ]>
        <[stringt8c][ICAO][GTWH]>
        <[string8][DisplayName][{DISPLAY_NAME}]>
        <[string8][DisplayNameFull][{DISPLAY_NAME} Experimental Rotorcraft]>
        <[float64][MaximumTakeoffMass][520.0]>
        <[uint32][MaximumPersonsOnBoard][2]>
        <[float64][WingSpan][9.8]>
        <[float64][Length][12.2]>
        <[float64][Height][3.7]>
        <[uint32][Year][2026]>
        <[uint32][EngineCount][1]>
        <[float64][EnginePower][180000.0]>
        <[float64][MinimumAirspeed][0.0]>
        <[float64][ApproachAirspeed][20.0]>
        <[float64][CruiseAirspeed][45.0]>
        <[float64][CruiseAltitude][600.0]>
        <[float64][CruiseSpeed][45.0]>
        <[float64][MaximumAirspeed][65.0]>
        <[float64][MaximumAltitude][2500.0]>
        <[float64][MaximumSpeed][65.0]>
        <[string8][Tags][ airplane helicopter piston experimental military gear tailgear vertical_takeoff ]>
        <[string8][Pilot][pilot_jason]>
    >
>
"""
    path.write_text(text, encoding="utf-8")


def prepare_source(donor: Path) -> None:
    if not SOURCE_OBJ.exists():
        raise FileNotFoundError(f"Missing source OBJ: {SOURCE_OBJ}")
    donor_tmd = donor / "bleriot.tmd"
    if not donor_tmd.exists():
        raise FileNotFoundError(f"Missing donor TMD: {donor_tmd}")

    if SOURCE_DIR.exists():
        shutil.rmtree(SOURCE_DIR)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_runtime_resources(SOURCE_ROOT)

    vertices, faces = parse_obj(SOURCE_OBJ)
    base = build_patches(vertices, faces, "aircraft")
    dummy = dummy_geometry()
    geometries: dict[str, dict[str, Patch]] = {}

    for name in extract_geometry_names(donor_tmd):
        if name in FUSELAGE_NAMES:
            geometries[name] = clone_patch_map(base["Fuselage"])
        elif name in MAIN_ROTOR_NAMES:
            geometries[name] = clone_patch_map(base["MainRotor"])
        elif name in TAIL_ROTOR_NAMES:
            geometries[name] = clone_patch_map(base["TailRotor"])
        elif name in LEFT_SKID_NAMES:
            geometries[name] = clone_patch_map(base["LeftSkid"])
        elif name in RIGHT_SKID_NAMES:
            geometries[name] = clone_patch_map(base["RightSkid"])
        else:
            geometries[name] = clone_patch_map(dummy)

    write_aircraft_source_tmc(SOURCE_DIR / f"{AIRCRAFT_NAME}.tmc")
    write_minimal_tmd(SOURCE_DIR / f"{AIRCRAFT_NAME}.tmd", sorted(geometries))
    write_tgi(SOURCE_DIR / f"{AIRCRAFT_NAME}.tgi", geometries)
    write_model_tmc(SOURCE_DIR / "model.tmc")
    write_root_converter_config(SOURCE_ROOT / "config.tmc", SOURCE_ROOT, BUILD_USER)
    for material_name, settings in MATERIALS.items():
        write_png(SOURCE_DIR / f"{material_name}_color.png", settings["color"])

    print(f"Wrote Frankenstein source: {SOURCE_DIR}")
    print(f"Geometry names emitted: {len(geometries)}")


def assemble_package(donor: Path) -> None:
    converted = BUILD_USER / "aircraft" / AIRCRAFT_NAME
    converted_tmb = converted / f"{AIRCRAFT_NAME}.tmb"
    if not converted_tmb.exists():
        raise FileNotFoundError(
            f"Missing converted TMB: {converted_tmb}. Run run_aerofly_converter.py first."
        )

    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    shutil.copytree(donor, PACKAGE_DIR, ignore=shutil.ignore_patterns(".git", ".github"))

    for old_name, new_name in {
        "bleriot.tmc": f"{AIRCRAFT_NAME}.tmc",
        "bleriot.tmd": f"{AIRCRAFT_NAME}.tmd",
    }.items():
        old_path = PACKAGE_DIR / old_name
        if old_path.exists():
            old_path.rename(PACKAGE_DIR / new_name)

    old_tmb = PACKAGE_DIR / "bleriot.tmb"
    if old_tmb.exists():
        old_tmb.unlink()

    shutil.copy2(converted_tmb, PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmb")
    for texture in converted.glob("*.ttx"):
        shutil.copy2(texture, PACKAGE_DIR / texture.name)

    patch_tmc(PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmc")
    patch_tmd(PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmd")
    (PACKAGE_DIR / "_GTVR_FRANKENHELI.txt").write_text(
        "\n".join(
            [
                f"{DISPLAY_NAME}",
                "",
                "Experimental custom military rotorcraft package.",
                "Donor graph: user-installed community Bleriot XI.",
                "Visual model: generated GTVR attack copter shell compiled with Bleriot geometry names.",
                "Physics: open text aircraft graph with upward rotor-thrust experiment.",
                "",
                "This is intentionally not EC135-based.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Assembled package: {PACKAGE_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the non-EC135 GTVR Frankenstein military heli.")
    parser.add_argument("--donor", type=Path, default=DEFAULT_DONOR)
    parser.add_argument("--prepare-source", action="store_true")
    parser.add_argument("--assemble-package", action="store_true")
    args = parser.parse_args()

    if not args.prepare_source and not args.assemble_package:
        args.prepare_source = True
        args.assemble_package = True

    if args.prepare_source:
        prepare_source(args.donor)
    if args.assemble_package:
        assemble_package(args.donor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
