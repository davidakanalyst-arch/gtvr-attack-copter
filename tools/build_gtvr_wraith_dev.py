from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import build_gtvr_wraith_ec135_core as core
from build_gtvr_source_project import write_png
from build_msfs_shell_source import Material


ROOT = Path(__file__).resolve().parents[1]

STABLE_AIRCRAFT_NAME = "gtvr_wraith_ec135_core"
DEV_AIRCRAFT_NAME = "gtvr_wraith_dev"
DEV_DISPLAY_NAME = "GTVR Wraith Dev"
DEV_ICAO = "GTWD"
DEV_PILOT = "pilot_jason"

DEV_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_dev_source" / "aircraft"
DEV_SOURCE_DIR = DEV_SOURCE_ROOT / DEV_AIRCRAFT_NAME
DEV_BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_dev_build_user"
DEV_LAUNCH_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_dev_launch"
DEV_PACKAGE_DIR = ROOT / "local-aircraft-packages" / DEV_AIRCRAFT_NAME
DEV_SOURCE_STAMP = DEV_SOURCE_DIR / "_GTVR_WRAITH_DEV_SOURCE_STAMP.txt"

DEFAULT_FS4_USER = Path.home() / "Documents" / "Aerofly FS 4"
DEFAULT_INNER_SHELL_SKIP_MATERIAL_REGEX = (
    r"(glass|window|windscreen|windshield|transparent|translucent|clear|alpha|"
    r"opacity|lens)"
)
INNER_SHELL_MATERIAL_NAME = "gtvr_inner_matte_black"
INNER_SHELL_TEXTURE_NAME = "gtvr_inner_matte_black"
INNER_SHELL_COLOR = (2, 2, 2)
DEFAULT_PILOT_ALIGNMENT_X_DELTA = 0.40
DEFAULT_COCKPIT_X_DELTA = 0.0

COCKPIT_FLAT_MATERIALS = {
    "gtvr_cockpit_black": ((4, 4, 4), "generated-gtvr-dev-cockpit-black"),
    "gtvr_cockpit_dark_gray": ((22, 24, 25), "generated-gtvr-dev-cockpit-dark-gray"),
    "gtvr_cockpit_seat": ((18, 20, 22), "generated-gtvr-dev-cockpit-seat"),
    "gtvr_cockpit_metal": ((88, 92, 92), "generated-gtvr-dev-cockpit-metal"),
    "gtvr_cockpit_rubber": ((7, 7, 7), "generated-gtvr-dev-cockpit-rubber"),
    "gtvr_cockpit_button_green": ((10, 150, 78), "generated-gtvr-dev-cockpit-button-green"),
    "gtvr_cockpit_button_red": ((190, 28, 24), "generated-gtvr-dev-cockpit-button-red"),
}
COCKPIT_PFD_MATERIAL = "gtvr_cockpit_pfd"
COCKPIT_MAP_MATERIAL = "gtvr_cockpit_map"
COCKPIT_PFD_TEXTURE = "gtvr_cockpit_pfd"
COCKPIT_MAP_TEXTURE = "gtvr_cockpit_map"

_ORIGINAL_PATCH_TMC = core.patch_tmc
_ORIGINAL_BUILD_BODY = core.build_body
_ORIGINAL_LEGACY_ROTOR_PATCH_MAPS = core.legacy_rotor_patch_maps
_current_pilot_alignment_x_delta = 0.0


def patch_dev_tmc(path: Path) -> None:
    _ORIGINAL_PATCH_TMC(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("<[stringt8c][ICAO][GTWE]>", f"<[stringt8c][ICAO][{DEV_ICAO}]>", 1)
    text = re.sub(r"<\[string8\]\[Pilot\]\[[^\]]+\]>", f"<[string8][Pilot][{DEV_PILOT}]>", text, count=1)
    path.write_text(text, encoding="utf-8")


def configure_core_for_dev() -> None:
    core.AIRCRAFT_NAME = DEV_AIRCRAFT_NAME
    core.DISPLAY_NAME = DEV_DISPLAY_NAME
    core.SOURCE_ROOT = DEV_SOURCE_ROOT
    core.SOURCE_DIR = DEV_SOURCE_DIR
    core.BUILD_USER = DEV_BUILD_USER
    core.PACKAGE_DIR = DEV_PACKAGE_DIR
    core.patch_tmc = patch_dev_tmc
    core.build_body = build_body_for_dev
    core.legacy_rotor_patch_maps = legacy_rotor_patch_maps_for_dev
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


def legacy_rotor_patch_maps_for_dev() -> tuple[dict[str, core.Patch], dict[str, core.Patch]]:
    main_rotor, tail_rotor = _ORIGINAL_LEGACY_ROTOR_PATCH_MAPS()
    if abs(_current_pilot_alignment_x_delta) > 1e-9:
        core.translate_patch_map(main_rotor, _current_pilot_alignment_x_delta, 0.0, 0.0)
        core.translate_patch_map(tail_rotor, _current_pilot_alignment_x_delta, 0.0, 0.0)
    return main_rotor, tail_rotor


def shift_visual_shell_for_pilot_alignment(
    args: argparse.Namespace,
    body: dict[str, core.Patch],
    tail_rotor: dict[str, core.Patch],
    visual_gear: dict[str, core.Patch],
) -> None:
    global _current_pilot_alignment_x_delta
    _current_pilot_alignment_x_delta = args.pilot_alignment_x_delta
    if abs(args.pilot_alignment_x_delta) < 1e-9:
        return
    core.translate_patch_map(body, args.pilot_alignment_x_delta, 0.0, 0.0)
    core.translate_patch_map(tail_rotor, args.pilot_alignment_x_delta, 0.0, 0.0)
    core.translate_patch_map(visual_gear, args.pilot_alignment_x_delta, 0.0, 0.0)
    print(
        "Dev pilot alignment: "
        f"shifted visual shell + rotors by X {args.pilot_alignment_x_delta:.3f}m around {DEV_PILOT}."
    )


def material_is_inner_shell_solid(material_name: str, skip_regex: str | None) -> bool:
    if not skip_regex:
        return True
    return re.search(skip_regex, material_name, re.IGNORECASE) is None


def append_reversed_face(
    source_patch: core.Patch,
    target_patch: core.Patch,
    source_indices: list[int],
    face_attribute: int,
) -> None:
    base_index = len(target_patch.vertices) // 8
    for source_index in (source_indices[0], source_indices[2], source_indices[1]):
        offset = source_index * 8
        vertex = list(source_patch.vertices[offset : offset + 8])
        vertex[3] = -vertex[3]
        vertex[4] = -vertex[4]
        vertex[5] = -vertex[5]
        target_patch.vertices.extend(vertex)
    target_patch.indices.extend([base_index, base_index + 1, base_index + 2])
    target_patch.face_attributes.append(face_attribute)


def make_patch_visible_from_inside(source_patch: core.Patch, target_patch: core.Patch) -> int:
    original_indices = list(source_patch.indices)
    original_face_attributes = list(source_patch.face_attributes)
    original_face_count = len(original_indices) // 3
    for face_index in range(original_face_count):
        start = face_index * 3
        face_indices = original_indices[start : start + 3]
        if len(face_indices) != 3:
            continue
        if original_face_attributes:
            face_attribute = original_face_attributes[face_index]
        else:
            face_attribute = 0
        append_reversed_face(source_patch, target_patch, face_indices, face_attribute)
    return original_face_count


def ensure_inner_shell_material(materials: dict[int, Material]) -> None:
    write_png(core.SOURCE_DIR / f"{INNER_SHELL_TEXTURE_NAME}.png", INNER_SHELL_COLOR)
    if any(material.name == INNER_SHELL_MATERIAL_NAME for material in materials.values()):
        return
    next_index = max(materials.keys(), default=-1) + 1
    materials[next_index] = Material(
        name=INNER_SHELL_MATERIAL_NAME,
        texture_name=INNER_SHELL_TEXTURE_NAME,
        source_uri="generated-gtvr-dev-inner-shell",
        color=(*INNER_SHELL_COLOR, 255),
    )


def next_material_index(materials: dict[int, Material]) -> int:
    return max(materials.keys(), default=-1) + 1


def add_generated_material(
    materials: dict[int, Material],
    *,
    name: str,
    texture_name: str,
    color: tuple[int, int, int],
    source_uri: str,
) -> None:
    if any(material.name == name for material in materials.values()):
        return
    write_png(core.SOURCE_DIR / f"{texture_name}.png", color)
    materials[next_material_index(materials)] = Material(
        name=name,
        texture_name=texture_name,
        source_uri=source_uri,
        color=(*color, 255),
    )


def load_font(size: int):
    from PIL import ImageFont

    for font_path in (
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ):
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def write_cockpit_pfd_texture(path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (512, 512), (4, 8, 10))
    draw = ImageDraw.Draw(image)
    small = load_font(22)
    medium = load_font(30)
    large = load_font(52)

    draw.rectangle((122, 48, 390, 250), fill=(22, 88, 132))
    draw.rectangle((122, 250, 390, 388), fill=(92, 55, 30))
    draw.line((122, 250, 390, 250), fill=(235, 235, 210), width=3)
    for offset in (-90, -45, 45, 90):
        draw.line((256 - 70, 250 + offset, 256 + 70, 250 + offset), fill=(220, 230, 230), width=2)
    draw.line((216, 250, 296, 250), fill=(255, 235, 90), width=5)
    draw.polygon([(256, 210), (244, 232), (268, 232)], fill=(255, 235, 90))

    draw.rectangle((18, 54, 106, 394), outline=(78, 220, 220), width=3)
    draw.text((34, 20), "SPD", font=small, fill=(130, 240, 240))
    for y, value in zip((86, 152, 218, 284, 350), ("140", "120", "100", "080", "060")):
        draw.text((36, y), value, font=medium, fill=(224, 255, 255))
        draw.line((88, y + 18, 104, y + 18), fill=(224, 255, 255), width=2)
    draw.rectangle((28, 220, 96, 282), outline=(255, 255, 255), width=3)
    draw.text((42, 232), "090", font=medium, fill=(255, 255, 255))

    draw.rectangle((406, 54, 494, 394), outline=(78, 220, 220), width=3)
    draw.text((428, 20), "ALT", font=small, fill=(130, 240, 240))
    for y, value in zip((86, 152, 218, 284, 350), ("1600", "1500", "1400", "1300", "1200")):
        draw.text((416, y), value, font=small, fill=(224, 255, 255))
        draw.line((406, y + 15, 424, y + 15), fill=(224, 255, 255), width=2)
    draw.rectangle((414, 220, 486, 282), outline=(255, 255, 255), width=3)
    draw.text((424, 236), "1420", font=small, fill=(255, 255, 255))

    draw.text((178, 402), "WRAITH", font=large, fill=(114, 230, 190))
    draw.text((186, 458), "ATT   IAS   ALT", font=small, fill=(190, 230, 220))
    image.save(path)


def write_cockpit_map_texture(path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (512, 512), (1, 14, 12))
    draw = ImageDraw.Draw(image)
    small = load_font(22)
    medium = load_font(32)
    large = load_font(44)

    for pos in range(32, 512, 48):
        draw.line((pos, 0, pos, 512), fill=(14, 78, 64), width=1)
        draw.line((0, pos, 512, pos), fill=(14, 78, 64), width=1)
    draw.ellipse((62, 62, 450, 450), outline=(30, 155, 122), width=3)
    draw.ellipse((150, 150, 362, 362), outline=(24, 105, 92), width=2)
    draw.line((256, 72, 256, 440), fill=(54, 188, 144), width=2)
    draw.line((72, 256, 440, 256), fill=(54, 188, 144), width=2)
    route = [(118, 358), (178, 304), (232, 278), (292, 230), (370, 168)]
    draw.line(route, fill=(245, 216, 70), width=6, joint="curve")
    for point in route:
        x, y = point
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(245, 216, 70))
    draw.polygon([(256, 220), (238, 286), (256, 276), (274, 286)], fill=(70, 220, 255))
    draw.text((28, 22), "ROLLING MAP", font=large, fill=(120, 245, 210))
    draw.text((26, 456), "HDG 084", font=medium, fill=(220, 255, 220))
    draw.text((354, 456), "GS 090", font=small, fill=(220, 255, 220))
    image.save(path)


def ensure_cockpit_materials(materials: dict[int, Material]) -> None:
    for material_name, (color, source_uri) in COCKPIT_FLAT_MATERIALS.items():
        add_generated_material(
            materials,
            name=material_name,
            texture_name=material_name,
            color=color,
            source_uri=source_uri,
        )

    pfd_path = core.SOURCE_DIR / f"{COCKPIT_PFD_TEXTURE}.png"
    map_path = core.SOURCE_DIR / f"{COCKPIT_MAP_TEXTURE}.png"
    write_cockpit_pfd_texture(pfd_path)
    write_cockpit_map_texture(map_path)
    if not any(material.name == COCKPIT_PFD_MATERIAL for material in materials.values()):
        materials[next_material_index(materials)] = Material(
            name=COCKPIT_PFD_MATERIAL,
            texture_name=COCKPIT_PFD_TEXTURE,
            source_uri="generated-gtvr-dev-cockpit-pfd",
            color=(24, 170, 180, 255),
        )
    if not any(material.name == COCKPIT_MAP_MATERIAL for material in materials.values()):
        materials[next_material_index(materials)] = Material(
            name=COCKPIT_MAP_MATERIAL,
            texture_name=COCKPIT_MAP_TEXTURE,
            source_uri="generated-gtvr-dev-cockpit-map",
            color=(20, 160, 120, 255),
        )


def patch_for(body: dict[str, core.Patch], material_name: str) -> core.Patch:
    return body.setdefault(material_name, core.Patch(material_name))


def vector_sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vector_add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vector_mul(a: tuple[float, float, float], value: float) -> tuple[float, float, float]:
    return (a[0] * value, a[1] * value, a[2] * value)


def vector_cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vector_length(a: tuple[float, float, float]) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def vector_normalize(a: tuple[float, float, float]) -> tuple[float, float, float]:
    length = vector_length(a)
    if length < 1e-9:
        return (0.0, 0.0, 1.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def append_quad(
    patch: core.Patch,
    points: list[tuple[float, float, float]],
    normal: tuple[float, float, float],
    uvs: list[tuple[float, float]] | None = None,
) -> None:
    if uvs is None:
        uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    base_index = len(patch.vertices) // 8
    for point, uv in zip(points, uvs):
        patch.vertices.extend([point[0], point[1], point[2], normal[0], normal[1], normal[2], uv[0], uv[1]])
    patch.indices.extend([base_index, base_index + 1, base_index + 2, base_index, base_index + 2, base_index + 3])
    patch.face_attributes.extend([0, 0])


def append_box(
    body: dict[str, core.Patch],
    material_name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
) -> None:
    patch = patch_for(body, material_name)
    x, y, z = center
    sx, sy, sz = (size[0] * 0.5, size[1] * 0.5, size[2] * 0.5)
    minx, maxx = x - sx, x + sx
    miny, maxy = y - sy, y + sy
    minz, maxz = z - sz, z + sz
    append_quad(patch, [(maxx, miny, minz), (maxx, maxy, minz), (maxx, maxy, maxz), (maxx, miny, maxz)], (1, 0, 0))
    append_quad(patch, [(minx, miny, minz), (minx, miny, maxz), (minx, maxy, maxz), (minx, maxy, minz)], (-1, 0, 0))
    append_quad(patch, [(minx, maxy, minz), (minx, maxy, maxz), (maxx, maxy, maxz), (maxx, maxy, minz)], (0, 1, 0))
    append_quad(patch, [(minx, miny, minz), (maxx, miny, minz), (maxx, miny, maxz), (minx, miny, maxz)], (0, -1, 0))
    append_quad(patch, [(minx, miny, maxz), (maxx, miny, maxz), (maxx, maxy, maxz), (minx, maxy, maxz)], (0, 0, 1))
    append_quad(patch, [(minx, miny, minz), (minx, maxy, minz), (maxx, maxy, minz), (maxx, miny, minz)], (0, 0, -1))


def append_cylinder_between(
    body: dict[str, core.Patch],
    material_name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    *,
    segments: int = 10,
) -> None:
    patch = patch_for(body, material_name)
    axis = vector_sub(end, start)
    axis_unit = vector_normalize(axis)
    reference = (0.0, 0.0, 1.0) if abs(axis_unit[2]) < 0.92 else (0.0, 1.0, 0.0)
    right = vector_normalize(vector_cross(axis_unit, reference))
    up = vector_normalize(vector_cross(right, axis_unit))
    start_ring: list[tuple[float, float, float]] = []
    end_ring: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    for index in range(segments):
        angle = index / segments * math.tau
        radial = vector_add(vector_mul(right, math.cos(angle)), vector_mul(up, math.sin(angle)))
        normals.append(radial)
        start_ring.append(vector_add(start, vector_mul(radial, radius)))
        end_ring.append(vector_add(end, vector_mul(radial, radius)))

    for index in range(segments):
        next_index = (index + 1) % segments
        base = len(patch.vertices) // 8
        for point, normal, uv in (
            (start_ring[index], normals[index], (index / segments, 0.0)),
            (start_ring[next_index], normals[next_index], (next_index / segments, 0.0)),
            (end_ring[next_index], normals[next_index], (next_index / segments, 1.0)),
            (end_ring[index], normals[index], (index / segments, 1.0)),
        ):
            patch.vertices.extend([point[0], point[1], point[2], normal[0], normal[1], normal[2], uv[0], uv[1]])
        patch.indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])
        patch.face_attributes.extend([0, 0])

    append_cap(patch, start, list(reversed(start_ring)), vector_mul(axis_unit, -1.0))
    append_cap(patch, end, end_ring, axis_unit)


def append_cap(
    patch: core.Patch,
    center: tuple[float, float, float],
    ring: list[tuple[float, float, float]],
    normal: tuple[float, float, float],
) -> None:
    center_index = len(patch.vertices) // 8
    patch.vertices.extend([center[0], center[1], center[2], normal[0], normal[1], normal[2], 0.5, 0.5])
    for point in ring:
        patch.vertices.extend([point[0], point[1], point[2], normal[0], normal[1], normal[2], 0.5, 0.5])
    for index in range(len(ring)):
        patch.indices.extend([center_index, center_index + 1 + index, center_index + 1 + ((index + 1) % len(ring))])
        patch.face_attributes.append(0)


def append_textured_panel(
    body: dict[str, core.Patch],
    material_name: str,
    *,
    center: tuple[float, float, float],
    width_y: float,
    height_z: float,
) -> None:
    patch = patch_for(body, material_name)
    x, y, z = center
    half_w = width_y * 0.5
    half_h = height_z * 0.5
    front = [
        (x, y - half_w, z - half_h),
        (x, y - half_w, z + half_h),
        (x, y + half_w, z + half_h),
        (x, y + half_w, z - half_h),
    ]
    append_quad(patch, front, (-1.0, 0.0, 0.0), [(0.0, 1.0), (0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
    append_quad(patch, list(reversed(front)), (1.0, 0.0, 0.0), [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)])


def add_framed_screen(
    body: dict[str, core.Patch],
    *,
    material_name: str,
    center: tuple[float, float, float],
    width_y: float = 0.285,
    height_z: float = 0.17,
) -> None:
    x, y, z = center
    append_box(body, "gtvr_cockpit_black", (x + 0.012, y, z), (0.035, width_y + 0.055, height_z + 0.055))
    append_textured_panel(body, material_name, center=(x - 0.008, y, z), width_y=width_y, height_z=height_z)


def add_cockpit_kit(args: argparse.Namespace, materials: dict[int, Material], body: dict[str, core.Patch]) -> None:
    if not args.cockpit_kit:
        return
    ensure_cockpit_materials(materials)
    x_delta = args.cockpit_x_delta
    x = lambda value: value + x_delta

    append_box(body, "gtvr_cockpit_dark_gray", (x(1.62), 0.0, -0.775), (1.55, 1.34, 0.055))
    append_box(body, "gtvr_cockpit_black", (x(2.30), 0.0, -0.31), (0.56, 1.18, 0.14))
    append_box(body, "gtvr_cockpit_black", (x(2.23), 0.0, 0.095), (0.52, 1.16, 0.075))
    append_box(body, "gtvr_cockpit_dark_gray", (x(1.78), 0.0, -0.55), (0.78, 0.22, 0.28))
    append_box(body, "gtvr_cockpit_black", (x(1.94), 0.0, -0.37), (0.40, 0.18, 0.11))

    for seat_y in (-0.40, 0.40):
        append_box(body, "gtvr_cockpit_seat", (x(1.28), seat_y, -0.67), (0.58, 0.42, 0.13))
        append_box(body, "gtvr_cockpit_seat", (x(0.98), seat_y, -0.37), (0.13, 0.42, 0.58))
        append_box(body, "gtvr_cockpit_black", (x(0.91), seat_y, -0.01), (0.11, 0.34, 0.18))
        append_box(body, "gtvr_cockpit_dark_gray", (x(1.35), seat_y, -0.575), (0.42, 0.32, 0.035))

    screen_x = x(2.47)
    for side_y in (-0.34, 0.20):
        add_framed_screen(body, material_name=COCKPIT_PFD_MATERIAL, center=(screen_x, side_y, 0.015))
        add_framed_screen(body, material_name=COCKPIT_MAP_MATERIAL, center=(screen_x, side_y, -0.205), height_z=0.155)
        append_box(body, "gtvr_cockpit_metal", (x(2.43), side_y - 0.18, -0.095), (0.035, 0.028, 0.40))
        append_box(body, "gtvr_cockpit_metal", (x(2.43), side_y + 0.18, -0.095), (0.035, 0.028, 0.40))

    for center_y in (-0.07, 0.07):
        append_cylinder_between(
            body,
            "gtvr_cockpit_metal",
            (x(2.44), center_y, -0.125),
            (x(2.425), center_y, -0.125),
            0.052,
            segments=18,
        )
        append_cylinder_between(
            body,
            "gtvr_cockpit_rubber",
            (x(2.418), center_y, -0.125),
            (x(2.405), center_y, -0.125),
            0.038,
            segments=18,
        )

    for stick_y in (-0.38, 0.40):
        append_cylinder_between(body, "gtvr_cockpit_metal", (x(2.25), stick_y, -0.64), (x(2.23), stick_y, -0.24), 0.023)
        append_cylinder_between(body, "gtvr_cockpit_rubber", (x(2.22), stick_y, -0.22), (x(2.31), stick_y, -0.13), 0.045)
        append_box(body, "gtvr_cockpit_button_red", (x(2.295), stick_y - 0.028, -0.105), (0.032, 0.018, 0.014))
        append_box(body, "gtvr_cockpit_button_green", (x(2.295), stick_y + 0.028, -0.105), (0.032, 0.018, 0.014))

    for start_y, end_y in ((-0.58, -0.11), (0.58, 0.63)):
        append_cylinder_between(body, "gtvr_cockpit_metal", (x(1.67), start_y, -0.66), (x(2.08), end_y, -0.49), 0.022)
        append_cylinder_between(body, "gtvr_cockpit_rubber", (x(2.04), end_y, -0.505), (x(2.16), end_y, -0.455), 0.030)
        append_cylinder_between(body, "gtvr_cockpit_metal", (x(2.08), end_y - 0.035, -0.50), (x(2.14), end_y - 0.035, -0.475), 0.017)
        append_cylinder_between(body, "gtvr_cockpit_metal", (x(2.08), end_y + 0.035, -0.50), (x(2.14), end_y + 0.035, -0.475), 0.017)

    for seat_y in (-0.40, 0.40):
        for pedal_offset in (-0.12, 0.12):
            pedal_y = seat_y + pedal_offset
            append_cylinder_between(body, "gtvr_cockpit_metal", (x(1.96), pedal_y, -0.73), (x(2.21), pedal_y, -0.60), 0.016)
            append_box(body, "gtvr_cockpit_rubber", (x(2.26), pedal_y, -0.56), (0.055, 0.13, 0.10))

    print(
        "Dev cockpit kit: added seats, cyclics, collectives/throttles, pedals, "
        "dual PFD/map glass displays and panel hardware."
    )


def make_inner_shell_opaque(body: dict[str, core.Patch], skip_regex: str | None) -> tuple[int, list[str]]:
    duplicated_faces = 0
    skipped_materials: list[str] = []
    inner_patch = body.setdefault(INNER_SHELL_MATERIAL_NAME, core.Patch(INNER_SHELL_MATERIAL_NAME))
    for material_name, patch in list(body.items()):
        if material_name == INNER_SHELL_MATERIAL_NAME:
            continue
        if not material_is_inner_shell_solid(material_name, skip_regex):
            skipped_materials.append(material_name)
            continue
        duplicated_faces += make_patch_visible_from_inside(patch, inner_patch)
    return duplicated_faces, skipped_materials


def build_body_for_dev(args: argparse.Namespace):
    materials, body, tail_rotor, visual_gear, source_faces, imported_faces = _ORIGINAL_BUILD_BODY(args)
    shift_visual_shell_for_pilot_alignment(args, body, tail_rotor, visual_gear)
    if args.inner_shell:
        ensure_inner_shell_material(materials)
        duplicated_faces, skipped_materials = make_inner_shell_opaque(
            body,
            args.inner_shell_skip_material_regex,
        )
        print(
            "Dev inner shell: "
            f"duplicated {duplicated_faces} solid faces into {INNER_SHELL_MATERIAL_NAME}."
        )
        if skipped_materials:
            skipped_preview = ", ".join(sorted(skipped_materials)[:12])
            suffix = "..." if len(skipped_materials) > 12 else ""
            print(f"Dev inner shell: skipped transparent/non-solid materials: {skipped_preview}{suffix}")
    add_cockpit_kit(args, materials, body)
    return materials, body, tail_rotor, visual_gear, source_faces, imported_faces


def write_source_stamp() -> None:
    DEV_SOURCE_STAMP.write_text(
        "\n".join(
            [
                "GTVR Wraith Dev source prepared.",
                f"aircraft={DEV_AIRCRAFT_NAME}",
                f"display={DEV_DISPLAY_NAME}",
                f"inner_shell=solid materials are duplicated inward into {INNER_SHELL_MATERIAL_NAME}",
                "cockpit_kit=generated seats, controls, pedals and static glass displays",
                f"pilot_alignment_x_delta={_current_pilot_alignment_x_delta:.3f}",
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
                "Solid shell materials include inward-facing matte black faces for cockpit-side opacity.",
                "Generated cockpit kit includes seats, cyclics, collectives/throttles, pedals and static PFD/map displays.",
                f"Dev pilot uses {DEV_PILOT}, the known-good EC135 pilot object.",
                f"Visual shell is shifted X {DEFAULT_PILOT_ALIGNMENT_X_DELTA:.2f}m for pilot/window alignment.",
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
    parser.add_argument(
        "--pilot-alignment-x-delta",
        type=float,
        default=DEFAULT_PILOT_ALIGNMENT_X_DELTA,
        help="Dev-only visual shell X shift used to align the fixed EC135 pilot with the Wraith side window.",
    )
    parser.add_argument(
        "--cockpit-x-delta",
        type=float,
        default=DEFAULT_COCKPIT_X_DELTA,
        help="Dev-only X tuning offset for generated cockpit seats, controls and displays.",
    )
    parser.add_argument("--no-yaw-180", dest="yaw_180", action="store_false")
    parser.set_defaults(yaw_180=True)
    parser.add_argument(
        "--no-inner-shell",
        dest="inner_shell",
        action="store_false",
        help="Do not duplicate solid shell faces inward for cockpit-side visibility.",
    )
    parser.set_defaults(inner_shell=True)
    parser.add_argument(
        "--inner-shell-skip-material-regex",
        default=DEFAULT_INNER_SHELL_SKIP_MATERIAL_REGEX,
        help="Material names matching this regex are not inward-duplicated.",
    )
    parser.add_argument(
        "--no-cockpit-kit",
        dest="cockpit_kit",
        action="store_false",
        help="Do not add the generated cockpit seats, controls, pedals and static displays.",
    )
    parser.set_defaults(cockpit_kit=True)


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
