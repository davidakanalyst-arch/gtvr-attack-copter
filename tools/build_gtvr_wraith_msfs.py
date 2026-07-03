from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path
from zipfile import ZipFile

from build_gtvr_source_project import (
    MATERIALS,
    Patch as SourcePatch,
    SOURCE_OBJ,
    build_patches as build_source_patches,
    ensure_runtime_resources,
    parse_obj,
    write_png,
    write_root_converter_config,
)
from build_gtvr_wraith_optica import (
    AIRCRAFT_NAME,
    DEFAULT_DONOR,
    DISPLAY_NAME,
    MAIN_ROTOR_PIVOT,
    PACKAGE_DIR,
    VISUAL_Z_OFFSET,
    extract_geometry_names,
    patch_tmc,
    patch_tmd,
    write_aircraft_source_tmc,
    write_option_tmc,
    write_wraith_state_files,
)
from build_msfs_shell_source import (
    BUILD_USER as STANDALONE_BUILD_USER,
    PRESETS,
    Material,
    Patch,
    build_patches,
    collect_materials,
    fmt,
    read_buffers,
    traverse_nodes,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_msfs_source" / "aircraft"
SOURCE_DIR = SOURCE_ROOT / AIRCRAFT_NAME
BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_msfs_build_user"
DEFAULT_MSFS_HELI_DIR = Path.home() / "Downloads" / "MSFS Helis"
DEFAULT_SKIP_ROTORS = (
    r"(main[_ ]?rotor|rotor_main|prop_blur|rotor1|"
    r"bambi|bucket|water_face|cargo|hook|hoist|sling|rope|load)"
)


def clone_import_patch_map(patches: dict[str, Patch], *, yaw_180: bool = False) -> dict[str, Patch]:
    if not yaw_180:
        return {
            name: Patch(
                material_name=patch.material_name,
                vertices=list(patch.vertices),
                indices=list(patch.indices),
                face_attributes=list(patch.face_attributes),
            )
            for name, patch in patches.items()
        }

    cloned: dict[str, Patch] = {}
    for name, patch in patches.items():
        vertices = list(patch.vertices)
        for offset in range(0, len(vertices), 8):
            vertices[offset] = -vertices[offset]
            vertices[offset + 1] = -vertices[offset + 1]
            vertices[offset + 3] = -vertices[offset + 3]
            vertices[offset + 4] = -vertices[offset + 4]
        cloned[name] = Patch(
            material_name=patch.material_name,
            vertices=vertices,
            indices=list(patch.indices),
            face_attributes=list(patch.face_attributes),
        )
    return cloned


def clone_patch_map(patches: dict[str, Patch]) -> dict[str, Patch]:
    return {
        name: Patch(
            material_name=patch.material_name,
            vertices=list(patch.vertices),
            indices=list(patch.indices),
            face_attributes=list(patch.face_attributes),
        )
        for name, patch in patches.items()
    }


def source_patch_to_import_patch(source: SourcePatch) -> Patch:
    return Patch(
        material_name=source.material_name,
        vertices=list(source.vertices),
        indices=list(source.indices),
        face_attributes=list(source.face_attributes),
    )


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


def empty_geometry() -> dict[str, Patch]:
    return {}


def legacy_rotor_patch_maps() -> tuple[dict[str, Patch], dict[str, Patch]]:
    vertices, faces = parse_obj(SOURCE_OBJ)
    vertices = [(x, y, z + VISUAL_Z_OFFSET) for x, y, z in vertices]
    source_maps = build_source_patches(vertices, faces, "aircraft")
    main_rotor = {
        material_name: source_patch_to_import_patch(patch)
        for material_name, patch in source_maps.get("MainRotor", {}).items()
    }
    tail_rotor = {
        material_name: source_patch_to_import_patch(patch)
        for material_name, patch in source_maps.get("TailRotor", {}).items()
    }
    return main_rotor, tail_rotor


def add_flat_materials(materials: dict[int, Material], out_dir: Path) -> None:
    next_index = max(materials.keys(), default=-1) + 1
    for name, settings in MATERIALS.items():
        if any(material.name == name for material in materials.values()):
            continue
        texture_name = f"gtvr_{name}"
        write_png(out_dir / f"{texture_name}.png", settings["color"])
        materials[next_index] = Material(
            name=name,
            texture_name=texture_name,
            source_uri="generated-gtvr-rotor-flat-color",
            color=(*settings["color"], 255),
        )
        next_index += 1


def used_materials(materials: dict[int, Material], geometries: dict[str, dict[str, Patch]]) -> list[Material]:
    used = {material_name for patch_map in geometries.values() for material_name in patch_map}
    return [material for material in materials.values() if material.name in used]


def write_tgi(path: Path, materials: dict[int, Material], geometries: dict[str, dict[str, Patch]]) -> None:
    material_list = used_materials(materials, geometries)
    material_index = {material.name: index for index, material in enumerate(material_list)}
    lines: list[str] = [
        "<[file][][]",
        "    <[tmxglscene_impexp][][]",
        "        <[pointer_list_tmxglmaterial_impexp][material_list][]",
    ]

    for index, material in enumerate(material_list):
        lines.extend(
            [
                f"            <[tmxglmaterial_impexp][element][{index}]",
                f"                <[string8][name][{material.name}]>",
                "                <[string8][shader_hint][standard exterior]>",
                "                <[list_tm_tmtexture_index_pair_impexp][texture_list][]",
                "                    <[tm_tmtexture_index_pair_impexp][element][0]",
                "                        <[string8][channel][diffuse]>",
                f"                        <[string8][name][{material.texture_name}]>",
                "                        <[bool][repeat_s][true]>",
                "                        <[bool][repeat_t][true]>",
                "                        <[float32][uvscaling][1]>",
                "                    >",
                "                >",
                "                <[list_tm_shader_fixed_uniform_impexp][uniform_list][]>",
                "            >",
            ]
        )

    lines.extend(["        >", "        <[list_tmxglgeometry_impexp][geometry_list][]"])
    for geometry_index, geometry_name in enumerate(sorted(geometries)):
        patch_map = geometries[geometry_name]
        lines.extend(
            [
                f"            <[tmxglgeometry_impexp][element][{geometry_index}]",
                f"                <[int32][id][{1000 + geometry_index}]>",
                f"                <[string8][name][{geometry_name}]>",
                "                <[matrix4_float64][matrix][ 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000]>",
                "                <[matrix4_float64][matrix_local][ 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000]>",
                "                <[list_tmxglpatch_impexp][patch_list][]",
            ]
        )
        for patch_index, material_name in enumerate(sorted(patch_map)):
            patch = patch_map[material_name]
            lines.extend(
                [
                    f"                    <[tmxglpatch_impexp][element][{patch_index}]",
                    f"                        <[uint32][num_vertices][{len(patch.vertices) // 8}]>",
                    f"                        <[uint32][num_faces][{len(patch.indices) // 3}]>",
                    f"                        <[int32][material_id][{material_index[material_name]}]>",
                    "                        <[int32][vertex_format_size][8]>",
                    "                        <[array_int32][vertex_attrib_size][3 3 0 0 2 0 0 0]>",
                    "                        <[array_int32][vertex_attrib_offset][0 3 -1 -1 6 -1 -1 -1]>",
                    f"                        <[list_float64][vertex_list][{fmt(patch.vertices)}]>",
                    f"                        <[list_uint32][index_list][{fmt(patch.indices)}]>",
                    f"                        <[list_uint32][face_attrib_list][{fmt(patch.face_attributes)}]>",
                    "                    >",
                ]
            )
        lines.extend(["                >", "            >"])

    lines.extend(["        >", "    >", ">"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_model_tmc(path: Path, materials: dict[int, Material], geometries: dict[str, dict[str, Patch]], max_texture_size: int) -> None:
    texture_names = "\n".join(
        f"                                    {material.texture_name}"
        for material in used_materials(materials, geometries)
    )
    text = f"""<[file][][] 
    <[convert_model_settings][][]
        <[float64][BumpMapScaling][1]>
        <[list_convert_target_settings][Targets][]
            <[convert_target_settings][element][0]
                <[string8][Target][Desktop]>
                <[list_string8][Repaints][]>
                <[list_convert_texture_settings][FileOptions][]
                    <[convert_texture_settings][element][0]
                        <[int32][MaxTextureSize][{max_texture_size}]>
                        <[float64][BumpMapScaling][1.0]>
                        <[list_string8][Files][
{texture_names}
                                              ]>
                    >
                >
            >
        >
    >
>
"""
    path.write_text(text, encoding="utf-8")


def write_minimal_tmd(path: Path, geometry_names: list[str]) -> None:
    text = f"""<[file][][] 
    <[modelmanager][][]
        <[pointer_list_tmuniverse][DynamicObjects][]
            <[rigidbody][Fuselage][]
                <[float64][Mass][5000.0]>
                <[tmvector3d][InertiaLength][4.5 1.5 1.5]>
                <[tmvector3d][R0][0.0 0.0 0.0]>
                <[tmmatrix3d][B0][1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0]>
            >
        >
        <[pointer_list_tmgraphics][GraphicObjects][]
            <[rigidbodygraphics][Fuselage][]
                <[uint32][PositionID][Fuselage.R]>
                <[uint32][OrientationID][Fuselage.Q]>
                <[string8][GeometryList][ {' '.join(sorted(geometry_names))} ]>
            >
        >
    >
>
"""
    path.write_text(text, encoding="utf-8")


def prepare_source(args: argparse.Namespace) -> None:
    preset = PRESETS[args.preset]
    archive = args.archive or (args.msfs_dir / preset["archive"])
    gltf_path = args.gltf or preset["gltf"]
    max_faces = args.max_faces or preset["max_faces"]
    if not archive.exists():
        raise FileNotFoundError(f"MSFS archive not found: {archive}")
    if not args.donor.exists():
        raise FileNotFoundError(f"Optica donor not found: {args.donor}")

    if SOURCE_DIR.exists():
        shutil.rmtree(SOURCE_DIR)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_runtime_resources(SOURCE_ROOT)

    with ZipFile(archive) as zipped:
        gltf = json.loads(zipped.read(gltf_path).decode("utf-8"))
        buffers = read_buffers(zipped, gltf_path, gltf)
        materials = collect_materials(
            zipped=zipped,
            gltf=gltf,
            out_dir=SOURCE_DIR,
            max_texture_size=args.max_texture_size,
        )
        mesh_nodes = traverse_nodes(gltf, args.skip_node_regex)
        imported, source_faces, imported_faces, bounds_min, bounds_max = build_patches(
            gltf=gltf,
            buffers=buffers,
            mesh_nodes=mesh_nodes,
            materials=materials,
            max_faces=max_faces,
            scale=args.scale,
        )

    add_flat_materials(materials, SOURCE_DIR)
    main_rotor, tail_rotor = legacy_rotor_patch_maps()
    cabin = merge_patch_maps(clone_import_patch_map(imported, yaw_180=args.yaw_180), tail_rotor)

    geometry_names = extract_geometry_names(args.donor / "optica.tmd")
    geometries: dict[str, dict[str, Patch]] = {}
    for geometry_name in geometry_names:
        if geometry_name == "Cabin":
            geometries[geometry_name] = cabin
        elif geometry_name in {"Prop", "PropBlurFast"}:
            geometries[geometry_name] = clone_patch_map(main_rotor)
        else:
            geometries[geometry_name] = empty_geometry()

    write_aircraft_source_tmc(SOURCE_DIR / f"{AIRCRAFT_NAME}.tmc")
    write_minimal_tmd(SOURCE_DIR / f"{AIRCRAFT_NAME}.tmd", sorted(geometries))
    write_tgi(SOURCE_DIR / f"{AIRCRAFT_NAME}.tgi", materials, geometries)
    write_model_tmc(SOURCE_DIR / "model.tmc", materials, geometries, args.max_texture_size)
    write_root_converter_config(SOURCE_ROOT / "config.tmc", SOURCE_ROOT, BUILD_USER)
    (SOURCE_DIR / "_MSFS_WRAITH_IMPORT.md").write_text(
        "\n".join(
            [
                "# GTVR Wraith MSFS Import",
                "",
                f"- Preset: `{args.preset}`",
                f"- Archive: `{archive}`",
                f"- glTF: `{gltf_path}`",
                f"- Source faces: `{source_faces}`",
                f"- Imported body faces: `{imported_faces}`",
                f"- Imported bounds min: `{[round(value, 3) for value in bounds_min]}`",
                f"- Imported bounds max: `{[round(value, 3) for value in bounds_max]}`",
                f"- Main rotor pivot retained from Wraith: `{MAIN_ROTOR_PIVOT}`",
                f"- Geometry names emitted for Optica graph: `{len(geometries)}`",
                "",
                "The MSFS assets are read from the user's local archive and generated into ignored build output.",
                "Do not commit or redistribute the generated source folder or compiled package.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote Wraith MSFS source: {SOURCE_DIR}")
    print(f"Source faces: {source_faces}")
    print(f"Imported body faces: {imported_faces}")
    print(f"Geometry names emitted: {len(geometries)}")
    print("")
    print("Convert with:")
    print(
        f"  python tools\\run_aerofly_converter.py {AIRCRAFT_NAME} "
        f"tools\\vendor\\gtvr_wraith_msfs_source\\aircraft --userfolder tools\\vendor\\gtvr_wraith_msfs_launch"
    )


def assemble_package(args: argparse.Namespace) -> None:
    converted = BUILD_USER / "aircraft" / AIRCRAFT_NAME
    converted_tmb = converted / f"{AIRCRAFT_NAME}.tmb"
    if not converted_tmb.exists():
        raise FileNotFoundError(
            f"Missing converted TMB: {converted_tmb}. Run the converter command printed by --prepare-source first."
        )
    if not args.donor.exists():
        raise FileNotFoundError(f"Optica donor not found: {args.donor}")

    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    shutil.copytree(args.donor, PACKAGE_DIR, ignore=shutil.ignore_patterns(".git", ".github"))

    for old_name, new_name in {
        "optica.tmc": f"{AIRCRAFT_NAME}.tmc",
        "optica.tmd": f"{AIRCRAFT_NAME}.tmd",
    }.items():
        old_path = PACKAGE_DIR / old_name
        if old_path.exists():
            old_path.rename(PACKAGE_DIR / new_name)

    old_tmb = PACKAGE_DIR / "optica.tmb"
    if old_tmb.exists():
        old_tmb.unlink()
    for old_state in PACKAGE_DIR.glob("optica_*.tmd"):
        old_state.unlink()

    shutil.copy2(converted_tmb, PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmb")
    for texture in converted.glob("*.ttx"):
        shutil.copy2(texture, PACKAGE_DIR / texture.name)

    patch_tmc(PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmc")
    patch_tmd(PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmd")
    write_wraith_state_files(PACKAGE_DIR)
    write_option_tmc(PACKAGE_DIR / "option.tmc")
    (PACKAGE_DIR / "_GTVR_WRAITH_MSFS.txt").write_text(
        "\n".join(
            [
                f"{DISPLAY_NAME}",
                "",
                "Experimental Wraith build with an MSFS helicopter exterior imported into the Optica donor graph.",
                "The package still uses Optica-derived physics, sounds, runway logic and cockpit camera.",
                "The imported MSFS asset is local-only and should not be committed or redistributed.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Assembled package: {PACKAGE_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GTVR Wraith with a local MSFS helicopter exterior shell.")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="uh60")
    parser.add_argument("--msfs-dir", type=Path, default=DEFAULT_MSFS_HELI_DIR)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--gltf")
    parser.add_argument("--donor", type=Path, default=DEFAULT_DONOR)
    parser.add_argument("--max-faces", type=int)
    parser.add_argument("--max-texture-size", type=int, default=1024)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--skip-node-regex", default=DEFAULT_SKIP_ROTORS)
    parser.add_argument("--no-yaw-180", dest="yaw_180", action="store_false")
    parser.set_defaults(yaw_180=True)
    parser.add_argument("--prepare-source", action="store_true")
    parser.add_argument("--assemble-package", action="store_true")
    args = parser.parse_args()

    if not args.prepare_source and not args.assemble_package:
        args.prepare_source = True
        args.assemble_package = True
    if args.prepare_source:
        prepare_source(args)
    if args.assemble_package:
        assemble_package(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
