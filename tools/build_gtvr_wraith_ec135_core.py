from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from zipfile import ZipFile

from build_gtvr_source_project import ensure_runtime_resources, write_root_converter_config
from build_gtvr_wraith_msfs import (
    DEFAULT_MSFS_HELI_DIR,
    DEFAULT_SKIP_ROTORS,
    add_flat_materials,
    clone_import_patch_map,
    clone_patch_map,
    legacy_rotor_patch_maps,
    write_minimal_tmd,
    write_model_tmc,
    write_tgi,
)
from build_msfs_shell_source import (
    PRESETS,
    Patch,
    build_patches,
    collect_materials,
    msfs_to_aerofly,
    normalize_vector,
    primitive_triangles,
    read_accessor,
    read_buffers,
    transform_normal,
    transform_point,
    traverse_nodes,
)


ROOT = Path(__file__).resolve().parents[1]
AIRCRAFT_NAME = "gtvr_wraith_ec135_core"
DISPLAY_NAME = "GTVR Wraith EC135 Core"
SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_ec135_source" / "aircraft"
SOURCE_DIR = SOURCE_ROOT / AIRCRAFT_NAME
BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_ec135_build_user"
PACKAGE_DIR = ROOT / "local-aircraft-packages" / AIRCRAFT_NAME
STOCK_EC135 = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator\aircraft\ec135")
MISSING_GEOMETRY_LOG = ROOT / "tools" / "vendor" / "ec135_log_missing_geometry_names.txt"
MSFS_IMPORT_GROUND_Z = -1.05
VISUAL_TARGET_GROUND_Z = -1.72
VISUAL_BODY_LIFT = 0.28
VISUAL_GEAR_MIN_Z = -1.58
VISUAL_X_OFFSET = -3.2
VISUAL_Y_OFFSET = 0.0
LOW_NON_TIRE_Z_CUTOFF = -1.32
TAIL_ROTOR_NODE_REGEX = (
    r"^(Tail_Rotor\.001|Tail_Rotor\.002|Tail_Rotor\.003|Tail_Rotor\.005|"
    r"Tail_Rotor\.032|Tail_Rotor_Still1)$"
)
DEFAULT_MAX_FACES = 700_000
DEFAULT_SKIP_MATERIAL_REGEX = (
    r"(ski|platform|occluder|void|gltfvalidator|^cabin$|cpit|glass_cpit|^pit$|"
    r"cyclic|gauge|blackint|metal_efb|metal_claw|gun_click|^tire$|^static_parts$|"
    r"decal|rainfx|sensorglass|glass_ext|glass_nav|glass_red_bcn|eots|flir|sensor_bly)"
)
GEAR_NODE_REGEX = (
    r"^(C_ger_Assy|Rear_gear|Strut_rear|REAR_WHEEL_STILL|NurbsPath|"
    r"Cylinder\.(012|029|030|031|034|036|050|052|054|056|058|071|072|073|074|075|076|077|078|079|080|082|083|084|085)|"
    r"Cube\.(011|024|025|026|027|028|029|030|031|032|033|034|035|036|037|038|039|040|041|042|043)|"
    r"Tire_new(?:_rim|_bolts)?\.(001|002)|"
    r"Strut\.(001|002)|Assy\.(002|003)|Caliper\.(001|002|003|004)|"
    r"Cablecutter_Frnt\.(001|002)|NurbsPath\.(001|002|003|004)|"
    r"Clip\.(001|002|003|004|005|006|007|008|009|010))$"
)

BASE_GEOMETRIES = {
    "Fuselage",
    "FuselageDetails",
    "Tailboom",
    "Stabilizer",
    "RotorMast",
    "RotorBlade0",
    "RotorBlade1",
    "RotorBlade2",
    "RotorBlade3",
    "TailBlade0",
    "TailBlade1",
    "TailBlade2",
    "TailBlade3",
    "TailBlade4",
    "TailBlade5",
    "TailBlade6",
    "TailBlade7",
    "TailBlade8",
    "TailBlade9",
    "TailRotorHub",
    "TailRotorCont",
    "LeftLowSkid",
    "RightLowSkid",
    "SkidsMiddle",
    "StickL",
    "StickR",
    "Glass1",
    "Glass2",
    "Glass3",
    "Glass4",
    "Glass5",
    "Glass6",
    "Glass7",
    "Glass8",
    "Glass9",
    "Glass10",
}


def copy_patch_map(patches: dict[str, Patch]) -> dict[str, Patch]:
    return {
        material_name: Patch(
            material_name=patch.material_name,
            vertices=list(patch.vertices),
            indices=list(patch.indices),
            face_attributes=list(patch.face_attributes),
        )
        for material_name, patch in patches.items()
    }


def translate_patch_map(patches: dict[str, Patch], x_delta: float, y_delta: float, z_delta: float) -> None:
    for patch in patches.values():
        for offset in range(0, len(patch.vertices), 8):
            patch.vertices[offset] += x_delta
            patch.vertices[offset + 1] += y_delta
            patch.vertices[offset + 2] += z_delta


def filter_patch_materials(patches: dict[str, Patch], material_regex: str | None) -> dict[str, Patch]:
    if not material_regex:
        return patches
    pattern = re.compile(material_regex, re.IGNORECASE)
    return {name: patch for name, patch in patches.items() if not pattern.search(name)}


def remove_low_non_tire_faces(patches: dict[str, Patch], z_cutoff: float) -> dict[str, Patch]:
    filtered: dict[str, Patch] = {}
    for name, patch in patches.items():
        if re.search(r"tire", name, re.IGNORECASE):
            filtered[name] = patch
            continue

        kept = Patch(material_name=patch.material_name)
        for attr_index, face_offset in enumerate(range(0, len(patch.indices), 3)):
            face_indices = patch.indices[face_offset : face_offset + 3]
            if len(face_indices) < 3:
                continue
            zs = [patch.vertices[index * 8 + 2] for index in face_indices]
            if max(zs) < z_cutoff:
                continue

            base_index = len(kept.vertices) // 8
            for index in face_indices:
                start = index * 8
                kept.vertices.extend(patch.vertices[start : start + 8])
            kept.indices.extend([base_index, base_index + 1, base_index + 2])
            if patch.face_attributes:
                kept.face_attributes.append(patch.face_attributes[attr_index])

        if kept.indices:
            filtered[name] = kept
    return filtered


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


def patch_bounds(patches: dict[str, Patch]) -> tuple[list[float], list[float]] | None:
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    found = False
    for patch in patches.values():
        for offset in range(0, len(patch.vertices), 8):
            found = True
            for axis in range(3):
                value = patch.vertices[offset + axis]
                mins[axis] = min(mins[axis], value)
                maxs[axis] = max(maxs[axis], value)
    return (mins, maxs) if found else None


def lift_patch_map_min_z(patches: dict[str, Patch], min_z: float) -> None:
    bounds = patch_bounds(patches)
    if not bounds:
        return
    z_delta = min_z - bounds[0][2]
    if z_delta > 0.0:
        translate_patch_map(patches, 0.0, 0.0, z_delta)


def reference_frame(gltf: dict, buffers: list[bytes], mesh_nodes: list[tuple[int, list[float]]]) -> tuple[float, float, float]:
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    for node_index, matrix in mesh_nodes:
        mesh = gltf["meshes"][gltf["nodes"][node_index]["mesh"]]
        for primitive in mesh.get("primitives", []):
            attributes = primitive.get("attributes", {})
            if "POSITION" not in attributes:
                continue
            for position in read_accessor(gltf, buffers, attributes["POSITION"]):
                converted = msfs_to_aerofly(transform_point(matrix, position[:3]), 1.0)
                for axis in range(3):
                    mins[axis] = min(mins[axis], converted[axis])
                    maxs[axis] = max(maxs[axis], converted[axis])
    center_x = (mins[0] + maxs[0]) * 0.5
    center_y = (mins[1] + maxs[1]) * 0.5
    z_offset = MSFS_IMPORT_GROUND_Z - mins[2]
    return center_x, center_y, z_offset


def build_selected_nodes(
    *,
    gltf: dict,
    buffers: list[bytes],
    mesh_nodes: list[tuple[int, list[float]]],
    materials: dict[int, object],
    center_x: float,
    center_y: float,
    z_offset: float,
    node_regex: str,
) -> dict[str, Patch]:
    selected = re.compile(node_regex, re.IGNORECASE)
    patches = {material.name: Patch(material.name) for material in materials.values()}
    for node_index, matrix in mesh_nodes:
        node = gltf["nodes"][node_index]
        if not selected.search(node.get("name", "")):
            continue
        mesh = gltf["meshes"][node["mesh"]]
        for primitive in mesh.get("primitives", []):
            attributes = primitive.get("attributes", {})
            if "POSITION" not in attributes:
                continue
            material = materials.get(primitive.get("material", 0), next(iter(materials.values())))
            patch = patches[material.name]
            positions = read_accessor(gltf, buffers, attributes["POSITION"])
            normals = read_accessor(gltf, buffers, attributes["NORMAL"]) if "NORMAL" in attributes else None
            uvs = read_accessor(gltf, buffers, attributes["TEXCOORD_0"]) if "TEXCOORD_0" in attributes else None

            for triangle in primitive_triangles(gltf, buffers, primitive):
                base_index = len(patch.vertices) // 8
                for source_index in triangle:
                    position = msfs_to_aerofly(transform_point(matrix, positions[source_index][:3]), 1.0)
                    position = (position[0] - center_x, position[1] - center_y, position[2] + z_offset)
                    if normals:
                        normal = msfs_to_aerofly(transform_normal(matrix, normals[source_index][:3]), 1.0)
                        normal = normalize_vector(normal)
                    else:
                        normal = (0.0, 0.0, 1.0)
                    uv = uvs[source_index][:2] if uvs else (0.0, 0.0)
                    patch.vertices.extend(
                        [
                            position[0],
                            position[1],
                            position[2],
                            normal[0],
                            normal[1],
                            normal[2],
                            uv[0],
                            uv[1],
                        ]
                    )
                patch.indices.extend([base_index, base_index + 1, base_index + 2])
                patch.face_attributes.append(0)
    return {name: patch for name, patch in patches.items() if patch.indices}


def read_geometry_names() -> list[str]:
    names = set(BASE_GEOMETRIES)
    if MISSING_GEOMETRY_LOG.exists():
        for line in MISSING_GEOMETRY_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
            token = line.strip()
            if token and re.fullmatch(r"[A-Za-z0-9_]+", token):
                names.add(token)
    return sorted(names)


def write_aircraft_source_tmc(path: Path) -> None:
    text = f"""<[file][][]
    <[tmsimulator_scenery_object][element][0]
        <[string8][type][object]>
        <[string8][geometry][{AIRCRAFT_NAME}]>
    >
>
"""
    path.write_text(text, encoding="utf-8")


def build_body(args: argparse.Namespace) -> tuple[dict[int, object], dict[str, Patch], dict[str, Patch], int, int]:
    preset = PRESETS[args.preset]
    archive = args.archive or (args.msfs_dir / preset["archive"])
    gltf_path = args.gltf or preset["gltf"]
    max_faces = args.max_faces or preset["max_faces"]
    if not archive.exists():
        raise FileNotFoundError(f"MSFS archive not found: {archive}")

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
        all_mesh_nodes = traverse_nodes(gltf, None)
        center_x, center_y, z_offset = reference_frame(gltf, buffers, mesh_nodes)
        tail_rotor_imported = build_selected_nodes(
            gltf=gltf,
            buffers=buffers,
            mesh_nodes=all_mesh_nodes,
            materials=materials,
            center_x=center_x,
            center_y=center_y,
            z_offset=z_offset,
            node_regex=TAIL_ROTOR_NODE_REGEX,
        )
        gear_imported = build_selected_nodes(
            gltf=gltf,
            buffers=buffers,
            mesh_nodes=all_mesh_nodes,
            materials=materials,
            center_x=center_x,
            center_y=center_y,
            z_offset=z_offset,
            node_regex=GEAR_NODE_REGEX,
        )
        imported, source_faces, imported_faces, _bounds_min, _bounds_max = build_patches(
            gltf=gltf,
            buffers=buffers,
            mesh_nodes=mesh_nodes,
            materials=materials,
            max_faces=max_faces,
            scale=args.scale,
        )
    body = filter_patch_materials(clone_import_patch_map(imported, yaw_180=args.yaw_180), args.skip_material_regex)
    tail_rotor = clone_import_patch_map(tail_rotor_imported, yaw_180=args.yaw_180)
    visual_gear = clone_import_patch_map(gear_imported, yaw_180=args.yaw_180)
    translate_patch_map(
        body,
        args.visual_x_offset,
        args.visual_y_offset,
        args.visual_ground_z - MSFS_IMPORT_GROUND_Z + args.visual_body_lift,
    )
    translate_patch_map(
        tail_rotor,
        args.visual_x_offset,
        args.visual_y_offset,
        args.visual_ground_z - MSFS_IMPORT_GROUND_Z + args.visual_body_lift,
    )
    translate_patch_map(
        visual_gear,
        args.visual_x_offset,
        args.visual_y_offset,
        args.visual_ground_z - MSFS_IMPORT_GROUND_Z + args.visual_body_lift,
    )
    lift_patch_map_min_z(visual_gear, args.visual_gear_min_z)
    body = remove_low_non_tire_faces(body, args.low_non_tire_z_cutoff)
    body = merge_patch_maps(body, visual_gear)
    return materials, body, tail_rotor, source_faces, imported_faces


def prepare_source(args: argparse.Namespace) -> None:
    if SOURCE_DIR.exists():
        shutil.rmtree(SOURCE_DIR)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_runtime_resources(SOURCE_ROOT)

    materials, body, tail_rotor, source_faces, imported_faces = build_body(args)
    add_flat_materials(materials, SOURCE_DIR)
    main_rotor, fallback_tail_rotor = legacy_rotor_patch_maps()
    translate_patch_map(main_rotor, 0.0, 0.0, args.visual_body_lift)
    translate_patch_map(fallback_tail_rotor, 0.0, 0.0, args.visual_body_lift)
    visual_tail_rotor = tail_rotor or fallback_tail_rotor

    geometries: dict[str, dict[str, Patch]] = {}
    for geometry_name in read_geometry_names():
        if geometry_name == "Fuselage":
            geometries[geometry_name] = copy_patch_map(body)
        elif geometry_name in {"RotorBlade0", "RotorBlade1", "RotorBlade2", "RotorBlade3"}:
            geometries[geometry_name] = clone_patch_map(main_rotor)
        elif geometry_name == "TailBlade0":
            geometries[geometry_name] = copy_patch_map(visual_tail_rotor)
        elif geometry_name.startswith("TailBlade") or geometry_name in {"TailRotorHub", "TailRotorCont"}:
            geometries[geometry_name] = {}
        else:
            geometries[geometry_name] = {}

    write_aircraft_source_tmc(SOURCE_DIR / f"{AIRCRAFT_NAME}.tmc")
    write_minimal_tmd(SOURCE_DIR / f"{AIRCRAFT_NAME}.tmd", sorted(geometries))
    write_tgi(SOURCE_DIR / f"{AIRCRAFT_NAME}.tgi", materials, geometries)
    write_model_tmc(SOURCE_DIR / "model.tmc", materials, geometries, args.max_texture_size)
    write_root_converter_config(SOURCE_ROOT / "config.tmc", SOURCE_ROOT, BUILD_USER)
    (SOURCE_DIR / "_GTVR_WRAITH_EC135_SOURCE.md").write_text(
        "\n".join(
            [
                "# GTVR Wraith EC135 Core Source",
                "",
                "This source compiles a Wraith exterior with EC135 geometry names.",
                f"- Geometry names emitted: `{len(geometries)}`",
                f"- MSFS source faces: `{source_faces}`",
                f"- Imported faces: `{imported_faces}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote EC135-compatible Wraith source: {SOURCE_DIR}")
    print(f"Geometry names emitted: {len(geometries)}")
    print(f"Imported body faces: {imported_faces}")


def patch_tmc(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"<\[stringt8c\]\[ICAO\]\[[^\]]*\]>", "<[stringt8c][ICAO][GTWE]>", text, count=1)
    text = re.sub(r"<\[string8\]\[DisplayName\]\[[^\]]*\]>", f"<[string8][DisplayName][{DISPLAY_NAME}]>", text, count=1)
    text = re.sub(
        r"<\[string8\]\[DisplayNameFull\]\[[^\]]*\]>",
        f"<[string8][DisplayNameFull][{DISPLAY_NAME} Local Test]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[string8\]\[Tags\]\[[^\]]*\]>",
        "<[string8][Tags][ helicopter military twinengine turbine experimental ]>",
        text,
        count=1,
    )
    text = re.sub(
        r"<\[list_vector4_float64\]\[ContactSpheres\]\[[^\]]*\]>",
        "<[list_vector4_float64][ContactSpheres][ ( 1.896 1.128 -1.667 0.05) ( 1.896 -1.128 -1.667 0.05) (-0.876 1.128 -1.668 0.05) (-0.876 -1.128 -1.668 0.05) ]>",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def assemble_package(_: argparse.Namespace) -> None:
    converted = BUILD_USER / "aircraft" / AIRCRAFT_NAME
    converted_tmb = converted / f"{AIRCRAFT_NAME}.tmb"
    if not converted_tmb.exists():
        raise FileNotFoundError(f"Missing converted TMB: {converted_tmb}")
    if not STOCK_EC135.exists():
        raise FileNotFoundError(f"Stock EC135 not found: {STOCK_EC135}")

    preserved_previews: dict[str, bytes] = {}
    if PACKAGE_DIR.exists():
        for preview_name in ("preview.ttx", "preview_small.ttx"):
            preview_path = PACKAGE_DIR / preview_name
            if preview_path.exists():
                preserved_previews[preview_name] = preview_path.read_bytes()
        shutil.rmtree(PACKAGE_DIR)
    shutil.copytree(STOCK_EC135, PACKAGE_DIR, ignore=shutil.ignore_patterns(".git", ".github"))

    rename_pairs = {
        "ec135.tmc": f"{AIRCRAFT_NAME}.tmc",
        "ec135.tmq": f"{AIRCRAFT_NAME}.tmq",
        "ec135.tmb": f"{AIRCRAFT_NAME}.tmb",
        "ec135_clean.tmd": f"{AIRCRAFT_NAME}_clean.tmd",
        "ec135_cold.tmd": f"{AIRCRAFT_NAME}_cold.tmd",
        "ec135_landing.tmd": f"{AIRCRAFT_NAME}_landing.tmd",
        "ec135_start.tmd": f"{AIRCRAFT_NAME}_start.tmd",
        "ec135_takeoff.tmd": f"{AIRCRAFT_NAME}_takeoff.tmd",
    }
    for old_name, new_name in rename_pairs.items():
        old_path = PACKAGE_DIR / old_name
        if old_path.exists():
            old_path.rename(PACKAGE_DIR / new_name)

    shutil.copy2(converted_tmb, PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmb")
    for texture in converted.glob("*.ttx"):
        if texture.name in {"preview.ttx", "preview_small.ttx"} and texture.name in preserved_previews:
            continue
        shutil.copy2(texture, PACKAGE_DIR / texture.name)
    for preview_name, content in preserved_previews.items():
        (PACKAGE_DIR / preview_name).write_bytes(content)
    patch_tmc(PACKAGE_DIR / f"{AIRCRAFT_NAME}.tmc")
    (PACKAGE_DIR / "_GTVR_WRAITH_EC135_CORE.txt").write_text(
        "\n".join(
            [
                f"{DISPLAY_NAME}",
                "",
                "Local-only EC135-core Wraith test.",
                "The package keeps EC135 controls, flight model, sounds, TMQ and states.",
                "Only the compiled visual TMB is replaced with an EC135-geometry-compatible Wraith shell.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Assembled package: {PACKAGE_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GTVR Wraith as an EC135-core local package.")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="uh60")
    parser.add_argument("--msfs-dir", type=Path, default=DEFAULT_MSFS_HELI_DIR)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--gltf")
    parser.add_argument("--max-faces", type=int, default=DEFAULT_MAX_FACES)
    parser.add_argument("--max-texture-size", type=int, default=1024)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--skip-node-regex", default=DEFAULT_SKIP_ROTORS)
    parser.add_argument("--skip-material-regex", default=DEFAULT_SKIP_MATERIAL_REGEX)
    parser.add_argument("--visual-ground-z", type=float, default=VISUAL_TARGET_GROUND_Z)
    parser.add_argument("--visual-body-lift", type=float, default=VISUAL_BODY_LIFT)
    parser.add_argument("--visual-gear-min-z", type=float, default=VISUAL_GEAR_MIN_Z)
    parser.add_argument("--visual-x-offset", type=float, default=VISUAL_X_OFFSET)
    parser.add_argument("--visual-y-offset", type=float, default=VISUAL_Y_OFFSET)
    parser.add_argument("--low-non-tire-z-cutoff", type=float, default=LOW_NON_TIRE_Z_CUTOFF)
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
