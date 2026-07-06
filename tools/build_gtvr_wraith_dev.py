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
DEFAULT_INTERIOR_FORWARD_X_DELTA = 0.32
DEFAULT_DASH_FORWARD_X_DELTA = 0.55
DISPLAY_FALLBACK_X_OFFSET = 0.006
CONTROL_MATTE_BLACK_MATERIAL = "gtvr_control_black"
SEAT_Z_LIFT = 0.16
PEDAL_Z_LIFT = -0.03
PEDAL_X_REARWARD = 0.18
HIDDEN_DEV_CLICKSPOT_RE = re.compile(
    r"^(?:pilotstick|copilotstick|stick|pilotpushtotalk|copilotpushtotalk|"
    r"collective|throttle|noselandinglight|enginestrim|coolielandinglight|.*cyclic.*|.*pedal.*)",
    re.IGNORECASE,
)
HIDDEN_DEV_STATIC_VISUAL_RE = re.compile(
    r"^(?:"
    r"CHCollectiveL0|CHCollectiveL1|CHCollectiveR0|CHCollectiveR1|"
    r"LeftCollectiveLeverHead|RightCollectiveLeverHead|"
    r"LLPedalCont|LRPedalCont|RLPedalCont|RRPedalCont|Pedalsupport|"
    r"LeftCyclicCont|LeftCyclicLink|RightCyclicCont|Rightcycliclink|"
    r"StickL.*|StickR.*|StickBagLeft|StickBagRight|PitchCont|PitchSlider|PitchbagL|PitchbagR"
    r")$",
    re.IGNORECASE,
)

COCKPIT_FLAT_MATERIALS = {
    "gtvr_cockpit_black": ((4, 4, 4), "generated-gtvr-dev-cockpit-black"),
    "gtvr_control_black": ((0, 0, 0), "generated-gtvr-dev-control-black"),
    "gtvr_cockpit_dark_gray": ((22, 24, 25), "generated-gtvr-dev-cockpit-dark-gray"),
    "gtvr_cockpit_seat": ((18, 20, 22), "generated-gtvr-dev-cockpit-seat"),
    "gtvr_cockpit_seat_highlight": ((36, 39, 40), "generated-gtvr-dev-cockpit-seat-highlight"),
    "gtvr_cockpit_seat_shadow": ((9, 10, 11), "generated-gtvr-dev-cockpit-seat-shadow"),
    "gtvr_cockpit_metal": ((88, 92, 92), "generated-gtvr-dev-cockpit-metal"),
    "gtvr_cockpit_rubber": ((7, 7, 7), "generated-gtvr-dev-cockpit-rubber"),
    "gtvr_cockpit_button_green": ((10, 150, 78), "generated-gtvr-dev-cockpit-button-green"),
    "gtvr_cockpit_button_red": ((190, 28, 24), "generated-gtvr-dev-cockpit-button-red"),
    "gtvr_glass_sky": ((18, 86, 134), "generated-gtvr-dev-glass-sky"),
    "gtvr_glass_ground": ((96, 56, 32), "generated-gtvr-dev-glass-ground"),
    "gtvr_glass_cyan": ((58, 220, 220), "generated-gtvr-dev-glass-cyan"),
    "gtvr_glass_green": ((80, 235, 170), "generated-gtvr-dev-glass-green"),
    "gtvr_glass_white": ((225, 245, 238), "generated-gtvr-dev-glass-white"),
    "gtvr_glass_yellow": ((245, 210, 72), "generated-gtvr-dev-glass-yellow"),
}
DEV_INTERIOR_SHADER_MATERIALS = {
    "gtvr_cockpit_black",
    "gtvr_control_black",
    "gtvr_cockpit_dark_gray",
    "gtvr_cockpit_seat",
    "gtvr_cockpit_seat_highlight",
    "gtvr_cockpit_seat_shadow",
    "gtvr_cockpit_metal",
    "gtvr_cockpit_rubber",
    "gtvr_cockpit_button_green",
    "gtvr_cockpit_button_red",
    INNER_SHELL_MATERIAL_NAME,
}
COCKPIT_PFD_MATERIAL = "gtvr_cockpit_flight"
COCKPIT_MAP_MATERIAL = "gtvr_cockpit_map"
COCKPIT_PFD_TEXTURE = "gtvr_cockpit_flight"
COCKPIT_MAP_TEXTURE = "gtvr_cockpit_map"

_ORIGINAL_PATCH_TMC = core.patch_tmc
_ORIGINAL_BUILD_BODY = core.build_body
_ORIGINAL_LEGACY_ROTOR_PATCH_MAPS = core.legacy_rotor_patch_maps
_current_pilot_alignment_x_delta = 0.0
_current_cockpit_x_delta = DEFAULT_COCKPIT_X_DELTA
_current_interior_forward_x_delta = DEFAULT_INTERIOR_FORWARD_X_DELTA
_current_dash_forward_x_delta = DEFAULT_DASH_FORWARD_X_DELTA
_current_animated_control_geometries: dict[str, dict[str, core.Patch]] = {}
_current_live_display_geometries: dict[str, dict[str, core.Patch]] = {}
_current_live_display_pivots: dict[str, tuple[float, float, float]] = {}
_current_stock_display_geometries: dict[str, dict[str, core.Patch]] = {}


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
    core.prepare_source = prepare_source_for_dev
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
    small = load_font(21)
    medium = load_font(30)
    large = load_font(46)

    draw.rounded_rectangle((14, 12, 498, 500), radius=18, fill=(5, 12, 15), outline=(74, 190, 190), width=4)
    draw.rectangle((118, 56, 394, 246), fill=(20, 94, 146))
    draw.rectangle((118, 246, 394, 374), fill=(92, 56, 32))
    draw.line((118, 246, 394, 246), fill=(238, 238, 215), width=4)
    for offset in (-80, -40, 40, 80):
        draw.line((196, 246 + offset, 316, 246 + offset), fill=(220, 230, 230), width=2)
    draw.line((214, 246, 298, 246), fill=(255, 235, 90), width=5)
    draw.polygon([(256, 206), (242, 230), (270, 230)], fill=(255, 235, 90))

    draw.rectangle((25, 62, 105, 382), outline=(78, 220, 220), width=3)
    draw.text((38, 26), "SPD", font=small, fill=(130, 240, 240))
    for y, value in zip((88, 150, 212, 274, 336), ("130", "110", "090", "070", "050")):
        draw.text((43, y), value, font=small, fill=(224, 255, 255))
        draw.line((88, y + 14, 104, y + 14), fill=(224, 255, 255), width=2)
    draw.rectangle((32, 216, 100, 274), outline=(255, 255, 255), width=3)
    draw.text((47, 230), "092", font=medium, fill=(255, 255, 255))

    draw.rectangle((407, 62, 487, 382), outline=(78, 220, 220), width=3)
    draw.text((427, 26), "ALT", font=small, fill=(130, 240, 240))
    for y, value in zip((88, 150, 212, 274, 336), ("1600", "1500", "1400", "1300", "1200")):
        draw.text((416, y), value, font=small, fill=(224, 255, 255))
        draw.line((407, y + 14, 423, y + 14), fill=(224, 255, 255), width=2)
    draw.rectangle((413, 216, 483, 274), outline=(255, 255, 255), width=3)
    draw.text((420, 232), "1420", font=small, fill=(255, 255, 255))

    draw.text((178, 398), "WRAITH", font=large, fill=(114, 230, 190))
    draw.text((154, 450), "ATT   IAS   ALT", font=medium, fill=(190, 230, 220))
    image.save(path)


def write_cockpit_map_texture(path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (512, 512), (1, 14, 12))
    draw = ImageDraw.Draw(image)
    small = load_font(22)
    medium = load_font(32)
    large = load_font(42)

    draw.rounded_rectangle((14, 12, 498, 500), radius=18, fill=(2, 16, 14), outline=(62, 205, 160), width=4)
    for pos in range(42, 512, 46):
        draw.line((pos, 60, pos, 430), fill=(14, 78, 64), width=1)
        draw.line((34, pos, 478, pos), fill=(14, 78, 64), width=1)
    draw.ellipse((70, 82, 442, 454), outline=(30, 155, 122), width=3)
    draw.ellipse((154, 166, 358, 370), outline=(24, 105, 92), width=2)
    draw.line((256, 92, 256, 444), fill=(54, 188, 144), width=2)
    draw.line((72, 268, 440, 268), fill=(54, 188, 144), width=2)
    route = [(118, 366), (178, 315), (232, 288), (298, 238), (378, 170)]
    draw.line(route, fill=(245, 216, 70), width=6, joint="curve")
    for point in route:
        x, y = point
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(245, 216, 70))
    draw.polygon([(256, 224), (238, 292), (256, 282), (274, 292)], fill=(70, 220, 255))
    draw.text((34, 28), "ROLLING MAP", font=large, fill=(120, 245, 210))
    draw.text((36, 452), "HDG 084", font=medium, fill=(220, 255, 220))
    draw.text((364, 458), "GS 092", font=small, fill=(220, 255, 220))
    image.save(path)


def write_cockpit_seat_texture(path: Path, base: tuple[int, int, int], seam: tuple[int, int, int]) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (128, 128), base)
    draw = ImageDraw.Draw(image)
    for y in range(0, 128, 7):
        shade = tuple(max(0, min(255, channel + (4 if (y // 7) % 2 else -3))) for channel in base)
        draw.rectangle((0, y, 128, min(127, y + 3)), fill=shade)
    for x in range(12, 128, 24):
        draw.line((x, 0, x, 127), fill=seam, width=1)
    for y in range(16, 128, 32):
        draw.line((0, y, 127, y), fill=seam, width=1)
    for x in range(8, 128, 16):
        for y in range(8, 128, 16):
            dot = tuple(max(0, channel - 7) for channel in base)
            draw.point((x, y), fill=dot)
            draw.point((x + 1, y), fill=dot)
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

    write_cockpit_seat_texture(core.SOURCE_DIR / "gtvr_cockpit_seat.png", (21, 24, 25), (39, 44, 45))
    write_cockpit_seat_texture(core.SOURCE_DIR / "gtvr_cockpit_seat_highlight.png", (39, 43, 44), (62, 68, 69))
    write_cockpit_seat_texture(core.SOURCE_DIR / "gtvr_cockpit_seat_shadow.png", (8, 9, 10), (22, 24, 25))

    pfd_path = core.SOURCE_DIR / f"{COCKPIT_PFD_TEXTURE}.png"
    map_path = core.SOURCE_DIR / f"{COCKPIT_MAP_TEXTURE}.png"
    write_cockpit_pfd_texture(pfd_path)
    write_cockpit_map_texture(map_path)
    if not any(material.name == COCKPIT_PFD_MATERIAL for material in materials.values()):
        materials[next_material_index(materials)] = Material(
            name=COCKPIT_PFD_MATERIAL,
            texture_name=COCKPIT_PFD_TEXTURE,
            source_uri="generated-gtvr-dev-cockpit-flight",
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


def animated_control_geometry(name: str) -> dict[str, core.Patch]:
    return _current_animated_control_geometries.setdefault(name, {})


def live_display_geometry(name: str) -> dict[str, core.Patch]:
    return _current_live_display_geometries.setdefault(name, {})


def stock_display_geometry(name: str) -> dict[str, core.Patch]:
    return _current_stock_display_geometries.setdefault(name, {})


def merge_patch_map_into(target: dict[str, core.Patch], source: dict[str, core.Patch]) -> None:
    for material_name, source_patch in source.items():
        target_patch = target.setdefault(material_name, core.Patch(material_name))
        vertex_offset = len(target_patch.vertices) // 8
        target_patch.vertices.extend(source_patch.vertices)
        target_patch.indices.extend(index + vertex_offset for index in source_patch.indices)
        target_patch.face_attributes.extend(source_patch.face_attributes)


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
    caps: bool = True,
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

    if caps:
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
    append_quad(patch, front, (-1.0, 0.0, 0.0), [(1.0, 1.0), (1.0, 0.0), (0.0, 0.0), (0.0, 1.0)])
    append_quad(patch, list(reversed(front)), (1.0, 0.0, 0.0), [(0.0, 1.0), (0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])


def append_triangle(
    patch: core.Patch,
    points: list[tuple[float, float, float]],
    normal: tuple[float, float, float],
) -> None:
    base_index = len(patch.vertices) // 8
    for point in points:
        patch.vertices.extend([point[0], point[1], point[2], normal[0], normal[1], normal[2], 0.5, 0.5])
    patch.indices.extend([base_index, base_index + 1, base_index + 2])
    patch.face_attributes.append(0)


def append_auto_quad(
    body: dict[str, core.Patch],
    material_name: str,
    points: list[tuple[float, float, float]],
    uvs: list[tuple[float, float]] | None = None,
) -> None:
    edge_a = vector_sub(points[1], points[0])
    edge_b = vector_sub(points[2], points[0])
    normal = vector_normalize(vector_cross(edge_a, edge_b))
    append_quad(patch_for(body, material_name), points, normal, uvs)


def append_pillowed_seat_cushion(
    body: dict[str, core.Patch],
    material_name: str,
    *,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    segments_x: int = 12,
    segments_y: int = 10,
) -> None:
    cx, cy, cz = center
    sx, sy, sz = size
    min_x, max_x = cx - sx * 0.5, cx + sx * 0.5
    min_y, max_y = cy - sy * 0.5, cy + sy * 0.5
    bottom_z = cz - sz * 0.5
    top_z = cz + sz * 0.5
    edge_drop = sz * 0.42
    crown = sz * 0.08

    def point_at(u: float, v: float) -> tuple[float, float, float]:
        nx = abs(u * 2.0 - 1.0)
        ny = abs(v * 2.0 - 1.0)
        edge = max(nx, ny)
        edge_fall = max(0.0, (edge - 0.68) / 0.32)
        crown_shape = max(0.0, 1.0 - min(1.0, (nx * nx + ny * ny) * 0.55))
        return (
            min_x + sx * u,
            min_y + sy * v,
            top_z - edge_drop * edge_fall * edge_fall + crown * crown_shape,
        )

    for ix in range(segments_x):
        u0 = ix / segments_x
        u1 = (ix + 1) / segments_x
        for iy in range(segments_y):
            v0 = iy / segments_y
            v1 = (iy + 1) / segments_y
            append_auto_quad(
                body,
                material_name,
                [point_at(u0, v0), point_at(u1, v0), point_at(u1, v1), point_at(u0, v1)],
                [(u0, v0), (u1, v0), (u1, v1), (u0, v1)],
            )

    for iy in range(segments_y):
        v0 = iy / segments_y
        v1 = (iy + 1) / segments_y
        top0 = point_at(1.0, v0)
        top1 = point_at(1.0, v1)
        append_auto_quad(body, material_name, [(max_x, top0[1], bottom_z), (max_x, top1[1], bottom_z), top1, top0])
        top0 = point_at(0.0, v0)
        top1 = point_at(0.0, v1)
        append_auto_quad(body, material_name, [(min_x, top1[1], bottom_z), (min_x, top0[1], bottom_z), top0, top1])

    for ix in range(segments_x):
        u0 = ix / segments_x
        u1 = (ix + 1) / segments_x
        top0 = point_at(u0, 1.0)
        top1 = point_at(u1, 1.0)
        append_auto_quad(body, material_name, [(top0[0], max_y, bottom_z), (top0[0], max_y, top0[2]), (top1[0], max_y, top1[2]), (top1[0], max_y, bottom_z)])
        top0 = point_at(u0, 0.0)
        top1 = point_at(u1, 0.0)
        append_auto_quad(body, material_name, [(top1[0], min_y, bottom_z), (top1[0], min_y, top1[2]), (top0[0], min_y, top0[2]), (top0[0], min_y, bottom_z)])


def append_pillowed_back_cushion(
    body: dict[str, core.Patch],
    material_name: str,
    *,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    segments_y: int = 10,
    segments_z: int = 12,
) -> None:
    cx, cy, cz = center
    sx, sy, sz = size
    back_x = cx - sx * 0.5
    front_x = cx + sx * 0.5
    min_y, max_y = cy - sy * 0.5, cy + sy * 0.5
    min_z, max_z = cz - sz * 0.5, cz + sz * 0.5
    edge_drop = sx * 0.55
    crown = sx * 0.20

    def point_at(u: float, v: float) -> tuple[float, float, float]:
        ny = abs(u * 2.0 - 1.0)
        nz = abs(v * 2.0 - 1.0)
        edge = max(ny, nz)
        edge_fall = max(0.0, (edge - 0.68) / 0.32)
        crown_shape = max(0.0, 1.0 - min(1.0, (ny * ny + nz * nz) * 0.55))
        return (
            front_x - edge_drop * edge_fall * edge_fall + crown * crown_shape,
            min_y + sy * u,
            min_z + sz * v,
        )

    for iy in range(segments_y):
        u0 = iy / segments_y
        u1 = (iy + 1) / segments_y
        for iz in range(segments_z):
            v0 = iz / segments_z
            v1 = (iz + 1) / segments_z
            append_auto_quad(
                body,
                material_name,
                [point_at(u0, v0), point_at(u1, v0), point_at(u1, v1), point_at(u0, v1)],
                [(u0, v0), (u1, v0), (u1, v1), (u0, v1)],
            )

    for iy in range(segments_y):
        u0 = iy / segments_y
        u1 = (iy + 1) / segments_y
        top0 = point_at(u0, 1.0)
        top1 = point_at(u1, 1.0)
        append_auto_quad(body, material_name, [(back_x, top0[1], max_z), top0, top1, (back_x, top1[1], max_z)])
        bottom0 = point_at(u0, 0.0)
        bottom1 = point_at(u1, 0.0)
        append_auto_quad(body, material_name, [(back_x, bottom1[1], min_z), bottom1, bottom0, (back_x, bottom0[1], min_z)])

    for iz in range(segments_z):
        v0 = iz / segments_z
        v1 = (iz + 1) / segments_z
        side0 = point_at(0.0, v0)
        side1 = point_at(0.0, v1)
        append_auto_quad(body, material_name, [(back_x, min_y, side1[2]), side1, side0, (back_x, min_y, side0[2])])
        side0 = point_at(1.0, v0)
        side1 = point_at(1.0, v1)
        append_auto_quad(body, material_name, [(back_x, max_y, side0[2]), side0, side1, (back_x, max_y, side1[2])])


def append_panel_rect(
    body: dict[str, core.Patch],
    material_name: str,
    *,
    x: float,
    center_y: float,
    center_z: float,
    width_y: float,
    height_z: float,
) -> None:
    half_w = width_y * 0.5
    half_h = height_z * 0.5
    patch = patch_for(body, material_name)
    append_quad(
        patch,
        [
            (x, center_y - half_w, center_z - half_h),
            (x, center_y - half_w, center_z + half_h),
            (x, center_y + half_w, center_z + half_h),
            (x, center_y + half_w, center_z - half_h),
        ],
        (-1.0, 0.0, 0.0),
    )


def append_panel_line(
    body: dict[str, core.Patch],
    material_name: str,
    *,
    x: float,
    start_y: float,
    start_z: float,
    end_y: float,
    end_z: float,
    thickness: float,
) -> None:
    dy = end_y - start_y
    dz = end_z - start_z
    length = math.sqrt(dy * dy + dz * dz)
    if length < 1e-9:
        append_panel_rect(
            body,
            material_name,
            x=x,
            center_y=start_y,
            center_z=start_z,
            width_y=thickness,
            height_z=thickness,
        )
        return
    offset_y = -dz / length * thickness * 0.5
    offset_z = dy / length * thickness * 0.5
    patch = patch_for(body, material_name)
    append_quad(
        patch,
        [
            (x, start_y + offset_y, start_z + offset_z),
            (x, end_y + offset_y, end_z + offset_z),
            (x, end_y - offset_y, end_z - offset_z),
            (x, start_y - offset_y, start_z - offset_z),
        ],
        (-1.0, 0.0, 0.0),
    )


def append_panel_triangle(
    body: dict[str, core.Patch],
    material_name: str,
    *,
    x: float,
    points_yz: list[tuple[float, float]],
) -> None:
    if len(points_yz) != 3:
        raise ValueError("Panel triangle requires three Y/Z points")
    patch = patch_for(body, material_name)
    append_triangle(patch, [(x, y, z) for y, z in points_yz], (-1.0, 0.0, 0.0))


def append_panel_ring(
    body: dict[str, core.Patch],
    material_name: str,
    *,
    x: float,
    center_y: float,
    center_z: float,
    radius: float,
    thickness: float,
    segments: int = 24,
) -> None:
    previous: tuple[float, float] | None = None
    first: tuple[float, float] | None = None
    for index in range(segments + 1):
        angle = index / segments * math.tau
        point = (center_y + math.cos(angle) * radius, center_z + math.sin(angle) * radius)
        if previous is not None:
            append_panel_line(
                body,
                material_name,
                x=x,
                start_y=previous[0],
                start_z=previous[1],
                end_y=point[0],
                end_z=point[1],
                thickness=thickness,
            )
        elif first is None:
            first = point
        previous = point
    if previous is not None and first is not None:
        append_panel_line(
            body,
            material_name,
            x=x,
            start_y=previous[0],
            start_z=previous[1],
            end_y=first[0],
            end_z=first[1],
            thickness=thickness,
        )


def add_framed_screen(
    body: dict[str, core.Patch],
    *,
    material_name: str,
    center: tuple[float, float, float],
    width_y: float = 0.285,
    height_z: float = 0.17,
) -> None:
    x, y, z = center
    append_box(body, CONTROL_MATTE_BLACK_MATERIAL, (x + 0.012, y, z), (0.035, width_y + 0.055, height_z + 0.055))
    append_textured_panel(body, material_name, center=(x - 0.008, y, z), width_y=width_y, height_z=height_z)


def add_dashboard_frame(body: dict[str, core.Patch], dash_x) -> None:
    panel_x = dash_x(2.47)
    rail_x = dash_x(2.45)

    append_box(body, CONTROL_MATTE_BLACK_MATERIAL, (rail_x, 0.0, 0.080), (0.13, 1.22, 0.070))
    append_box(body, CONTROL_MATTE_BLACK_MATERIAL, (rail_x, 0.0, -0.330), (0.13, 1.22, 0.075))

    for post_y in (-0.155, 0.155):
        append_box(body, CONTROL_MATTE_BLACK_MATERIAL, (rail_x, post_y, -0.125), (0.12, 0.048, 0.390))


def add_pfd_static_overlay(static: dict[str, core.Patch], *, x: float, y: float, z: float) -> None:
    half_w = 0.158
    half_h = 0.158
    append_panel_rect(static, CONTROL_MATTE_BLACK_MATERIAL, x=x + 0.002, center_y=y, center_z=z, width_y=0.322, height_z=0.322)
    for line in (
        (y - half_w, z - half_h, y + half_w, z - half_h),
        (y - half_w, z + half_h, y + half_w, z + half_h),
        (y - half_w, z - half_h, y - half_w, z + half_h),
        (y + half_w, z - half_h, y + half_w, z + half_h),
    ):
        append_panel_line(
            static,
            "gtvr_glass_cyan",
            x=x,
            start_y=line[0],
            start_z=line[1],
            end_y=line[2],
            end_z=line[3],
            thickness=0.003,
        )

    append_panel_line(static, "gtvr_glass_cyan", x=x, start_y=y, start_z=z - 0.145, end_y=y, end_z=z + 0.145, thickness=0.0016)

    for tape_y in (y - 0.098, y + 0.098):
        append_panel_rect(static, "gtvr_cockpit_black", x=x + 0.001, center_y=tape_y, center_z=z, width_y=0.090, height_z=0.255)
        append_panel_line(static, "gtvr_glass_cyan", x=x, start_y=tape_y - 0.045, start_z=z - 0.128, end_y=tape_y - 0.045, end_z=z + 0.128, thickness=0.002)
        append_panel_line(static, "gtvr_glass_cyan", x=x, start_y=tape_y + 0.045, start_z=z - 0.128, end_y=tape_y + 0.045, end_z=z + 0.128, thickness=0.002)
        append_panel_line(static, "gtvr_glass_cyan", x=x, start_y=tape_y - 0.045, start_z=z - 0.128, end_y=tape_y + 0.045, end_z=z - 0.128, thickness=0.002)
        append_panel_line(static, "gtvr_glass_cyan", x=x, start_y=tape_y - 0.045, start_z=z + 0.128, end_y=tape_y + 0.045, end_z=z + 0.128, thickness=0.002)

    append_panel_line(static, "gtvr_glass_green", x=x, start_y=y - 0.143, start_z=z, end_y=y - 0.080, end_z=z, thickness=0.004)
    append_panel_line(static, "gtvr_glass_green", x=x, start_y=y + 0.080, start_z=z, end_y=y + 0.143, end_z=z, thickness=0.004)
    append_panel_triangle(
        static,
        "gtvr_glass_green",
        x=x,
        points_yz=[(y - 0.028, z - 0.012), (y - 0.010, z), (y - 0.028, z + 0.012)],
    )
    append_panel_triangle(
        static,
        "gtvr_glass_green",
        x=x,
        points_yz=[(y + 0.028, z - 0.012), (y + 0.010, z), (y + 0.028, z + 0.012)],
    )


def add_pfd_horizon_layer(horizon: dict[str, core.Patch], *, x: float, y: float, z: float) -> None:
    append_panel_rect(horizon, "gtvr_glass_sky", x=x, center_y=y, center_z=z + 0.052, width_y=0.150, height_z=0.108)
    append_panel_rect(horizon, "gtvr_glass_ground", x=x, center_y=y, center_z=z - 0.052, width_y=0.150, height_z=0.108)
    append_panel_line(horizon, "gtvr_glass_white", x=x, start_y=y - 0.074, start_z=z, end_y=y + 0.074, end_z=z, thickness=0.003)
    for offset, width in ((-0.070, 0.040), (-0.035, 0.064), (0.035, 0.064), (0.070, 0.040)):
        append_panel_line(
            horizon,
            "gtvr_glass_white",
            x=x,
            start_y=y - width * 0.5,
            start_z=z + offset,
            end_y=y + width * 0.5,
            end_z=z + offset,
            thickness=0.002,
        )


def add_pfd_tape_layer(
    tape: dict[str, core.Patch],
    *,
    x: float,
    y: float,
    z: float,
    side: str,
) -> None:
    for index in range(-7, 8):
        tick_z = z + index * 0.024
        tick_width = 0.058 if index % 2 == 0 else 0.036
        material = "gtvr_glass_green" if index == 0 else "gtvr_glass_white"
        if side == "left":
            start_y = y - tick_width * 0.5
            end_y = y + tick_width * 0.5
        else:
            start_y = y + tick_width * 0.5
            end_y = y - tick_width * 0.5
        append_panel_line(tape, material, x=x, start_y=start_y, start_z=tick_z, end_y=end_y, end_z=tick_z, thickness=0.0022)
    append_panel_triangle(
        tape,
        "gtvr_glass_green",
        x=x,
        points_yz=[(y - 0.018, z - 0.010), (y + 0.018, z), (y - 0.018, z + 0.010)]
        if side == "left"
        else [(y + 0.018, z - 0.010), (y - 0.018, z), (y + 0.018, z + 0.010)],
    )


def add_pfd_heading_layer(heading: dict[str, core.Patch], *, x: float, y: float, z: float) -> None:
    append_panel_ring(heading, "gtvr_glass_cyan", x=x, center_y=y, center_z=z, radius=0.030, thickness=0.0015, segments=20)
    for angle in (0.0, math.pi * 0.5, math.pi, math.pi * 1.5):
        inner = 0.020
        outer = 0.034
        append_panel_line(
            heading,
            "gtvr_glass_white",
            x=x,
            start_y=y + math.cos(angle) * inner,
            start_z=z + math.sin(angle) * inner,
            end_y=y + math.cos(angle) * outer,
            end_z=z + math.sin(angle) * outer,
            thickness=0.0018,
        )
    append_panel_triangle(
        heading,
        "gtvr_glass_yellow",
        x=x,
        points_yz=[(y - 0.006, z + 0.020), (y, z + 0.034), (y + 0.006, z + 0.020)],
    )


def add_live_pfd_display(*, screen_x: float, side_y: float, side_name: str) -> None:
    x = screen_x - 0.018
    z = -0.12
    static = live_display_geometry(f"GTVR{side_name}PFDStatic")
    speed_tape = live_display_geometry(f"GTVR{side_name}PFDSpeedTape")
    alt_tape = live_display_geometry(f"GTVR{side_name}PFDAltTape")

    _current_live_display_pivots[f"{side_name}PFD"] = (x, side_y, z)

    add_pfd_static_overlay(static, x=x, y=side_y, z=z)
    add_pfd_tape_layer(speed_tape, x=x - 0.004, y=side_y - 0.098, z=z, side="left")
    add_pfd_tape_layer(alt_tape, x=x - 0.004, y=side_y + 0.098, z=z, side="right")


def add_live_map_display(*, screen_x: float) -> None:
    x = screen_x - 0.018
    y = 0.0
    z = -0.12
    static = live_display_geometry("GTVRMapStatic")
    moving = live_display_geometry("GTVRMapMoving")

    _current_live_display_pivots["Map"] = (x, y, z)

    append_panel_rect(static, "gtvr_glass_green", x=x, center_y=y, center_z=z, width_y=0.010, height_z=0.036)
    append_panel_triangle(
        static,
        "gtvr_glass_cyan",
        x=x - 0.002,
        points_yz=[(y - 0.014, z - 0.010), (y, z + 0.024), (y + 0.014, z - 0.010)],
    )
    append_panel_line(static, "gtvr_glass_yellow", x=x, start_y=y - 0.052, start_z=z - 0.112, end_y=y, end_z=z, thickness=0.003)
    append_panel_line(static, "gtvr_glass_yellow", x=x, start_y=y, start_z=z, end_y=y + 0.074, end_z=z + 0.086, thickness=0.003)

    append_panel_ring(moving, "gtvr_glass_green", x=x - 0.004, center_y=y, center_z=z, radius=0.118, thickness=0.002, segments=32)
    append_panel_ring(moving, "gtvr_glass_cyan", x=x - 0.004, center_y=y, center_z=z, radius=0.062, thickness=0.0015, segments=24)
    for grid in (-0.080, -0.040, 0.040, 0.080):
        append_panel_line(moving, "gtvr_glass_green", x=x - 0.004, start_y=y + grid, start_z=z - 0.112, end_y=y + grid, end_z=z + 0.112, thickness=0.001)
        append_panel_line(moving, "gtvr_glass_green", x=x - 0.004, start_y=y - 0.120, start_z=z + grid, end_y=y + 0.120, end_z=z + grid, thickness=0.001)
    for angle in range(0, 360, 30):
        radians = math.radians(angle)
        inner = 0.102 if angle % 90 else 0.092
        outer = 0.122
        append_panel_line(
            moving,
            "gtvr_glass_white" if angle % 90 == 0 else "gtvr_glass_green",
            x=x - 0.004,
            start_y=y + math.cos(radians) * inner,
            start_z=z + math.sin(radians) * inner,
            end_y=y + math.cos(radians) * outer,
            end_z=z + math.sin(radians) * outer,
            thickness=0.002,
        )


def add_live_glass_displays(*, screen_x: float) -> None:
    add_live_pfd_display(screen_x=screen_x, side_y=-0.39, side_name="Left")
    add_live_pfd_display(screen_x=screen_x, side_y=0.39, side_name="Right")
    add_live_map_display(screen_x=screen_x)


def add_stock_display_surfaces(*, screen_x: float) -> None:
    display_x = screen_x - 0.020
    append_textured_panel(
        stock_display_geometry("DisplayNDL"),
        COCKPIT_MAP_MATERIAL,
        center=(display_x, 0.0, -0.12),
        width_y=0.30,
        height_z=0.34,
    )


def add_static_display_fallback(body: dict[str, core.Patch]) -> None:
    """Keep fixed screen cues visible without duplicating the moving live layers."""
    for geometry_name in live_display_static_geometry_names():
        display_geometry = _current_live_display_geometries[geometry_name]
        fallback = core.copy_patch_map(display_geometry)
        core.translate_patch_map(fallback, DISPLAY_FALLBACK_X_OFFSET, 0.0, 0.0)
        merge_patch_map_into(body, fallback)


def add_upholstered_seat(body: dict[str, core.Patch], base_x: float, seat_y: float) -> None:
    z = lambda value: value + SEAT_Z_LIFT
    append_box(body, "gtvr_cockpit_black", (base_x + 0.01, seat_y, z(-0.742)), (0.54, 0.34, 0.045))
    append_pillowed_seat_cushion(
        body,
        "gtvr_cockpit_seat",
        center=(base_x, seat_y, z(-0.655)),
        size=(0.56, 0.39, 0.120),
    )
    append_pillowed_seat_cushion(
        body,
        "gtvr_cockpit_seat_highlight",
        center=(base_x + 0.045, seat_y, z(-0.605)),
        size=(0.38, 0.235, 0.036),
        segments_x=8,
        segments_y=6,
    )
    append_cylinder_between(
        body,
        "gtvr_cockpit_seat_highlight",
        (base_x + 0.275, seat_y - 0.155, z(-0.610)),
        (base_x + 0.275, seat_y + 0.155, z(-0.610)),
        0.050,
        segments=28,
    )
    for side in (-1.0, 1.0):
        bolster_y = seat_y + side * 0.205
        append_cylinder_between(
            body,
            "gtvr_cockpit_seat_shadow",
            (base_x - 0.225, bolster_y, z(-0.615)),
            (base_x + 0.225, bolster_y, z(-0.615)),
            0.038,
            segments=28,
        )
    for seam_y in (seat_y - 0.105, seat_y, seat_y + 0.105):
        append_cylinder_between(
            body,
            "gtvr_cockpit_seat_shadow",
            (base_x - 0.190, seam_y, z(-0.575)),
            (base_x + 0.185, seam_y, z(-0.575)),
            0.004,
            segments=10,
        )

    back_x = base_x - 0.305
    append_box(body, "gtvr_cockpit_seat_shadow", (back_x - 0.075, seat_y, z(-0.355)), (0.032, 0.345, 0.505))
    append_pillowed_back_cushion(
        body,
        "gtvr_cockpit_seat",
        center=(back_x, seat_y, z(-0.355)),
        size=(0.125, 0.380, 0.565),
    )
    append_pillowed_back_cushion(
        body,
        "gtvr_cockpit_seat_highlight",
        center=(back_x + 0.050, seat_y, z(-0.350)),
        size=(0.042, 0.250, 0.380),
        segments_y=7,
        segments_z=9,
    )
    for side in (-1.0, 1.0):
        bolster_y = seat_y + side * 0.205
        append_cylinder_between(
            body,
            "gtvr_cockpit_seat_shadow",
            (back_x + 0.040, bolster_y, z(-0.600)),
            (back_x + 0.040, bolster_y, z(-0.145)),
            0.037,
            segments=24,
        )
    for seam_y in (seat_y - 0.110, seat_y + 0.110):
        append_cylinder_between(
            body,
            "gtvr_cockpit_seat_shadow",
            (back_x + 0.066, seam_y, z(-0.560)),
            (back_x + 0.066, seam_y, z(-0.165)),
            0.004,
            segments=10,
        )
    append_pillowed_back_cushion(
        body,
        "gtvr_cockpit_seat",
        center=(back_x - 0.015, seat_y, z(-0.020)),
        size=(0.145, 0.295, 0.155),
        segments_y=8,
        segments_z=6,
    )
    append_cylinder_between(
        body,
        "gtvr_cockpit_seat_shadow",
        (back_x - 0.040, seat_y - 0.120, z(-0.080)),
        (back_x - 0.040, seat_y + 0.120, z(-0.080)),
        0.020,
        segments=20,
    )


def add_cyclic_controls(body: dict[str, core.Patch], interior_x) -> None:
    for stick_y, geometry_name in ((-0.30, "GTVRLeftCyclicStick"), (0.30, "GTVRRightCyclicStick")):
        control = animated_control_geometry(geometry_name)
        boot_x = interior_x(2.08)
        boot_z = -0.755
        grip_x = interior_x(1.90)
        grip_z = -0.235
        append_cylinder_between(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            (boot_x - 0.055, stick_y - 0.065, boot_z),
            (boot_x + 0.055, stick_y + 0.065, boot_z),
            0.034,
            segments=28,
        )
        append_cylinder_between(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            (boot_x, stick_y, boot_z + 0.020),
            (grip_x, stick_y, grip_z),
            0.024,
            segments=32,
        )
        append_cylinder_between(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            (grip_x, stick_y, grip_z),
            (grip_x + 0.020, stick_y, grip_z + 0.145),
            0.045,
            segments=32,
        )
        append_cylinder_between(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            (grip_x + 0.012, stick_y - 0.050, grip_z + 0.104),
            (grip_x + 0.045, stick_y + 0.050, grip_z + 0.118),
            0.032,
            segments=32,
        )
        append_cylinder_between(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            (grip_x + 0.018, stick_y, grip_z + 0.148),
            (grip_x + 0.026, stick_y, grip_z + 0.162),
            0.038,
            segments=28,
        )


def add_collective_controls(body: dict[str, core.Patch], interior_x) -> None:
    for lever_y, geometry_name in (
        (-0.16, "LeftCollectiveLever"),
        (0.64, "RightCollectiveLever"),
    ):
        control = animated_control_geometry(geometry_name)
        base = (interior_x(1.34), lever_y, -0.565)
        elbow = (interior_x(1.70), lever_y, -0.440)
        grip_end = (interior_x(1.90), lever_y, -0.400)
        append_cylinder_between(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            (base[0] - 0.050, lever_y - 0.044, base[2] - 0.010),
            (base[0] + 0.050, lever_y + 0.044, base[2] - 0.010),
            0.028,
            segments=28,
        )
        append_cylinder_between(control, CONTROL_MATTE_BLACK_MATERIAL, base, elbow, 0.022, segments=32)
        append_cylinder_between(control, CONTROL_MATTE_BLACK_MATERIAL, elbow, grip_end, 0.038, segments=32)
        append_cylinder_between(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            (grip_end[0] - 0.035, lever_y - 0.035, grip_end[2] + 0.010),
            (grip_end[0] + 0.035, lever_y + 0.035, grip_end[2] + 0.010),
            0.022,
            segments=28,
        )


def add_pedal_set(body: dict[str, core.Patch], interior_x) -> None:
    pz = lambda value: value + PEDAL_Z_LIFT
    for seat_y, left_name, right_name in (
        (-0.40, "LLPedal", "LRPedal"),
        (0.40, "RLPedal", "RRPedal"),
    ):
        crossbar_x = interior_x(2.22) - PEDAL_X_REARWARD
        pad_x = interior_x(2.56) - PEDAL_X_REARWARD
        append_cylinder_between(
            body,
            CONTROL_MATTE_BLACK_MATERIAL,
            (crossbar_x, seat_y - 0.16, pz(-0.710)),
            (crossbar_x, seat_y + 0.16, pz(-0.710)),
            0.014,
            segments=28,
        )
        for pedal_offset, geometry_name in ((-0.12, left_name), (0.12, right_name)):
            pedal_y = seat_y + pedal_offset
            pedal = animated_control_geometry(geometry_name)
            append_cylinder_between(
                pedal,
                CONTROL_MATTE_BLACK_MATERIAL,
                (crossbar_x, pedal_y, pz(-0.710)),
                (pad_x - 0.025, pedal_y, pz(-0.510)),
                0.015,
                segments=28,
            )
            append_cylinder_between(
                pedal,
                CONTROL_MATTE_BLACK_MATERIAL,
                (pad_x, pedal_y - 0.060, pz(-0.500)),
                (pad_x, pedal_y + 0.060, pz(-0.500)),
                0.032,
                segments=28,
            )
            append_cylinder_between(
                pedal,
                CONTROL_MATTE_BLACK_MATERIAL,
                (pad_x + 0.035, pedal_y - 0.055, pz(-0.455)),
                (pad_x + 0.035, pedal_y + 0.055, pz(-0.455)),
                0.025,
                segments=28,
            )


def add_cockpit_kit(args: argparse.Namespace, materials: dict[int, Material], body: dict[str, core.Patch]) -> None:
    global _current_animated_control_geometries, _current_live_display_geometries, _current_live_display_pivots
    global _current_stock_display_geometries
    global _current_cockpit_x_delta
    global _current_dash_forward_x_delta, _current_interior_forward_x_delta
    _current_animated_control_geometries = {}
    _current_live_display_geometries = {}
    _current_live_display_pivots = {}
    _current_stock_display_geometries = {}
    _current_cockpit_x_delta = args.cockpit_x_delta
    _current_interior_forward_x_delta = args.interior_forward_x_delta
    _current_dash_forward_x_delta = args.dash_forward_x_delta
    if not args.cockpit_kit:
        return
    ensure_cockpit_materials(materials)
    ensure_inner_shell_material(materials)
    x_delta = args.cockpit_x_delta
    x = lambda value: value + x_delta
    interior_x = lambda value: x(value + args.interior_forward_x_delta)
    dash_x = lambda value: x(value + args.dash_forward_x_delta)

    add_dashboard_frame(body, dash_x)

    for seat_y in (-0.40, 0.40):
        add_upholstered_seat(body, interior_x(1.68), seat_y)

    screen_x = dash_x(2.47)
    for side_y in (-0.39, 0.39):
        add_framed_screen(
            body,
            material_name=CONTROL_MATTE_BLACK_MATERIAL,
            center=(screen_x, side_y, -0.12),
            width_y=0.34,
            height_z=0.34,
        )
        append_box(body, CONTROL_MATTE_BLACK_MATERIAL, (dash_x(2.43), side_y - 0.215, -0.12), (0.035, 0.026, 0.39))
        append_box(body, CONTROL_MATTE_BLACK_MATERIAL, (dash_x(2.43), side_y + 0.215, -0.12), (0.035, 0.026, 0.39))

    add_framed_screen(
        body,
        material_name=COCKPIT_MAP_MATERIAL,
        center=(screen_x, 0.0, -0.12),
        width_y=0.30,
        height_z=0.34,
    )
    add_stock_display_surfaces(screen_x=screen_x)
    add_live_glass_displays(screen_x=screen_x)
    add_static_display_fallback(body)

    add_cyclic_controls(body, interior_x)
    add_collective_controls(body, interior_x)
    add_pedal_set(body, interior_x)

    print(
        "Dev cockpit kit: added raised upholstered seats, animated floor-mounted pure-black cyclics, left-side collectives, "
        "lowered rearward rounded pedals and live left/right speed-altitude overlays with a center map."
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


def current_interior_x(value: float) -> float:
    return value + _current_cockpit_x_delta + _current_interior_forward_x_delta


def fmt_vector(values: tuple[float, float, float]) -> str:
    return " ".join(f"{value:.6g}" for value in values)


def patch_map_has_faces(patches: dict[str, core.Patch]) -> bool:
    return any(patch.indices for patch in patches.values())


def control_graphic_groups() -> list[tuple[str, list[str], str]]:
    candidates = [
        ("GTVRLeftCyclicGraphics", ["GTVRLeftCyclicStick"], "GTVRLeftCyclicTransform.Output"),
        ("GTVRRightCyclicGraphics", ["GTVRRightCyclicStick"], "GTVRRightCyclicTransform.Output"),
        ("GTVRLeftCollectiveGraphics", ["LeftCollectiveLever"], "GTVRLeftCollectiveTransform.Output"),
        ("GTVRRightCollectiveGraphics", ["RightCollectiveLever"], "GTVRRightCollectiveTransform.Output"),
        ("GTVRLLPedalGraphics", ["LLPedal"], "GTVRLLPedalTransform.Output"),
        ("GTVRLRPedalGraphics", ["LRPedal"], "GTVRLRPedalTransform.Output"),
        ("GTVRRLPedalGraphics", ["RLPedal"], "GTVRRLPedalTransform.Output"),
        ("GTVRRRPedalGraphics", ["RRPedal"], "GTVRRRPedalTransform.Output"),
    ]
    groups: list[tuple[str, list[str], str]] = []
    for graphic_name, geometry_names, transform_name in candidates:
        if any(
            geometry_name in _current_animated_control_geometries
            and patch_map_has_faces(_current_animated_control_geometries[geometry_name])
            for geometry_name in geometry_names
        ):
            groups.append((graphic_name, geometry_names, transform_name))
    return groups


def visual_control_dynamic_objects() -> str:
    if not control_graphic_groups():
        return ""

    left_cyclic_pivot = (current_interior_x(2.08), -0.30, -0.755)
    right_cyclic_pivot = (current_interior_x(2.08), 0.30, -0.755)
    left_collective_pivot = (current_interior_x(1.34), -0.16, -0.565)
    right_collective_pivot = (current_interior_x(1.34), 0.64, -0.565)

    return f"""
            // GTVR generated cockpit visual controls
            <[graphics_input][GTVRVisualCyclicPitchTravel][]
                <[uint32][InputID][StickCyclicPitch.Output]>
                <[float64][Scaling][0.16]>
            >
            <[graphics_input][GTVRVisualCyclicRollTravel][]
                <[uint32][InputID][StickCyclicRoll.Output]>
                <[float64][Scaling][0.16]>
            >
            <[graphics_rotation][GTVRLeftCyclicPitchTransform][]
                <[string8][Input][GTVRVisualCyclicPitchTravel.Output]>
                <[tmvector3d][Axis][ 0.0 1.0 0.0 ]>
                <[tmvector3d][Pivot][ {fmt_vector(left_cyclic_pivot)} ]>
            >
            <[graphics_rotation][GTVRLeftCyclicTransform][]
                <[string8][Input][GTVRVisualCyclicRollTravel.Output]>
                <[tmvector3d][Axis][ 1.0 0.0 0.0 ]>
                <[tmvector3d][Pivot][ {fmt_vector(left_cyclic_pivot)} ]>
                <[string8][InputTransform][GTVRLeftCyclicPitchTransform.Output]>
            >
            <[graphics_rotation][GTVRRightCyclicPitchTransform][]
                <[string8][Input][GTVRVisualCyclicPitchTravel.Output]>
                <[tmvector3d][Axis][ 0.0 1.0 0.0 ]>
                <[tmvector3d][Pivot][ {fmt_vector(right_cyclic_pivot)} ]>
            >
            <[graphics_rotation][GTVRRightCyclicTransform][]
                <[string8][Input][GTVRVisualCyclicRollTravel.Output]>
                <[tmvector3d][Axis][ 1.0 0.0 0.0 ]>
                <[tmvector3d][Pivot][ {fmt_vector(right_cyclic_pivot)} ]>
                <[string8][InputTransform][GTVRRightCyclicPitchTransform.Output]>
            >
            <[graphics_input][GTVRVisualCollectiveTravel][]
                <[uint32][InputID][CollectivePitchLever.Output]>
                <[float64][Scaling][0.2]>
            >
            <[graphics_rotation][GTVRLeftCollectiveTransform][]
                <[string8][Input][GTVRVisualCollectiveTravel.Output]>
                <[tmvector3d][Axis][ 0.0 -1.0 0.0 ]>
                <[tmvector3d][Pivot][ {fmt_vector(left_collective_pivot)} ]>
            >
            <[graphics_rotation][GTVRRightCollectiveTransform][]
                <[string8][Input][GTVRVisualCollectiveTravel.Output]>
                <[tmvector3d][Axis][ 0.0 -1.0 0.0 ]>
                <[tmvector3d][Pivot][ {fmt_vector(right_collective_pivot)} ]>
            >
            <[graphics_input][GTVRVisualRudderPedalTravel][]
                <[uint32][InputID][ServoRudder.Output]>
                <[float64][Scaling][-0.07]>
            >
            <[graphics_translation][GTVRLLPedalTransform][]
                <[string8][Input][GTVRVisualRudderPedalTravel.Output]>
                <[tmvector3d][Axis][ 1.0 0.0 0.0 ]>
            >
            <[graphics_translation][GTVRLRPedalTransform][]
                <[string8][Input][GTVRVisualRudderPedalTravel.Output]>
                <[tmvector3d][Axis][ -1.0 0.0 0.0 ]>
            >
            <[graphics_translation][GTVRRLPedalTransform][]
                <[string8][Input][GTVRVisualRudderPedalTravel.Output]>
                <[tmvector3d][Axis][ 1.0 0.0 0.0 ]>
            >
            <[graphics_translation][GTVRRRPedalTransform][]
                <[string8][Input][GTVRVisualRudderPedalTravel.Output]>
                <[tmvector3d][Axis][ -1.0 0.0 0.0 ]>
            >"""


def visual_control_graphics_objects() -> str:
    lines: list[str] = []
    for graphic_name, geometry_names, transform_name in control_graphic_groups():
        lines.extend(
            [
                f"            <[rigidbodygraphics][{graphic_name}][]",
                "                <[uint32][PositionID][Fuselage.R]>",
                "                <[uint32][OrientationID][Fuselage.Q]>",
                f"                <[string8][GeometryList][ {' '.join(geometry_names)} ]>",
                f"                <[string8][InputTransform][{transform_name}]>",
                "            >",
            ]
        )
    return "\n".join(lines)


def live_display_static_geometry_names() -> list[str]:
    names = [
        "GTVRLeftPFDStatic",
        "GTVRRightPFDStatic",
        "GTVRMapStatic",
    ]
    return [name for name in names if name in _current_live_display_geometries and patch_map_has_faces(_current_live_display_geometries[name])]


def live_display_graphics_objects() -> str:
    if not _current_live_display_geometries:
        return ""

    map_pivot = _current_live_display_pivots.get("Map", (current_interior_x(2.47), 0.0, -0.12))
    static_names = live_display_static_geometry_names()
    static_block = ""
    if static_names:
        static_block = "\n".join(
            [
                "            <[rigidbodygraphics][GTVRGlassStaticGraphics][]",
                "                <[uint32][PositionID][Fuselage.R]>",
                "                <[uint32][OrientationID][Fuselage.Q]>",
                f"                <[string8][GeometryList][ {' '.join(static_names)} ]>",
                "            >",
            ]
        )

    pfd_blocks: list[str] = []
    for side_name in ("Left", "Right"):
        pfd_blocks.extend(
            [
                f"            <[rigidbodygraphics][GTVR{side_name}PFDSpeedTapeGraphics][]",
                f"                <[string8][GeometryList][ GTVR{side_name}PFDSpeedTape ]>",
                "                <[uint32][PositionID][Fuselage.R]>",
                "                <[uint32][OrientationID][Fuselage.Q]>",
                "                <[string8][InputTransform][GTVRGlassAirspeedTapeTransform.Output]>",
                "            >",
                f"            <[rigidbodygraphics][GTVR{side_name}PFDAltTapeGraphics][]",
                f"                <[string8][GeometryList][ GTVR{side_name}PFDAltTape ]>",
                "                <[uint32][PositionID][Fuselage.R]>",
                "                <[uint32][OrientationID][Fuselage.Q]>",
                "                <[string8][InputTransform][GTVRGlassAltTapeTransform.Output]>",
                "            >",
            ]
        )

    return "\n".join(
        [
            "            // GTVR live side displays: moving speed and altitude tapes only.",
            "            <[graphics_input][GTVRGlassAirspeedInput][]",
            "                <[uint32][InputID][GTVRAirspeedTapeValue.Output]>",
            "            >",
            "            <[graphics_linear_interpolation][GTVRGlassAirspeedTapeMapping][]",
            "                <[string8][Input][GTVRGlassAirspeedInput.Output]>",
            "                <[tmvector2d][Map][(0.0 0.115) (25.0 0.035) (50.0 -0.035) (80.0 -0.115)]>",
            "            >",
            "            <[graphics_translation][GTVRGlassAirspeedTapeTransform][]",
            "                <[string8][Input][GTVRGlassAirspeedTapeMapping.Output]>",
            "                <[tmvector3d][Axis][0.0 0.0 1.0]>",
            "            >",
            "            <[graphics_input][GTVRGlassAltInput][]",
            "                <[uint32][InputID][GTVRAltitudeTapeValue.Output]>",
            "            >",
            "            <[graphics_linear_interpolation][GTVRGlassAltTapeMapping][]",
            "                <[string8][Input][GTVRGlassAltInput.Output]>",
            "                <[tmvector2d][Map][(0.0 0.115) (500.0 0.035) (1000.0 -0.035) (1500.0 -0.115)]>",
            "            >",
            "            <[graphics_translation][GTVRGlassAltTapeTransform][]",
            "                <[string8][Input][GTVRGlassAltTapeMapping.Output]>",
            "                <[tmvector3d][Axis][0.0 0.0 1.0]>",
            "            >",
            static_block,
            *pfd_blocks,
            "            <[hingedbodygraphics][GTVRMapMovingGraphics][]",
            "                <[string8][GeometryList][ GTVRMapMoving ]>",
            "                <[uint32][PositionID][Fuselage.R]>",
            "                <[uint32][OrientationID][Fuselage.Q]>",
            "                <[uint32][InputID][HeadingAngle.Output]>",
            "                <[float64][Scaling][-0.017453]>",
            "                <[tmvector3d][Axis][ 1.0 0.0 0.0 ]>",
            f"                <[tmvector3d][Pivot][ {fmt_vector(map_pivot)} ]>",
            "            >",
        ]
    )


def live_telemetry_dynamic_objects() -> str:
    if not _current_live_display_geometries:
        return ""

    return """
            // GTVR dev-owned telemetry sensors for the side speed/altitude overlays.
            <[sender_body][GTVRLiveSenderBody][]
                <[string8][Body][Fuselage]>
            >
            <[pitot_tube][GTVRLivePitotTube][]
                <[string8][Body][Fuselage]>
            >
            <[airspeed_indicator][GTVRLiveAirspeedIndicator][]
                <[string8][StaticPressure][GTVRLivePitotTube.StaticPressure]>
                <[string8][TotalPressure][GTVRLivePitotTube.TotalPressure]>
            >
            <[output][GTVRAirspeedTapeValue][]
                <[string8][Input][GTVRLiveAirspeedIndicator.IndicatedAirspeed]>
            >
            <[sender][GTVRAirspeedTelemetrySender][]
                <[string8][Input][GTVRLiveAirspeedIndicator.IndicatedAirspeed]>
                <[string8][Message][Aircraft.IndicatedAirspeed]>
            >
            <[input_default][GTVRPressureSettingInput][]
                <[string8][Message][PressureSetting]>
                <[uint][Positions][201]>
                <[tmvector2d][Range][ 95000.0 105000.0]>
                <[float64][Value][101325.0]>
            >
            <[altimeter][GTVRLiveAltimeter][]
                <[string8][StaticPressure][GTVRLivePitotTube.StaticPressure]>
                <[string8][AltimeterSetting][GTVRPressureSettingInput.Output]>
            >
            <[output][GTVRAltitudeTapeValue][]
                <[string8][Input][GTVRLiveAltimeter.PressureAltitude]>
            >
            <[sender][GTVRAltitudeTelemetrySender][]
                <[string8][Input][GTVRLiveAltimeter.PressureAltitude]>
                <[string8][Message][Aircraft.Altitude]>
            >"""


def is_dev_static_visual_hidden(geometry_name: str) -> bool:
    return HIDDEN_DEV_STATIC_VISUAL_RE.search(geometry_name) is not None


def write_dev_visual_tmd(path: Path, geometry_names: list[str]) -> None:
    animated_names = set(_current_animated_control_geometries) | set(_current_live_display_geometries)
    static_geometry_names = [
        name for name in sorted(geometry_names)
        if name not in animated_names and not is_dev_static_visual_hidden(name)
    ]
    telemetry_objects = live_telemetry_dynamic_objects()
    display_graphics = live_display_graphics_objects()
    control_transforms = visual_control_dynamic_objects()
    graphic_objects = visual_control_graphics_objects()
    text = f"""<[file][][]
    <[modelmanager][][]
        <[pointer_list_tmuniverse][DynamicObjects][]
            <[rigidbody][Fuselage][]
                <[float64][Mass][5000.0]>
                <[tmvector3d][InertiaLength][4.5 1.5 1.5]>
                <[tmvector3d][R0][0.0 0.0 0.0]>
                <[tmmatrix3d][B0][1.0 0.0 0.0  0.0 1.0 0.0  0.0 0.0 1.0]>
            >
{telemetry_objects}
        >
        <[pointer_list_tmgraphics][GraphicObjects][]
            <[rigidbodygraphics][Fuselage][]
                <[uint32][PositionID][Fuselage.R]>
                <[uint32][OrientationID][Fuselage.Q]>
                <[string8][GeometryList][ {' '.join(static_geometry_names)} ]>
            >
{display_graphics}
{control_transforms}
{graphic_objects}
        >
    >
>
"""
    path.write_text(text, encoding="utf-8")


def patch_dev_tgi_material_shaders(path: Path) -> int:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    current_material: str | None = None
    patched = 0
    for index, line in enumerate(lines):
        if "<[tmxglmaterial_impexp][element]" in line:
            current_material = None
            continue
        if current_material is None:
            material_match = re.search(r"<\[string8\]\[name\]\[([^\]]+)\]>", line)
            if material_match:
                current_material = material_match.group(1)
            continue
        if current_material in DEV_INTERIOR_SHADER_MATERIALS and "<[string8][shader_hint]" in line:
            lines[index] = "                <[string8][shader_hint][standard interior]>"
            patched += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return patched


def prepare_source_for_dev(args: argparse.Namespace) -> None:
    if core.SOURCE_DIR.exists():
        shutil.rmtree(core.SOURCE_DIR)
    core.SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    core.ensure_runtime_resources(core.SOURCE_ROOT)

    materials, body, tail_rotor, visual_gear, source_faces, imported_faces = core.build_body(args)
    core.add_flat_materials(materials, core.SOURCE_DIR)
    main_rotor, fallback_tail_rotor = core.legacy_rotor_patch_maps()
    core.translate_patch_map(main_rotor, 0.0, 0.0, args.visual_body_lift)
    core.translate_patch_map(fallback_tail_rotor, 0.0, 0.0, args.visual_body_lift)
    visual_tail_rotor = tail_rotor or fallback_tail_rotor

    animated_names = set(_current_animated_control_geometries) | set(_current_live_display_geometries)
    geometries: dict[str, dict[str, core.Patch]] = {}
    for geometry_name in core.read_geometry_names():
        if geometry_name == "Fuselage":
            geometries[geometry_name] = core.copy_patch_map(body)
        elif geometry_name in _current_stock_display_geometries:
            geometries[geometry_name] = core.copy_patch_map(_current_stock_display_geometries[geometry_name])
        elif geometry_name in animated_names:
            source_geometry = _current_animated_control_geometries.get(
                geometry_name,
                _current_live_display_geometries.get(geometry_name, {}),
            )
            geometries[geometry_name] = core.copy_patch_map(source_geometry)
        elif geometry_name == "SkidsMiddle":
            geometries[geometry_name] = core.copy_patch_map(visual_gear)
        elif geometry_name in {"RotorBlade0", "RotorBlade1", "RotorBlade2", "RotorBlade3"}:
            geometries[geometry_name] = core.clone_patch_map(main_rotor)
        elif geometry_name == "TailBlade0":
            geometries[geometry_name] = core.copy_patch_map(visual_tail_rotor)
        elif geometry_name.startswith("TailBlade") or geometry_name in {"TailRotorHub", "TailRotorCont"}:
            geometries[geometry_name] = {}
        else:
            geometries[geometry_name] = {}

    for geometry_name, patches in _current_animated_control_geometries.items():
        geometries.setdefault(geometry_name, core.copy_patch_map(patches))
    for geometry_name, patches in _current_live_display_geometries.items():
        geometries.setdefault(geometry_name, core.copy_patch_map(patches))
    for geometry_name, patches in _current_stock_display_geometries.items():
        geometries.setdefault(geometry_name, core.copy_patch_map(patches))

    core.write_aircraft_source_tmc(core.SOURCE_DIR / f"{core.AIRCRAFT_NAME}.tmc")
    write_dev_visual_tmd(core.SOURCE_DIR / f"{core.AIRCRAFT_NAME}.tmd", sorted(geometries))
    tgi_path = core.SOURCE_DIR / f"{core.AIRCRAFT_NAME}.tgi"
    core.write_tgi(tgi_path, materials, geometries)
    patched_materials = patch_dev_tgi_material_shaders(tgi_path)
    core.write_model_tmc(core.SOURCE_DIR / "model.tmc", materials, geometries, args.max_texture_size)
    core.write_root_converter_config(core.SOURCE_ROOT / "config.tmc", core.SOURCE_ROOT, core.BUILD_USER)
    (core.SOURCE_DIR / "_GTVR_WRAITH_DEV_SOURCE.md").write_text(
        "\n".join(
            [
                "# GTVR Wraith Dev Source",
                "",
                "This source compiles the dev Wraith exterior with generated cockpit visuals.",
                f"- Geometry names emitted: `{len(geometries)}`",
                f"- Animated control geometry groups: `{len(control_graphic_groups())}`",
                f"- Live glass display geometry groups: `{len(_current_live_display_geometries)}`",
                f"- Stock EC135 display geometry groups: `{len(_current_stock_display_geometries)}`",
                f"- MSFS source faces: `{source_faces}`",
                f"- Imported faces: `{imported_faces}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote dev Wraith source: {core.SOURCE_DIR}")
    print(f"Geometry names emitted: {len(geometries)}")
    print(f"Animated control geometry groups: {len(control_graphic_groups())}")
    print(f"Live glass display geometry groups: {len(_current_live_display_geometries)}")
    print(f"Stock EC135 display geometry groups: {len(_current_stock_display_geometries)}")
    if patched_materials:
        print(f"Dev cockpit materials: forced {patched_materials} generated interior/control shaders.")
    print(f"Imported body faces: {imported_faces}")


def write_source_stamp() -> None:
    DEV_SOURCE_STAMP.write_text(
        "\n".join(
            [
                "GTVR Wraith Dev source prepared.",
                f"aircraft={DEV_AIRCRAFT_NAME}",
                f"display={DEV_DISPLAY_NAME}",
                f"inner_shell=solid materials are duplicated inward into {INNER_SHELL_MATERIAL_NAME}",
                "cockpit_kit=generated raised upholstered seats, no lower shelf/dash braces, animated floor-mounted pure-black cyclics, left-side collectives, lowered rearward pedals and left/right speed-altitude tape panels with a center map",
                "animated_controls=cyclic, collective and pedal meshes are emitted as dev-only graphics; cyclics use isolated pitch/roll transforms and collectives use collective-only transforms; inherited EC135 visible control geometry and handle clickspots are suppressed in the dev package",
                "live_glass=side displays use dev-owned pitot/airspeed/altimeter telemetry outputs for moving airspeed and altitude tape geometry; center map heading remains separate",
                "stock_display_surfaces=DisplayNDL is populated for the preserved center map texture; side PFD stock textures are intentionally suppressed",
                "glass_fallback=fixed display cues are merged into the visible dash mesh without duplicating moving live layers",
                f"cockpit_x_delta={_current_cockpit_x_delta:.3f}",
                f"interior_forward_x_delta={_current_interior_forward_x_delta:.3f}",
                f"dash_forward_x_delta={_current_dash_forward_x_delta:.3f}",
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
                "Generated cockpit kit includes raised textured upholstered seats, no lower shelf/pedestal slab or dash brace tubes, animated floor-mounted pure-black cyclics, left-side collective placement, lowered rearward rounded pedals, side speed-altitude tape panels and a center map.",
                "Generated cyclic, collective and pedal meshes are separated into animated visual geometry groups in the dev model TMD; cyclics use cyclic pitch/roll only and collectives use collective travel only.",
                "Inherited EC135 visible cockpit stick/collective/pedal visuals are removed from the dev model TMD static render list, and their click handles are reduced in controls.tmd so the dev-generated controls are the visible ones.",
                "Generated side display overlays bind moving airspeed and altitude tape graphics to dev-owned pitot/airspeed/altimeter telemetry outputs; the center map remains heading-driven.",
                "Only DisplayNDL is populated as a stock display surface; DisplayPFDL and DisplayPFDR are suppressed so the side displays are live geometry instead of static PFD textures.",
                "Recessed fixed display cues are merged into the visible dash mesh as an EC135-TMQ-safe fallback without duplicating moving live layers.",
                f"Dev pilot uses {DEV_PILOT}, the known-good EC135 pilot object.",
                f"Visual shell is shifted X {DEFAULT_PILOT_ALIGNMENT_X_DELTA:.2f}m for pilot/window alignment.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_dev_controls_tmd(path: Path) -> int:
    if not path.exists():
        return 0

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    patched: list[str] = []
    hidden_depth = 0
    hidden_objects = 0

    for line in lines:
        stripped = line.strip()
        opening = re.match(r"<\[(control_(?:box|cylinder))\]\[([^\]]+)\]\[\]", stripped)
        if hidden_depth == 0 and opening and HIDDEN_DEV_CLICKSPOT_RE.search(opening.group(2)):
            hidden_depth = 1
            hidden_objects += 1
        elif hidden_depth > 0 and re.match(r"<\[[^\]]+\]\[[^\]]+\]\[\]", stripped):
            hidden_depth += 1

        if hidden_depth > 0:
            indent = line[: len(line) - len(line.lstrip())]
            if "<[float64][Radius]" in stripped:
                line = f"{indent}<[float64][Radius][0.0001]>"
            elif "<[float64][Length]" in stripped:
                line = f"{indent}<[float64][Length][0.0001]>"
            elif "<[tmvector3d][Dimensions]" in stripped:
                line = f"{indent}<[tmvector3d][Dimensions][ 0.0001 0.0001 0.0001 ]>"

        patched.append(line)

        if hidden_depth > 0 and stripped == ">":
            hidden_depth -= 1

    if hidden_objects:
        path.write_text("\n".join(patched) + "\n", encoding="utf-8")
    return hidden_objects


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
        help="Dev-only X tuning offset for the whole generated cockpit kit.",
    )
    parser.add_argument(
        "--interior-forward-x-delta",
        type=float,
        default=DEFAULT_INTERIOR_FORWARD_X_DELTA,
        help="Dev-only extra forward X offset for seats, cyclic, collectives, pedals and floor. Does not move the dash or pilot.",
    )
    parser.add_argument(
        "--dash-forward-x-delta",
        type=float,
        default=DEFAULT_DASH_FORWARD_X_DELTA,
        help="Dev-only extra forward X offset for the dashboard and display group. Does not move seats, controls or pilot.",
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
            hidden_clickspots = patch_dev_controls_tmd(DEV_PACKAGE_DIR / "controls.tmd")
            if hidden_clickspots:
                print(f"Dev controls: hid {hidden_clickspots} inherited EC135 cockpit click/handle visuals.")
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
