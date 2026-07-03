from __future__ import annotations

import argparse
import json
import math
import re
import struct
import shutil
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

from build_gtvr_source_project import (
    ensure_runtime_resources,
    quote_path,
    write_root_converter_config,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MSFS_HELI_DIR = Path.home() / "Downloads" / "MSFS Helis"
SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_msfs_shell_source" / "aircraft"
BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_msfs_shell_build_user"


PRESETS = {
    "uh60": {
        "archive": "deltasimulations-uh60_0D2QR.zip",
        "gltf": "deltasimulations-uh60/Simobjects/Airplanes/UH60/model/UH60M_LOD00.gltf",
        "aircraft_name": "gtvr_msfs_uh60_shell",
        "display_name": "GTVR MSFS UH-60 Shell",
        "max_faces": 140_000,
    },
    "gazelle-simple": {
        "archive": "msfs-gazelle-helicopter-fafa.zip",
        "gltf": "SA342_Gazelle_v0.85_NAYR8/SA342_Gazelle_v0.85/SimObjects/Airplanes/GAZELLE/model.mistral/SimpleAircraft_LOD00.gltf",
        "aircraft_name": "gtvr_msfs_gazelle_shell",
        "display_name": "GTVR MSFS Gazelle Shell",
        "max_faces": 120_000,
    },
    "gazelle-fcp": {
        "archive": "FCP-Gazelle_DgcqI.zip",
        "gltf": "fcp-gazelle-sa-342/SimObjects/Airplanes/fcp_gazelle_sa_342_Aircraft/model/SA_342_lod00.gltf",
        "aircraft_name": "gtvr_msfs_fcp_gazelle_shell",
        "display_name": "GTVR MSFS FCP Gazelle Shell",
        "max_faces": 140_000,
    },
    "h135": {
        "archive": "HPG-Airbus-H135-Dev-Build-444_AVPNH.zip",
        "gltf": "hpg-airbus-h135/Simobjects/Airplanes/H-135 DEV HIGH SKIDS/model/H135_Exterior_LOD00.gltf",
        "aircraft_name": "gtvr_msfs_h135_shell",
        "display_name": "GTVR MSFS H135 Shell",
        "max_faces": 150_000,
    },
    "bell429": {
        "archive": "jXt Simulations Bell 429_v1_August2025_FS20_AdYUO.zip",
        "gltf": "jXt Simulations Bell 429_v1_August2025_FS20/jxtsimulations-aircraft-b429/SimObjects/Airplanes/JxT_B429/model/B429.gltf",
        "aircraft_name": "gtvr_msfs_bell429_shell",
        "display_name": "GTVR MSFS Bell 429 Shell",
        "max_faces": 150_000,
    },
}


COMPONENT_FORMAT = {
    5120: "b",
    5121: "B",
    5122: "h",
    5123: "H",
    5125: "I",
    5126: "f",
}
COMPONENT_SIZE = {
    5120: 1,
    5121: 1,
    5122: 2,
    5123: 2,
    5125: 4,
    5126: 4,
}
TYPE_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


@dataclass
class Material:
    name: str
    texture_name: str
    source_uri: str | None = None
    color: tuple[int, int, int, int] = (128, 128, 128, 255)


@dataclass
class Patch:
    material_name: str
    vertices: list[float] = field(default_factory=list)
    indices: list[int] = field(default_factory=list)
    face_attributes: list[int] = field(default_factory=list)


def sanitize_name(value: str, fallback: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip())
    value = value.strip("_").lower()
    return value or fallback


def fmt(values: list[float] | list[int]) -> str:
    rendered: list[str] = []
    for value in values:
        if isinstance(value, int):
            rendered.append(str(value))
        else:
            rendered.append(f"{value:.8g}")
    return " ".join(rendered)


def matmul(a: list[float], b: list[float]) -> list[float]:
    return [sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4)]


def translation_matrix(values: list[float]) -> list[float]:
    return [1, 0, 0, values[0], 0, 1, 0, values[1], 0, 0, 1, values[2], 0, 0, 0, 1]


def scale_matrix(values: list[float]) -> list[float]:
    return [values[0], 0, 0, 0, 0, values[1], 0, 0, 0, 0, values[2], 0, 0, 0, 0, 1]


def quaternion_matrix(values: list[float]) -> list[float]:
    x, y, z, w = values
    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z
    return [
        1 - 2 * (yy + zz),
        2 * (xy - wz),
        2 * (xz + wy),
        0,
        2 * (xy + wz),
        1 - 2 * (xx + zz),
        2 * (yz - wx),
        0,
        2 * (xz - wy),
        2 * (yz + wx),
        1 - 2 * (xx + yy),
        0,
        0,
        0,
        0,
        1,
    ]


def node_matrix(node: dict) -> list[float]:
    if "matrix" in node:
        m = node["matrix"]
        return [
            m[0],
            m[4],
            m[8],
            m[12],
            m[1],
            m[5],
            m[9],
            m[13],
            m[2],
            m[6],
            m[10],
            m[14],
            m[3],
            m[7],
            m[11],
            m[15],
        ]

    matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    if "translation" in node:
        matrix = matmul(matrix, translation_matrix(node["translation"]))
    if "rotation" in node:
        matrix = matmul(matrix, quaternion_matrix(node["rotation"]))
    if "scale" in node:
        matrix = matmul(matrix, scale_matrix(node["scale"]))
    return matrix


def transform_point(matrix: list[float], point: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3],
        matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7],
        matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11],
    )


def transform_normal(matrix: list[float], normal: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = normal
    nx = matrix[0] * x + matrix[1] * y + matrix[2] * z
    ny = matrix[4] * x + matrix[5] * y + matrix[6] * z
    nz = matrix[8] * x + matrix[9] * y + matrix[10] * z
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length <= 1e-9:
        return (0.0, 1.0, 0.0)
    return (nx / length, ny / length, nz / length)


def msfs_to_aerofly(point: tuple[float, float, float], scale: float) -> tuple[float, float, float]:
    # glTF/MSFS package axes are Y-up. Aerofly aircraft sources use X-forward,
    # Y-right, Z-up. The sign on Z places the usual side-view nose forward.
    x, y, z = point
    return (-z * scale, x * scale, y * scale)


def normalize_vector(values: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = values
    length = math.sqrt(x * x + y * y + z * z)
    if length <= 1e-9:
        return (0.0, 0.0, 1.0)
    return (x / length, y / length, z / length)


def read_accessor(gltf: dict, buffers: list[bytes], accessor_index: int) -> list[tuple]:
    accessor = gltf["accessors"][accessor_index]
    buffer_view = gltf["bufferViews"][accessor["bufferView"]]
    component_type = accessor["componentType"]
    component_count = TYPE_COMPONENTS[accessor["type"]]
    count = accessor["count"]
    offset = buffer_view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = buffer_view.get("byteStride", COMPONENT_SIZE[component_type] * component_count)
    data = buffers[buffer_view["buffer"]]
    unpack_format = "<" + (COMPONENT_FORMAT[component_type] * component_count)
    return [
        struct.unpack_from(unpack_format, data, offset + index * stride)
        for index in range(count)
    ]


def read_buffers(zipped: ZipFile, gltf_path: str, gltf: dict) -> list[bytes]:
    base = str(Path(gltf_path).parent).replace("\\", "/")
    buffers: list[bytes] = []
    for buffer in gltf.get("buffers", []):
        uri = buffer.get("uri")
        if not uri:
            raise ValueError("Embedded/base64 glTF buffers are not supported yet.")
        buffers.append(zipped.read(f"{base}/{uri}"))
    return buffers


def image_lookup(zipped: ZipFile) -> dict[str, str]:
    return {Path(name).name.lower(): name for name in zipped.namelist()}


def material_color(material: dict) -> tuple[int, int, int, int]:
    pbr = material.get("pbrMetallicRoughness", {})
    factor = pbr.get("baseColorFactor", [0.5, 0.5, 0.5, 1.0])
    return tuple(max(0, min(255, int(value * 255))) for value in factor[:4])  # type: ignore[return-value]


def material_texture_uri(gltf: dict, material: dict) -> str | None:
    pbr = material.get("pbrMetallicRoughness", {})
    texture_info = pbr.get("baseColorTexture")
    if not texture_info:
        return None
    texture = gltf.get("textures", [])[texture_info["index"]]
    image_index = texture.get("source")
    if image_index is None:
        image_index = (
            texture.get("extensions", {})
            .get("MSFT_texture_dds", {})
            .get("source")
        )
    if image_index is None:
        return None
    image = gltf.get("images", [])[image_index]
    return image.get("uri")


def write_texture_or_color(
    *,
    zipped: ZipFile,
    lookup: dict[str, str],
    out_dir: Path,
    texture_name: str,
    uri: str | None,
    color: tuple[int, int, int, int],
    max_texture_size: int,
) -> str:
    out_path = out_dir / f"{texture_name}.png"
    if uri:
        source = lookup.get(Path(uri).name.lower())
        if source:
            try:
                image = Image.open(BytesIO(zipped.read(source))).convert("RGBA")
                image.thumbnail((max_texture_size, max_texture_size), Image.Resampling.LANCZOS)
                image.save(out_path)
                return source
            except Exception:
                pass

    Image.new("RGBA", (8, 8), color).save(out_path)
    return "generated-flat-color"


def collect_materials(
    *,
    zipped: ZipFile,
    gltf: dict,
    out_dir: Path,
    max_texture_size: int,
) -> dict[int, Material]:
    lookup = image_lookup(zipped)
    materials: dict[int, Material] = {}
    for index, raw_material in enumerate(gltf.get("materials", [])):
        raw_name = raw_material.get("name", f"material_{index}")
        material_name = sanitize_name(raw_name, f"material_{index}")
        texture_name = sanitize_name(f"msfs_{index}_{raw_name}", f"msfs_material_{index}")
        uri = material_texture_uri(gltf, raw_material)
        color = material_color(raw_material)
        source_uri = write_texture_or_color(
            zipped=zipped,
            lookup=lookup,
            out_dir=out_dir,
            texture_name=texture_name,
            uri=uri,
            color=color,
            max_texture_size=max_texture_size,
        )
        materials[index] = Material(
            name=material_name,
            texture_name=texture_name,
            source_uri=source_uri,
            color=color,
        )
    if not materials:
        texture_name = "msfs_default_material"
        Image.new("RGBA", (8, 8), (128, 128, 128, 255)).save(out_dir / f"{texture_name}.png")
        materials[0] = Material(name="default_material", texture_name=texture_name)
    return materials


def primitive_triangles(gltf: dict, buffers: list[bytes], primitive: dict) -> list[tuple[int, int, int]]:
    if primitive.get("mode", 4) != 4:
        return []
    attributes = primitive.get("attributes", {})
    position_count = len(read_accessor(gltf, buffers, attributes["POSITION"]))
    if "indices" in primitive:
        raw_indices = [int(row[0]) for row in read_accessor(gltf, buffers, primitive["indices"])]
    else:
        raw_indices = list(range(position_count))
    return [
        (raw_indices[index], raw_indices[index + 1], raw_indices[index + 2])
        for index in range(0, len(raw_indices) - 2, 3)
    ]


def traverse_nodes(gltf: dict, skip_node_regex: str | None = None) -> list[tuple[int, list[float]]]:
    nodes = gltf.get("nodes", [])
    skip_pattern = re.compile(skip_node_regex, re.IGNORECASE) if skip_node_regex else None
    child_indices: set[int] = set()
    for node in nodes:
        child_indices.update(node.get("children", []))
    roots = list(gltf.get("scenes", [{}])[gltf.get("scene", 0)].get("nodes", []))
    if not roots:
        roots = [index for index in range(len(nodes)) if index not in child_indices]

    result: list[tuple[int, list[float]]] = []

    def visit(node_index: int, parent_matrix: list[float]) -> None:
        node = nodes[node_index]
        if skip_pattern and skip_pattern.search(node.get("name", "")):
            return
        matrix = matmul(parent_matrix, node_matrix(node))
        if "mesh" in node:
            result.append((node_index, matrix))
        for child in node.get("children", []):
            visit(child, matrix)

    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    for root in roots:
        visit(root, identity)
    return result


def count_faces(gltf: dict, buffers: list[bytes], mesh_nodes: list[tuple[int, list[float]]]) -> int:
    total = 0
    for node_index, _matrix in mesh_nodes:
        mesh = gltf["meshes"][gltf["nodes"][node_index]["mesh"]]
        for primitive in mesh.get("primitives", []):
            total += len(primitive_triangles(gltf, buffers, primitive))
    return total


def build_patches(
    *,
    gltf: dict,
    buffers: list[bytes],
    mesh_nodes: list[tuple[int, list[float]]],
    materials: dict[int, Material],
    max_faces: int,
    scale: float,
) -> tuple[dict[str, Patch], int, int, list[float], list[float]]:
    source_face_count = count_faces(gltf, buffers, mesh_nodes)
    keep_step = max(1, math.ceil(source_face_count / max_faces))
    patches = {material.name: Patch(material.name) for material in materials.values()}
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    imported_faces = 0
    seen_faces = 0

    # First pass: find converted bounds on the full model, not only sampled faces.
    for node_index, matrix in mesh_nodes:
        mesh = gltf["meshes"][gltf["nodes"][node_index]["mesh"]]
        for primitive in mesh.get("primitives", []):
            attributes = primitive.get("attributes", {})
            if "POSITION" not in attributes:
                continue
            positions = read_accessor(gltf, buffers, attributes["POSITION"])
            for position in positions:
                converted = msfs_to_aerofly(transform_point(matrix, position[:3]), scale)
                for axis in range(3):
                    mins[axis] = min(mins[axis], converted[axis])
                    maxs[axis] = max(maxs[axis], converted[axis])

    center_x = (mins[0] + maxs[0]) * 0.5
    center_y = (mins[1] + maxs[1]) * 0.5
    target_ground_z = -1.05
    z_offset = target_ground_z - mins[2]

    for node_index, matrix in mesh_nodes:
        mesh = gltf["meshes"][gltf["nodes"][node_index]["mesh"]]
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
                keep = seen_faces % keep_step == 0
                seen_faces += 1
                if not keep:
                    continue

                base_index = len(patch.vertices) // 8
                for source_index in triangle:
                    position = msfs_to_aerofly(transform_point(matrix, positions[source_index][:3]), scale)
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
                imported_faces += 1

    patches = {name: patch for name, patch in patches.items() if patch.indices}
    final_mins = [value - offset for value, offset in zip(mins, (center_x, center_y, -z_offset))]
    final_maxs = [value - offset for value, offset in zip(maxs, (center_x, center_y, -z_offset))]
    return patches, source_face_count, imported_faces, final_mins, final_maxs


def write_tgi(path: Path, materials: dict[int, Material], patches: dict[str, Patch]) -> None:
    material_list = [material for material in materials.values() if material.name in patches]
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
    lines.extend(
        [
            "            <[tmxglgeometry_impexp][element][0]",
            "                <[int32][id][1000]>",
            "                <[string8][name][Fuselage]>",
            "                <[matrix4_float64][matrix][ 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000]>",
            "                <[matrix4_float64][matrix_local][ 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 1.000000]>",
            "                <[list_tmxglpatch_impexp][patch_list][]",
        ]
    )

    patch_index = 0
    for material_name in sorted(patches):
        patch = patches[material_name]
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
        patch_index += 1

    lines.extend(["                >", "            >", "        >", "    >", ">"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_aircraft_tmc(path: Path, aircraft_name: str, display_name: str) -> None:
    text = f"""<[file][][] 
    <[modelinformation][][]
        <[int32][Version][230]>
        <[list_vector4_float64][ContactSpheres][ ( 2.2 1.2 -1.05 0.1 ) ( 2.2 -1.2 -1.05 0.1 ) ( -2.2 1.2 -1.05 0.1 ) ( -2.2 -1.2 -1.05 0.1 ) ]>
        <[stringt8c][ICAO][GMSH]>
        <[string8][DisplayName][{display_name}]>
        <[string8][DisplayNameFull][{display_name}]>
        <[float64][MaximumTakeoffMass][5000.0]>
        <[uint32][MaximumPersonsOnBoard][4]>
        <[float64][WingSpan][16.0]>
        <[float64][Length][18.0]>
        <[float64][Height][4.0]>
        <[uint32][Year][2026]>
        <[uint32][EngineCount][1]>
        <[float64][EnginePower][1000000.0]>
        <[string8][Tags][ helicopter experimental visual-shell msfs-local ]>
    >
>
"""
    path.write_text(text, encoding="utf-8")


def write_minimal_tmd(path: Path) -> None:
    text = """<[file][][]
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
                <[string8][GeometryList][ Fuselage ]>
            >
        >
    >
>
"""
    path.write_text(text, encoding="utf-8")


def write_model_tmc(path: Path, materials: dict[int, Material], max_texture_size: int) -> None:
    texture_names = "\n".join(
        f"                                    {material.texture_name}"
        for material in materials.values()
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


def write_summary(
    path: Path,
    *,
    preset: str,
    archive: Path,
    gltf_path: str,
    source_faces: int,
    imported_faces: int,
    bounds_min: list[float],
    bounds_max: list[float],
    materials: dict[int, Material],
) -> None:
    material_lines = [
        f"- {material.name}: {material.source_uri or 'flat color'}"
        for material in materials.values()
    ]
    text = "\n".join(
        [
            "# MSFS Shell Import",
            "",
            f"- Preset: `{preset}`",
            f"- Archive: `{archive}`",
            f"- glTF: `{gltf_path}`",
            f"- Source faces: `{source_faces}`",
            f"- Imported faces: `{imported_faces}`",
            f"- Bounds min: `{[round(value, 3) for value in bounds_min]}`",
            f"- Bounds max: `{[round(value, 3) for value in bounds_max]}`",
            "",
            "Textures/materials resolved from the local archive:",
            *material_lines,
            "",
            "This generated folder is local build output. Do not commit or redistribute the MSFS source assets.",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def build_source(args: argparse.Namespace) -> int:
    preset = PRESETS[args.preset]
    archive = args.archive or (args.msfs_dir / preset["archive"])
    gltf_path = args.gltf or preset["gltf"]
    aircraft_name = args.aircraft_name or preset["aircraft_name"]
    display_name = args.display_name or preset["display_name"]
    max_faces = args.max_faces or preset["max_faces"]

    if not archive.exists():
        raise FileNotFoundError(f"MSFS archive not found: {archive}")

    out_dir = SOURCE_ROOT / aircraft_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ensure_runtime_resources(SOURCE_ROOT)

    with ZipFile(archive) as zipped:
        gltf = json.loads(zipped.read(gltf_path).decode("utf-8"))
        buffers = read_buffers(zipped, gltf_path, gltf)
        materials = collect_materials(
            zipped=zipped,
            gltf=gltf,
            out_dir=out_dir,
            max_texture_size=args.max_texture_size,
        )
        mesh_nodes = traverse_nodes(gltf, args.skip_node_regex)
        patches, source_faces, imported_faces, bounds_min, bounds_max = build_patches(
            gltf=gltf,
            buffers=buffers,
            mesh_nodes=mesh_nodes,
            materials=materials,
            max_faces=max_faces,
            scale=args.scale,
        )

    write_aircraft_tmc(out_dir / f"{aircraft_name}.tmc", aircraft_name, display_name)
    write_minimal_tmd(out_dir / f"{aircraft_name}.tmd")
    write_tgi(out_dir / f"{aircraft_name}.tgi", materials, patches)
    write_model_tmc(out_dir / "model.tmc", materials, args.max_texture_size)
    write_root_converter_config(SOURCE_ROOT / "config.tmc", SOURCE_ROOT, BUILD_USER)
    write_summary(
        out_dir / "_MSFS_IMPORT.md",
        preset=args.preset,
        archive=archive,
        gltf_path=gltf_path,
        source_faces=source_faces,
        imported_faces=imported_faces,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        materials=materials,
    )

    print(f"Wrote MSFS shell source: {out_dir}")
    print(f"Source faces: {source_faces}")
    print(f"Imported faces: {imported_faces}")
    print(f"Bounds min: {[round(value, 3) for value in bounds_min]}")
    print(f"Bounds max: {[round(value, 3) for value in bounds_max]}")
    print("")
    print("Convert with:")
    print(
        f"  python tools\\run_aerofly_converter.py {aircraft_name} "
        f"{quote_path(SOURCE_ROOT).rstrip('/')} --userfolder {BUILD_USER}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Aerofly source geometry from a local MSFS helicopter glTF archive.")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="uh60")
    parser.add_argument("--msfs-dir", type=Path, default=DEFAULT_MSFS_HELI_DIR)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--gltf")
    parser.add_argument("--aircraft-name")
    parser.add_argument("--display-name")
    parser.add_argument("--max-faces", type=int)
    parser.add_argument("--max-texture-size", type=int, default=1024)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--skip-node-regex", help="Optional case-insensitive regex for MSFS node names to exclude.")
    args = parser.parse_args()
    return build_source(args)


if __name__ == "__main__":
    raise SystemExit(main())
