from __future__ import annotations

import math
import argparse
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_OBJ = ROOT / "source-model" / "gtvr_attack_copter_shell.obj"
AIRCRAFT_NAME = "gtvr_attack_copter"
PILOT_OVERLAY_NAME = "gtvr_attack_shell"
DEFAULT_SOURCE_ROOTS = {
    "aircraft": ROOT / "tools" / "vendor" / "gtvr_source_aircraft" / "aircraft",
    "pilot-overlay": ROOT / "tools" / "vendor" / "gtvr_overlay_source" / "aircraft",
}
LIVE_AIRCRAFT_DIR = Path.home() / "Documents" / "Aerofly FS 4" / "aircraft" / AIRCRAFT_NAME
DEFAULT_AEROFLY_USER_DIR = Path.home() / "Documents" / "Aerofly FS 4"
SDK_AIRCRAFT_ROOT = (
    ROOT
    / "tools"
    / "vendor"
    / "aerofly_fs_4_aircraft_sdk_20231108"
    / "aerofly_fs_4_aircraft_sdk"
    / "aircraft"
)
CONVERTER_BIN64 = ROOT / "tools" / "vendor" / "aerofly_fs_4_aircraft_converter" / "bin64"


MATERIALS = {
    "matte_graphite": {
        "shader": "standard exterior",
        "color": (16, 18, 18),
    },
    "canopy_glass": {
        "shader": "glass exterior",
        "color": (22, 54, 68),
    },
    "dark_metal": {
        "shader": "standard exterior",
        "color": (7, 8, 8),
    },
    "olive_panel": {
        "shader": "standard exterior",
        "color": (48, 61, 42),
    },
    "warning_red": {
        "shader": "standard exterior",
        "color": (150, 8, 5),
    },
}


LEFT_SKID_OBJECTS = {
    "left_skid",
    "front_left_skid_strut",
    "rear_left_skid_strut",
}
RIGHT_SKID_OBJECTS = {
    "right_skid",
    "front_right_skid_strut",
    "rear_right_skid_strut",
}
MAIN_ROTOR_OBJECTS = {
    "main_rotor_disc_reference",
    "main_rotor_cross_reference",
}
TAIL_ROTOR_OBJECTS = {
    "tail_rotor_reference",
    "tail_rotor_cross_reference",
}
OVERLAY_HEAD_OBJECTS = {
    "chin_sensor",
}
OVERLAY_LOWER_OBJECTS = {
    "left_stub_wing",
    "left_rocket_pod",
    "left_flare_box",
}
OVERLAY_UPPER_OBJECTS = {
    "right_stub_wing",
    "right_rocket_pod",
    "right_flare_box",
}


@dataclass
class ObjFace:
    object_name: str
    material_name: str
    indices: tuple[int, ...]


@dataclass
class Patch:
    material_name: str
    vertices: list[float] = field(default_factory=list)
    indices: list[int] = field(default_factory=list)
    face_attributes: list[int] = field(default_factory=list)


def parse_obj(path: Path) -> tuple[list[tuple[float, float, float]], list[ObjFace]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[ObjFace] = []
    object_name = "Fuselage"
    material_name = "matte_graphite"

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == "v":
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "o":
            object_name = parts[1]
        elif parts[0] == "usemtl":
            material_name = parts[1]
        elif parts[0] == "f":
            indices: list[int] = []
            for token in parts[1:]:
                vertex_token = token.split("/")[0]
                index = int(vertex_token)
                if index < 0:
                    index = len(vertices) + index + 1
                indices.append(index - 1)
            if len(indices) >= 3:
                faces.append(ObjFace(object_name, material_name, tuple(indices)))

    return vertices, faces


def geometry_name_for(object_name: str, profile: str) -> str:
    lowered = object_name.lower()
    if profile == "pilot-overlay":
        if lowered in OVERLAY_HEAD_OBJECTS:
            return "PilotHead"
        if lowered in OVERLAY_LOWER_OBJECTS:
            return "HeadsetLower"
        if lowered in OVERLAY_UPPER_OBJECTS:
            return "HeadsetUpper"
        return "PilotBody"

    if lowered in LEFT_SKID_OBJECTS:
        return "LeftSkid"
    if lowered in RIGHT_SKID_OBJECTS:
        return "RightSkid"
    if lowered in MAIN_ROTOR_OBJECTS:
        return "MainRotor"
    if lowered in TAIL_ROTOR_OBJECTS:
        return "TailRotor"
    return "Fuselage"


def subtract(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length <= 1e-9:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def uv_for(vertex: tuple[float, float, float]) -> tuple[float, float]:
    x, y, z = vertex
    return ((x + 6.2) / 12.4, (z + 2.0 + abs(y) * 0.08) / 5.0)


def build_patches(
    vertices: list[tuple[float, float, float]], faces: list[ObjFace], profile: str
) -> dict[str, dict[str, Patch]]:
    geometries: dict[str, dict[str, Patch]] = defaultdict(dict)

    for face in faces:
        geometry_name = geometry_name_for(face.object_name, profile)
        material_name = face.material_name if face.material_name in MATERIALS else "matte_graphite"
        patch = geometries[geometry_name].setdefault(material_name, Patch(material_name))

        # Fan triangulate quads and cylinder caps from the concept OBJ.
        for offset in range(1, len(face.indices) - 1):
            triangle_indices = (face.indices[0], face.indices[offset], face.indices[offset + 1])
            tri_vertices = [vertices[index] for index in triangle_indices]
            normal = normalize(cross(subtract(tri_vertices[1], tri_vertices[0]), subtract(tri_vertices[2], tri_vertices[0])))
            base_index = len(patch.vertices) // 8
            for vertex in tri_vertices:
                u, v = uv_for(vertex)
                patch.vertices.extend(
                    [
                        vertex[0],
                        vertex[1],
                        vertex[2],
                        normal[0],
                        normal[1],
                        normal[2],
                        u,
                        v,
                    ]
                )
            patch.indices.extend([base_index, base_index + 1, base_index + 2])
            patch.face_attributes.append(0)

    if profile == "aircraft":
        # Option folders in the live package reference both high and low skid names.
        if "LeftSkid" in geometries:
            geometries["LeftLowSkid"] = clone_patch_map(geometries["LeftSkid"])
        if "RightSkid" in geometries:
            geometries["RightLowSkid"] = clone_patch_map(geometries["RightSkid"])

    return dict(geometries)


def clone_patch_map(patches: dict[str, Patch]) -> dict[str, Patch]:
    cloned: dict[str, Patch] = {}
    for material_name, patch in patches.items():
        cloned[material_name] = Patch(
            material_name=patch.material_name,
            vertices=list(patch.vertices),
            indices=list(patch.indices),
            face_attributes=list(patch.face_attributes),
        )
    return cloned


def fmt(values: list[float] | list[int]) -> str:
    rendered: list[str] = []
    for value in values:
        if isinstance(value, int):
            rendered.append(str(value))
        else:
            rendered.append(f"{value:.8g}")
    return " ".join(rendered)


def write_tgi(path: Path, geometries: dict[str, dict[str, Patch]]) -> None:
    material_names = list(MATERIALS)
    material_index = {name: index for index, name in enumerate(material_names)}
    lines: list[str] = [
        "<[file][][]",
        "    <[tmxglscene_impexp][][]",
        "        <[pointer_list_tmxglmaterial_impexp][material_list][]",
    ]

    for index, material_name in enumerate(material_names):
        settings = MATERIALS[material_name]
        lines.extend(
            [
                f"            <[tmxglmaterial_impexp][element][{index}]",
                f"                <[string8][name][{material_name}]>",
                f"                <[string8][shader_hint][{settings['shader']}]>",
                "                <[list_tm_tmtexture_index_pair_impexp][texture_list][]",
                "                    <[tm_tmtexture_index_pair_impexp][element][0]",
                "                        <[string8][channel][diffuse]>",
                f"                        <[string8][name][{material_name}_color]>",
                "                        <[bool][repeat_s][true]>",
                "                        <[bool][repeat_t][true]>",
                "                        <[float32][uvscaling][1]>",
                "                    >",
                "                >",
                "                <[list_tm_shader_fixed_uniform_impexp][uniform_list][]",
                "                >",
                "            >",
            ]
        )

    lines.extend(
        [
            "        >",
            "        <[list_tmxglgeometry_impexp][geometry_list][]",
        ]
    )

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
            num_vertices = len(patch.vertices) // 8
            num_faces = len(patch.indices) // 3
            lines.extend(
                [
                    f"                    <[tmxglpatch_impexp][element][{patch_index}]",
                    f"                        <[uint32][num_vertices][{num_vertices}]>",
                    f"                        <[uint32][num_faces][{num_faces}]>",
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
        lines.extend(
            [
                "                >",
                "            >",
            ]
        )

    lines.extend(["        >", "    >", ">"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_model_tmc(path: Path) -> None:
    texture_names = "\n".join(f"                                    {name}_color" for name in MATERIALS)
    text = f"""<[file][][]
    <[convert_model_settings][][]
        <[float64][BumpMapScaling][1]>
        <[list_convert_target_settings][Targets][]
            <[convert_target_settings][element][0]
                <[string8][Target][Desktop]>
                <[list_string8][Repaints][]>
                <[list_convert_texture_settings][FileOptions][]
                    <[convert_texture_settings][element][0]
                        <[int32][MaxTextureSize][512]>
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


def write_aircraft_tmc(path: Path, aircraft_name: str, display_name: str) -> None:
    icao = "GTAC" if aircraft_name == AIRCRAFT_NAME else "GTSH"
    text = f"""<[file][][]
    <[modelinformation][][]
        <[int32][Version][230]>
        <[list_vector4_float64][ContactSpheres][ ( 1.896956 1.128562 -1.877823 0.05) ( 1.896956 -1.128562 -1.877823 0.05) (-0.876772 1.128558 -1.87855 0.05) (-0.876772 -1.128558 -1.87855 0.05) ]>
        <[stringt8c][ICAO][{icao}]>
        <[string8][DisplayName][{display_name}]>
        <[string8][DisplayNameFull][{display_name}]>
        <[float64][MaximumTaxiMass][2900.0]>
        <[float64][MaximumTakeoffMass][2835.0]>
        <[float64][MaximumLandingMass][2835.0]>
        <[float64][MaximumZeroFuelMass][2910.0]>
        <[float64][OperatingEmptyMass][1380.0]>
        <[float64][MaximumFuelMass][568.0]>
        <[uint32][MaximumPersonsOnBoard][7]>
        <[float64][WingSpan][10.2]>
        <[float64][Length][12.19]>
        <[float64][Height][3.62]>
        <[uint32][Year][2026]>
        <[uint32][EngineCount][2]>
        <[float64][EnginePower][609000.0]>
        <[float64][MinimumAirspeed][0.0]>
        <[float64][ApproachAirspeed][30.8]>
        <[float64][CruiseAirspeed][66.6]>
        <[float64][CruiseAltitude][2743.2]>
        <[float64][CruiseSpeed][69.45]>
        <[float64][MaximumAirspeed][79.74]>
        <[float64][MaximumAltitude][6096.0]>
        <[float64][MaximumSpeed][79.74]>
        <[float64][MaximumRange][565000.0]>
        <[string8][Tags][ helicopter turboshaft vertical_takeoff military prototype ]>
    >
>
"""
    path.write_text(text, encoding="utf-8")


def write_minimal_tmd(path: Path, geometry_names: list[str]) -> None:
    geometry_list = " ".join(geometry_names)
    text = f"""<[file][][]
    <[modelmanager][][]
        <[pointer_list_tmuniverse][DynamicObjects][]
            <[rigidbody][Fuselage][]
                <[float64][Mass][2835.0]>
                <[tmvector3d][InertiaLength][4.2 1.4 1.2]>
                <[tmvector3d][R0][0.0 0.0 0.0]>
                <[tmmatrix3d][B0][1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0]>
            >
        >
        <[pointer_list_tmgraphics][GraphicObjects][]
            <[rigidbodygraphics][Fuselage][]
                <[uint32][PositionID][Fuselage.R]>
                <[uint32][OrientationID][Fuselage.Q]>
                <[string8][GeometryList][ {geometry_list} ]>
            >
        >
    >
>
"""
    path.write_text(text, encoding="utf-8")


def quote_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/") + "/"


def write_root_converter_config(path: Path, intermediate_dir: Path, user_dir: Path) -> None:
    text = f"""<[file][][]
    <[convert_aircraft_settings][][]
        <[bool][ExportGeometryTextFile][false]>
        <[bool][WriteBakedTextures][false]>
        <[bool][SaveReportText][true]>
        <[bool][CombineSpecular][true]>
        <[string8][IntermediateFolder][{quote_path(intermediate_dir)}]>
        <[string8][UserFolder][{quote_path(user_dir)}]>
        <[string8][DesktopFolder][{quote_path(user_dir)}]>
        <[string8][MobileFolder][]>
        <[string8][IOSFolder][]>
        <[string8][AndroidFolder][]>
        <[string8][TempFolder][]>
    >
>
"""
    path.write_text(text, encoding="utf-8")


def write_png(path: Path, color: tuple[int, int, int]) -> None:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - local environment guard
        raise SystemExit("Pillow is required to write Aerofly source textures.") from exc

    image = Image.new("RGB", (8, 8), color)
    image.save(path)


def ensure_runtime_resources(out_root: Path) -> None:
    for resource_name in ("world", "texture", "shader_vulkan"):
        target = out_root / resource_name
        if target.exists():
            continue
        for source_root in (SDK_AIRCRAFT_ROOT, CONVERTER_BIN64):
            source = source_root / resource_name
            if source.exists():
                shutil.copytree(source, target)
                break


def copy_live_metadata(out_aircraft_dir: Path) -> None:
    if not LIVE_AIRCRAFT_DIR.exists():
        return
    for pattern in ("*.tmc",):
        for source in LIVE_AIRCRAFT_DIR.glob(pattern):
            shutil.copy2(source, out_aircraft_dir / source.name)
    for option_dir in ("highskids", "lowskids", "prototype_tactical"):
        source_dir = LIVE_AIRCRAFT_DIR / option_dir
        if source_dir.exists():
            target_dir = out_aircraft_dir / option_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            for source in source_dir.glob("*.tmc"):
                shutil.copy2(source, target_dir / source.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Aerofly source files for the GTVR attack copter.")
    parser.add_argument(
        "--profile",
        choices=("aircraft", "pilot-overlay"),
        default="aircraft",
        help="Build the full aircraft shell source or the external pilot-slot overlay source.",
    )
    parser.add_argument(
        "--user-dir",
        type=Path,
        default=DEFAULT_AEROFLY_USER_DIR,
        help="Aerofly user folder used by the converter config.",
    )
    args = parser.parse_args()

    if not SOURCE_OBJ.exists():
        print(f"Missing source OBJ: {SOURCE_OBJ}")
        return 2

    aircraft_name = AIRCRAFT_NAME if args.profile == "aircraft" else PILOT_OVERLAY_NAME
    display_name = "GTVR Attack Copter" if args.profile == "aircraft" else "GTVR Attack Shell"
    out_aircraft_root = DEFAULT_SOURCE_ROOTS[args.profile]
    out_aircraft_dir = out_aircraft_root / aircraft_name

    if out_aircraft_dir.exists():
        shutil.rmtree(out_aircraft_dir)
    out_aircraft_dir.mkdir(parents=True, exist_ok=True)
    ensure_runtime_resources(out_aircraft_root)

    vertices, faces = parse_obj(SOURCE_OBJ)
    geometries = build_patches(vertices, faces, args.profile)

    if args.profile == "aircraft":
        copy_live_metadata(out_aircraft_dir)
    write_aircraft_tmc(out_aircraft_dir / f"{aircraft_name}.tmc", aircraft_name, display_name)
    write_minimal_tmd(out_aircraft_dir / f"{aircraft_name}.tmd", sorted(geometries))
    write_tgi(out_aircraft_dir / f"{aircraft_name}.tgi", geometries)
    write_model_tmc(out_aircraft_dir / "model.tmc")
    write_root_converter_config(out_aircraft_root / "config.tmc", out_aircraft_root, args.user_dir)
    for material_name, settings in MATERIALS.items():
        write_png(out_aircraft_dir / f"{material_name}_color.png", settings["color"])

    print(f"Wrote source aircraft project: {out_aircraft_dir}")
    print(f"Geometries: {', '.join(sorted(geometries))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
