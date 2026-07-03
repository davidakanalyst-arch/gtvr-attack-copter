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
    write_png,
    write_root_converter_config,
    write_tgi,
)


ROOT = Path(__file__).resolve().parents[1]
AIRCRAFT_NAME = "gtvr_wraith_heli"
DISPLAY_NAME = "GTVR Wraith Heli"
DONOR_NAME = "optica"
DEFAULT_DONOR = Path.home() / "Documents" / "Aerofly FS 4" / "aircraft" / DONOR_NAME
SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_optica_source" / "aircraft"
SOURCE_DIR = SOURCE_ROOT / AIRCRAFT_NAME
BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_optica_build_user"
PACKAGE_DIR = ROOT / "local-aircraft-packages" / AIRCRAFT_NAME

# The source shell was designed around skid contact. The Optica donor's wheels sit
# slightly higher, so this keeps the visual skids near ground level on fresh spawn.
VISUAL_Z_OFFSET = 0.35
MAIN_ROTOR_PIVOT = (0.2, 0.0, 2.55 + VISUAL_Z_OFFSET)


def extract_geometry_names(tmd_path: Path) -> list[str]:
    text = tmd_path.read_text(encoding="utf-8", errors="replace")
    names: set[str] = set()
    for match in re.finditer(r"<\[string8\]\[Geometry(?:List)?\]\[([^\]]*)\]>", text, flags=re.DOTALL):
        for token in re.split(r"\s+", match.group(1).strip()):
            if token:
                names.add(token)
    return sorted(names)


def dummy_geometry() -> dict[str, Patch]:
    patch = Patch("dark_metal")
    points = [
        (0.0, 0.0, 0.0),
        (0.002, 0.0, 0.0),
        (0.0, 0.002, 0.0),
        (0.0, 0.0, 0.002),
    ]
    faces = [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)]
    for point in points:
        patch.vertices.extend([point[0], point[1], point[2], 0.0, 0.0, 1.0, 0.0, 0.0])
    for face in faces:
        patch.indices.extend(face)
        patch.face_attributes.append(0)
    return {"dark_metal": patch}


def merge_patch_maps(*patch_maps: dict[str, Patch]) -> dict[str, Patch]:
    merged: dict[str, Patch] = {}
    for patch_map in patch_maps:
        for material_name, source in patch_map.items():
            target = merged.setdefault(material_name, Patch(material_name))
            vertex_offset = len(target.vertices) // 8
            target.vertices.extend(source.vertices)
            target.indices.extend(index + vertex_offset for index in source.indices)
            target.face_attributes.extend(source.face_attributes)
    return merged


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


def vector(values: tuple[float, float, float]) -> str:
    return f"{values[0]:.3f} {values[1]:.3f} {values[2]:.3f}"


def patch_tmc(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"<\[stringt8c\]\[ICAO\]\[[^\]]*\]>", "<[stringt8c][ICAO][GTWH]>", text, count=1)
    text = re.sub(
        r"<\[string8\]\[DisplayName\]\[[^\]]*\]>",
        f"<[string8][DisplayName][{DISPLAY_NAME}]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[string8\]\[DisplayNameFull\]\[[^\]]*\]>",
        f"<[string8][DisplayNameFull][{DISPLAY_NAME} Optica V2 Prototype]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[uint32\]\s*\[Year\]\s*\[[^\]]*\]>",
        "<[uint32] [Year]                 [2026]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[string8\]\[Tags\]\[[^\]]*\]>",
        "<[string8][Tags][ airplane piston experimental military gear flaps helicopter prototype ]>",
        text,
        count=1,
    )
    start = text.find("<[list_localized_text][Descriptions][]")
    end = text.find("        <[float64][MaximumTaxiMass]", start)
    if start != -1 and end != -1:
        description = f"""<[list_localized_text][Descriptions][]
            <[localized_text][element][0]
                <[string8u][Language][en]>
                <[string8][Text][{DISPLAY_NAME} is a private GTVR experimental military rotorcraft shell running on the Edgley Optica slow-flight graph. V2 keeps the donor runway, control, sound and gear logic stable while replacing the exterior with a custom armed helicopter visual shell and top-rotor animation.]>
            >
        >
"""
        text = text[:start] + description + text[end:]
    path.write_text(text, encoding="utf-8")


def patch_tmd(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("Edgley EA-7 Optica", DISPLAY_NAME)
    text = text.replace("Edgley Optica", DISPLAY_NAME)

    text = patch_block(
        text,
        "<[camera][CameraFollow][]",
        {
            "<[tmvector3d][R0][-8.53 0 3.1325]>": "<[tmvector3d][R0][-10.0 0 3.4]>",
            "<[tmvector3d][Direction][ 0.965 0.0 -0.2622 ]>": "<[tmvector3d][Direction][ 0.96 0.0 -0.28 ]>",
        },
    )
    text = patch_block(
        text,
        "<[camera_head][CameraPilot][]",
        {
            "<[tmvector3d][R0][1.5 0.48 0.3]>": "<[tmvector3d][R0][3.75 0.36 1.25]>",
            "<[tmvector3d][Direction][0.99 0.0 -0.2]>": "<[tmvector3d][Direction][0.99 0.0 -0.16]>",
        },
    )

    # The Optica physics prop remains forward-facing for stable runway starts,
    # but the graphics are moved onto the custom roof rotor.
    pivot = vector(MAIN_ROTOR_PIVOT)
    text = patch_block(
        text,
        "<[propellergraphics][PropellerDisk][]",
        {
            "<[tmvector3d][Axis][1.0 0.0 0.0]>": "<[tmvector3d][Axis][0.0 0.0 1.0]>",
            "<[tmvector3d][Pivot][-0.455 0 0.04]>": f"<[tmvector3d][Pivot][{pivot}]>",
            "<[uint32][BladeNumber][5]>": "<[uint32][BladeNumber][4]>",
            "<[float64][Radius][0.606]>": "<[float64][Radius][4.9]>",
        },
    )
    text = patch_block(
        text,
        "<[rotatingbodygraphics][PropellerCone][]",
        {
            "<[tmvector3d][Axis][1.0 0.0 0.0]>": "<[tmvector3d][Axis][0.0 0.0 1.0]>",
            "<[tmvector3d][Pivot][-0.455 0 0.04]>": f"<[tmvector3d][Pivot][{pivot}]>",
        },
    )
    text = patch_block(
        text,
        "<[graphics_propeller_blade][PropellerBlades][]",
        {
            "<[tmvector3d][Axis][ 1.0 0.0 0.0 ]>": "<[tmvector3d][Axis][ 0.0 0.0 1.0 ]>",
            "<[tmvector3d][Pivot][-0.455 0 0.04]>": f"<[tmvector3d][Pivot][{pivot}]>",
            "<[float64][Radius][0.606]>": "<[float64][Radius][4.9]>",
        },
    )

    text = text.replace("<[bool][InstantCrash][true]>", "<[bool][InstantCrash][false]>", 1)
    path.write_text(text, encoding="utf-8")


def write_aircraft_source_tmc(path: Path) -> None:
    text = f"""<[file][][]
    <[modelinformation][][]
        <[int32][Version][230]>
        <[list_vector4_float64][ContactSpheres][ (2.267 0.2 -1.05 0.15) (-0.376 1.7 -0.951 0.212) (-0.376 -1.7 -0.951 0.212) ]>
        <[stringt8c][ICAO][GTWH]>
        <[string8][DisplayName][{DISPLAY_NAME}]>
        <[string8][DisplayNameFull][{DISPLAY_NAME} Optica V2 Prototype]>
        <[float64][MaximumTakeoffMass][1315.0]>
        <[uint32][MaximumPersonsOnBoard][3]>
        <[float64][WingSpan][12.0]>
        <[float64][Length][12.2]>
        <[float64][Height][3.7]>
        <[uint32][Year][2026]>
        <[uint32][EngineCount][1]>
        <[float64][EnginePower][194000.0]>
        <[float64][MinimumAirspeed][29.0]>
        <[float64][ApproachAirspeed][30.4]>
        <[float64][CruiseAirspeed][35.0]>
        <[float64][CruiseAltitude][1826.0]>
        <[float64][CruiseSpeed][66.5]>
        <[float64][MaximumAirspeed][70.0]>
        <[float64][MaximumAltitude][4275.0]>
        <[float64][MaximumSpeed][70.0]>
        <[string8][Tags][ airplane piston experimental military gear flaps helicopter prototype ]>
        <[string8][Pilot][pilot_robert]>
    >
>
"""
    path.write_text(text, encoding="utf-8")


def write_option_tmc(path: Path) -> None:
    text = """<[file][][]
    <[object][][]
        <[string8][Description][Optica V2 Prototype]>
        <[string8][Type][repaint]>
    >
>
"""
    path.write_text(text, encoding="utf-8")


def prepare_source(donor: Path) -> None:
    donor_tmd = donor / f"{DONOR_NAME}.tmd"
    if not SOURCE_OBJ.exists():
        raise FileNotFoundError(f"Missing source OBJ: {SOURCE_OBJ}")
    if not donor_tmd.exists():
        raise FileNotFoundError(f"Missing donor TMD: {donor_tmd}")

    if SOURCE_DIR.exists():
        shutil.rmtree(SOURCE_DIR)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_runtime_resources(SOURCE_ROOT)

    vertices, faces = parse_obj(SOURCE_OBJ)
    vertices = [(x, y, z + VISUAL_Z_OFFSET) for x, y, z in vertices]
    base = build_patches(vertices, faces, "aircraft")
    dummy = dummy_geometry()
    visible_shell = merge_patch_maps(
        base["Fuselage"],
        base["LeftSkid"],
        base["RightSkid"],
        base["TailRotor"],
    )

    geometries: dict[str, dict[str, Patch]] = {}
    for name in extract_geometry_names(donor_tmd):
        if name == "Cabin":
            geometries[name] = clone_patch_map(visible_shell)
        elif name == "Prop":
            geometries[name] = clone_patch_map(base["MainRotor"])
        else:
            geometries[name] = clone_patch_map(dummy)

    write_aircraft_source_tmc(SOURCE_DIR / f"{AIRCRAFT_NAME}.tmc")
    # The converter only needs a model graph that references the geometry names.
    from build_gtvr_source_project import write_minimal_tmd

    write_minimal_tmd(SOURCE_DIR / f"{AIRCRAFT_NAME}.tmd", sorted(geometries))
    write_tgi(SOURCE_DIR / f"{AIRCRAFT_NAME}.tgi", geometries)
    write_model_tmc(SOURCE_DIR / "model.tmc")
    write_root_converter_config(SOURCE_ROOT / "config.tmc", SOURCE_ROOT, BUILD_USER)
    for material_name, settings in MATERIALS.items():
        write_png(SOURCE_DIR / f"{material_name}_color.png", settings["color"])

    print(f"Wrote Optica-stable Wraith source: {SOURCE_DIR}")
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
        f"{DONOR_NAME}.tmc": f"{AIRCRAFT_NAME}.tmc",
        f"{DONOR_NAME}.tmd": f"{AIRCRAFT_NAME}.tmd",
    }.items():
        old_path = PACKAGE_DIR / old_name
        if old_path.exists():
            old_path.rename(PACKAGE_DIR / new_name)

    old_tmb = PACKAGE_DIR / f"{DONOR_NAME}.tmb"
    if old_tmb.exists():
        old_tmb.unlink()

    shutil.copy2(converted_tmb, PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmb")
    for texture in converted.glob("*.ttx"):
        shutil.copy2(texture, PACKAGE_DIR / texture.name)

    patch_tmc(PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmc")
    patch_tmd(PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmd")
    write_option_tmc(PACKAGE_DIR / "option.tmc")
    (PACKAGE_DIR / "_GTVR_WRAITH_OPTICA_V2.txt").write_text(
        "\n".join(
            [
                f"{DISPLAY_NAME}",
                "",
                "V2 stable-first experimental custom military rotorcraft package.",
                "Donor graph: user-installed community Edgley Optica.",
                "Visual model: generated GTVR attack helicopter shell compiled with Optica geometry names.",
                "Physics: Optica slow-flight, runway, gear, sound and control graph retained for controllability.",
                "Rotor: custom roof rotor is animated from the donor propeller graphics.",
                "",
                "This is intentionally not EC135-based.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Assembled package: {PACKAGE_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Optica-stable GTVR Wraith Heli.")
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
