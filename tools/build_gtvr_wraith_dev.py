from __future__ import annotations

import argparse
import math
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

import build_msfs_shell_source as msfs_shell
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

WRAITH_LIVERY_ASSET_DIR = ROOT / "assets" / "wraith_livery"
WRAITH_LIVERY_PATTERN = WRAITH_LIVERY_ASSET_DIR / "wraith_stealth_camo_v1.png"
WRAITH_LIVERY_SIZE = (1024, 1024)
WRAITH_LIVERY_MATERIALS = {
    "body_1": ("msfs_78_body_1", "gtvr_wraith_livery_body_1", "camo"),
    "body_2": ("msfs_33_body_2", "gtvr_wraith_livery_body_2", "camo"),
}

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
COCKPIT_FLOOR_APERTURE_CENTER_X = 3.22
COCKPIT_FLOOR_APERTURE_SEGMENTS = 64
COCKPIT_FLOOR_APERTURE_TAPER = 0.35
COCKPIT_FLOOR_APERTURE_THROAT_HALF_LENGTH = 0.26
COCKPIT_FLOOR_APERTURE_THROAT_HALF_WIDTH = 0.57
COCKPIT_FLOOR_APERTURE_CLEARANCE_HALF_LENGTH = 0.275
COCKPIT_FLOOR_APERTURE_CLEARANCE_HALF_WIDTH = 0.585
COCKPIT_FLOOR_APERTURE_OUTER_HALF_LENGTH = 0.325
COCKPIT_FLOOR_APERTURE_OUTER_HALF_WIDTH = 0.645
COCKPIT_FLOOR_APERTURE_MIN_CLIPPED_Z = -0.93
COCKPIT_FLOOR_APERTURE_MAX_CLIPPED_Z = -0.67
COCKPIT_FLOOR_APERTURE_SURFACE_MIN_Z = -1.00
COCKPIT_FLOOR_APERTURE_SURFACE_MAX_Z = -0.45
COCKPIT_FLOOR_APERTURE_MATERIALS = (
    "body_1",
    "body_2",
    "body_parts",
    "mesh",
    "whiteplastic",
)
COCKPIT_FLOOR_APERTURE_EXPECTED_CLIP_STATS = {
    "body_1": (142, 74, 812),
    "body_2": (142, 74, 812),
    "body_parts": (371, 230, 1350),
    "mesh": (152, 98, 490),
    "whiteplastic": (232, 180, 358),
}
COCKPIT_FLOOR_APERTURE_TOP_OVERLAP = 0.006
COCKPIT_FLOOR_APERTURE_CHAMFER_DROP = 0.020
COCKPIT_FLOOR_APERTURE_WALL_DEPTH = 0.030
COCKPIT_FLOOR_APERTURE_BOTTOM_OVERLAP = 0.006
DEV_PREVIEW_FILENAMES = ("preview.ttx", "preview_small.ttx")
PREVIEW_RENDER_DIR_NAME = "gtvr_wraith_preview"
PREVIEW_RENDER_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_preview_source" / "aircraft"
PREVIEW_RENDER_SOURCE_DIR = PREVIEW_RENDER_SOURCE_ROOT / PREVIEW_RENDER_DIR_NAME
PREVIEW_RENDER_BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_preview_build_user"
PREVIEW_RENDER_LAUNCH_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_preview_launch"
PREVIEW_RENDER_SOURCE_STAMP = PREVIEW_RENDER_SOURCE_DIR / "_GTVR_WRAITH_PREVIEW_SOURCE_STAMP.txt"
CONTROL_MATTE_BLACK_MATERIAL = "gtvr_control_black"
PEDAL_BLACK_MATERIAL = CONTROL_MATTE_BLACK_MATERIAL
CYCLIC_OPAQUE_MATERIAL = "gtvr_cyclic_opaque_dark_grey"
CONTROL_SPECULAR_TEXTURE = "gtvr_control_black_specular"
CONTROL_REFLECTION_TEXTURE = "gtvr_control_black_reflection"
MATTE_BLACK_SURFACE_TEXTURE = "gtvr_matte_black_surface"
TIRE_BLACK_MATERIAL = "gtvr_tire_black"
TIRE_BLACK_COLOR = (1, 1, 1)
REAR_STRUT_LENGTH_SCALE = 0.65
REAR_WHEEL_STRUT_SHAVE_BASE_X_RANGE = (-3.70, -3.20)
REAR_WHEEL_STRUT_SHAVE_HALF_WIDTH_Y = 0.09
REAR_WHEEL_STRUT_SHAVE_SHELL_CLEARANCE = 0.0005
REAR_WHEEL_STRUT_SHAVE_EXPECTED_SOURCE_FACES = 26993
REAR_WHEEL_STRUT_SHAVE_EXPECTED_MODIFIED_FACES = 426
REAR_WHEEL_STRUT_SHAVE_EXPECTED_REMOVED_FACES = 350
REAR_WHEEL_STRUT_SHAVE_EXPECTED_GENERATED_FACES = 420
REAR_WHEEL_STRUT_SHAVE_EXPECTED_RESULT_FACES = 26987
REAR_WHEEL_STRUT_SHAVE_SHELL_INDEX_CELL_SIZE = 0.25
FRONT_GEAR_BRACE_SOURCE_MATERIAL = "static_parts"
FRONT_GEAR_BRACE_MATERIAL = "gtvr_front_gear_brace_match"
FRONT_GEAR_BRACE_COLOR = (152, 106, 86)
FRONT_GEAR_BRACE_BASE_START = (0.57104015, 1.1479198, -0.95190045)
FRONT_GEAR_BRACE_BASE_END = (0.72173435, 1.0435283, -0.77173025)
FRONT_GEAR_BRACE_RADIUS = 0.058
FRONT_GEAR_BRACE_SEGMENTS = 12
FRONT_GEAR_BRACE_EXPECTED_ADDED_FACES = 96
TAIL_ROTOR_BLUR_MATERIAL = "gtvr_tail_rotor_blur"
TAIL_ROTOR_AXIS = (0.0, 1.0, 0.0)
TAIL_ROTOR_BASE_PIVOT = (-11.18395, 0.35312, 2.27417)
TAIL_ROTOR_X_FROM_TAIL_END = 0.80
TAIL_ROTOR_SIDE_CLEARANCE = 0.08
TAIL_ROTOR_PLANE_ROLL = math.radians(25.7)
TAIL_ROTOR_BLADE_PHASE = math.radians(10.0)
TAIL_ROTOR_PROCEDURAL_RADIUS = 1.05
TAIL_ROTOR_PROCEDURAL_ROOT_RADIUS = 0.16
TAIL_ROTOR_PROCEDURAL_ROOT_WIDTH = 0.20
TAIL_ROTOR_PROCEDURAL_MID_WIDTH = 0.13
TAIL_ROTOR_PROCEDURAL_TIP_WIDTH = 0.075
TAIL_ROTOR_PROCEDURAL_TIP_MARKER = 0.18
TAIL_ROTOR_PROCEDURAL_ROOT_THICKNESS = 0.060
TAIL_ROTOR_PROCEDURAL_MID_THICKNESS = 0.040
TAIL_ROTOR_PROCEDURAL_TIP_THICKNESS = 0.026
TAIL_ROTOR_BLUR_INNER_RADIUS = 0.28
TAIL_ROTOR_BLUR_OUTER_RADIUS = 0.98
TAIL_ROTOR_BLUR_STREAKS = 12
TAIL_ROTOR_BLUR_SWEEP = math.radians(8.0)
GTVR_MAIN_ROTOR_SPIN_GEOMETRY = "GTVRMainRotorSpin"
GTVR_TAIL_ROTOR_SPIN_GEOMETRY = "GTVRTailRotorSpin"
GTVR_MAIN_ROTOR_LOCKED_PIVOT = (-0.556228, -0.0000018, 2.53272)
GTVR_TAIL_ROTOR_LOCKED_PIVOT = (-10.8051, 0.418839, 2.27417)
GTVR_TAIL_ROTOR_LOCKED_AXIS = (0.0, 0.901077, 0.433659)
MAIN_ROTOR_VISUAL_SPIN_RATE = 41.36
TAIL_ROTOR_VISUAL_SPIN_RATE = 220.0
ROTOR_ANIMATION_PROBE_ONLY = False
ROTOR_ANIMATION_MAIN_PROBE_RATE = 1.5
ROTOR_ANIMATION_TAIL_PROBE_RATE = 2.5
ROTOR_ANIMATION_PROBE_MATERIAL = "gtvr_rotor_probe_red"
ROTOR_ANIMATION_PROBE_COLOR = (255, 8, 8)
MAIN_ROTOR_MAST_MATERIAL = CONTROL_MATTE_BLACK_MATERIAL
MAIN_ROTOR_MAST_HOLE_X_RANGE = (0.0, 0.9)
MAIN_ROTOR_MAST_HOLE_Y_RANGE = (-0.16, 0.16)
MAIN_ROTOR_MAST_HOLE_Z_RANGE = (1.30, 1.75)
MAIN_ROTOR_MAST_SOCKET_MATERIALS = ("black_venting",)
MAIN_ROTOR_MAST_SOCKET_X_RANGE = (-0.90, -0.10)
MAIN_ROTOR_MAST_SOCKET_Y_RANGE = (-0.65, 0.65)
MAIN_ROTOR_MAST_SOCKET_Z_RANGE = (1.20, 1.50)
MAIN_ROTOR_SOURCE_MAST_BASE_Z = 1.62
MAIN_ROTOR_SOURCE_MAST_TOP_Z = 2.42
MAIN_ROTOR_SOURCE_CENTER_Z = 2.55
MAIN_ROTOR_BASE_TO_CENTER_Z = MAIN_ROTOR_SOURCE_CENTER_Z - MAIN_ROTOR_SOURCE_MAST_BASE_Z
MAIN_ROTOR_CENTER_TO_MAST_TOP_Z = MAIN_ROTOR_SOURCE_CENTER_Z - MAIN_ROTOR_SOURCE_MAST_TOP_Z
MAIN_ROTOR_MAST_RADIUS = 0.095
MAIN_ROTOR_MAST_COLLAR_RADIUS = 0.155
MAIN_ROTOR_MAST_COLLAR_HALF_HEIGHT = 0.035
MAIN_ROTOR_PROCEDURAL_BLADE_COUNT = 4
MAIN_ROTOR_PROCEDURAL_RADIUS = 4.90
MAIN_ROTOR_PROCEDURAL_ROOT_RADIUS = 0.24
MAIN_ROTOR_PROCEDURAL_MID_RADIUS = 2.45
MAIN_ROTOR_PROCEDURAL_ROOT_WIDTH = 0.34
MAIN_ROTOR_PROCEDURAL_MID_WIDTH = 0.22
MAIN_ROTOR_PROCEDURAL_TIP_WIDTH = 0.12
MAIN_ROTOR_PROCEDURAL_TIP_SWEEP = -0.10
MAIN_ROTOR_PROCEDURAL_BLADE_THICKNESS = 0.035
MAIN_ROTOR_PROCEDURAL_PLANE_Z_OFFSET = MAIN_ROTOR_CENTER_TO_MAST_TOP_Z
MAIN_ROTOR_PROCEDURAL_HUB_RADIUS = 0.18
MAIN_ROTOR_PROCEDURAL_HUB_HEIGHT = MAIN_ROTOR_CENTER_TO_MAST_TOP_Z * 2.0
MAIN_ROTOR_BLUR_STREAKS = 16
MAIN_ROTOR_BLUR_INNER_RADIUS = 0.55
MAIN_ROTOR_BLUR_OUTER_RADIUS = 4.70
MAIN_ROTOR_BLUR_SWEEP = math.radians(5.0)
LEATHER_SPECULAR_TEXTURE = "gtvr_leather_specular"
LEATHER_REFLECTION_TEXTURE = "gtvr_leather_reflection"
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
TIRE_NODE_RE = re.compile(r"^(?:Tire_new\.(?:001|002)|REAR_WHEEL_STILL)$", re.IGNORECASE)
REAR_STRUT_NODE_RE = re.compile(r"^Rear_gear$", re.IGNORECASE)
PROTRUDING_MAIN_GEAR_SUPPORT_NODE_RE = re.compile(
    r"^(?:Strut\.(?:001|002)|Assy\.(?:002|003))$",
    re.IGNORECASE,
)
UNWANTED_GREEN_MATERIAL_RE = re.compile(r"^(?:bool|bool_002|slime_lgt)$", re.IGNORECASE)

COCKPIT_FLAT_MATERIALS = {
    "gtvr_cockpit_black": ((4, 4, 4), "generated-gtvr-dev-cockpit-black"),
    "gtvr_control_black": ((18, 19, 20), "generated-gtvr-dev-control-dark-grey"),
    CYCLIC_OPAQUE_MATERIAL: ((18, 19, 20), "generated-gtvr-dev-cyclic-opaque-dark-grey"),
    "gtvr_cockpit_dark_gray": ((22, 24, 25), "generated-gtvr-dev-cockpit-dark-gray"),
    "gtvr_cockpit_seat": ((30, 18, 12), "generated-gtvr-dev-cockpit-seat"),
    "gtvr_cockpit_seat_highlight": ((46, 28, 19), "generated-gtvr-dev-cockpit-seat-highlight"),
    "gtvr_cockpit_seat_shadow": ((14, 8, 5), "generated-gtvr-dev-cockpit-seat-shadow"),
    "gtvr_cockpit_metal": ((88, 92, 92), "generated-gtvr-dev-cockpit-metal"),
    "gtvr_cockpit_rubber": ((7, 7, 7), "generated-gtvr-dev-cockpit-rubber"),
    "gtvr_cockpit_button_green": ((10, 150, 78), "generated-gtvr-dev-cockpit-button-green"),
    "gtvr_cockpit_button_red": ((190, 28, 24), "generated-gtvr-dev-cockpit-button-red"),
    TAIL_ROTOR_BLUR_MATERIAL: ((64, 68, 70), "generated-gtvr-dev-tail-rotor-motion-blur"),
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
DEV_MATERIAL_SURFACE_MAPS = {
    CONTROL_MATTE_BLACK_MATERIAL: (
        ("specular", CONTROL_SPECULAR_TEXTURE),
        ("reflection", CONTROL_REFLECTION_TEXTURE),
    ),
    CYCLIC_OPAQUE_MATERIAL: (
        ("specular", MATTE_BLACK_SURFACE_TEXTURE),
        ("reflection", MATTE_BLACK_SURFACE_TEXTURE),
    ),
    "gtvr_cockpit_black": (
        ("specular", MATTE_BLACK_SURFACE_TEXTURE),
        ("reflection", MATTE_BLACK_SURFACE_TEXTURE),
    ),
    INNER_SHELL_MATERIAL_NAME: (
        ("specular", MATTE_BLACK_SURFACE_TEXTURE),
        ("reflection", MATTE_BLACK_SURFACE_TEXTURE),
    ),
    TIRE_BLACK_MATERIAL: (
        ("specular", MATTE_BLACK_SURFACE_TEXTURE),
        ("reflection", MATTE_BLACK_SURFACE_TEXTURE),
    ),
    "gtvr_cockpit_seat": (
        ("specular", LEATHER_SPECULAR_TEXTURE),
        ("reflection", LEATHER_REFLECTION_TEXTURE),
    ),
    "gtvr_cockpit_seat_highlight": (
        ("specular", LEATHER_SPECULAR_TEXTURE),
        ("reflection", LEATHER_REFLECTION_TEXTURE),
    ),
    "gtvr_cockpit_seat_shadow": (
        ("specular", LEATHER_SPECULAR_TEXTURE),
        ("reflection", LEATHER_REFLECTION_TEXTURE),
    ),
}
DEV_AUXILIARY_TEXTURE_NAMES = tuple(
    sorted({texture_name for slots in DEV_MATERIAL_SURFACE_MAPS.values() for _, texture_name in slots})
)
COCKPIT_PFD_MATERIAL = "gtvr_cockpit_flight"
COCKPIT_PFD_TEXTURE = "gtvr_cockpit_flight"
COCKPIT_PFD_SOURCE_TEXTURE = "gtvr_cockpit_flight_source"
CENTER_MAP_MATERIAL = "gtvr_center_map"
CENTER_MAP_TEXTURE = "gtvr_center_map_light"
STOCK_DISPLAY_MATERIAL = "display_light"
STOCK_DISPLAY_TEXTURE = "display_light"
STOCK_DISPLAY_STATE_INPUTS = (
    "PilotPFDSelectedOn",
    "CopilotPFDSelectedOn",
    "PilotPFDModeSetOn",
    "CopilotPFDModeSetOn",
    "PilotNDSelectedOn",
    "CopilotNDSelectedOn",
)
EC135_ND_MAP_STATE_INPUTS = (
    # EC135 ships only the ND on/off state entries as text.  The compiled TMQ still owns
    # the actual ND mode logic, so seed the most likely EC135 mode toggles by name.
    ("input_binary", "PilotNDModeSetOn", 1.0),
    ("input_binary", "CopilotNDModeSetOn", 1.0),
    ("input_binary", "ICPPilotNDMode", 1.0),
    ("input_binary", "ICPCopilotNDMode", 1.0),
)
# Crop the shared runtime display atlas instead of showing the entire source atlas on each Wraith screen.
# The EC135 runtime renders its glass cockpit into a shared display atlas. The Wraith side screens
# should use only the top PFD atlas windows: live speed, altitude, attitude and the heading tape.
# Fit left/right independently: crop off the duplicate strip on the centre-facing edge of each
# side screen, then shift the PFD source window down slightly so speed/altitude sit at the top edge
# and any leftover compass/ND clutter overflows at the bottom instead of stealing side space.
LEFT_PFD_DISPLAY_UV_RECT = (0.35, 0.045, 0.71, 0.385)
RIGHT_PFD_DISPLAY_UV_RECT = (0.0, 0.045, 0.355, 0.385)
SIDE_PFD_DISPLAY_WIDTH_Y = 0.305
SIDE_PFD_DISPLAY_HEIGHT_Z = 0.315
MAP_PANEL_DIR_NAME = "gtvr_map_panel"
MAP_PANEL_DISPLAY_SIZE = 1024
MAP_PANEL_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_map_panel_source" / "aircraft"
MAP_PANEL_SOURCE_DIR = MAP_PANEL_SOURCE_ROOT / MAP_PANEL_DIR_NAME
MAP_PANEL_BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_map_panel_build_user"
MAP_PANEL_LAUNCH_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_map_panel_launch"
MAP_PANEL_SOURCE_STAMP = MAP_PANEL_SOURCE_DIR / "_GTVR_WRAITH_MAP_PANEL_SOURCE_STAMP.txt"
MAP_PANEL_TEXTURE = "gtvr_map_panel_light"
MAP_PANEL_MATERIAL = "gtvr_map_panel_light"
ROTOR_ANIMATION_DIR_NAME = "gtvr_rotor_animation"
ROTOR_ANIMATION_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_rotor_animation_source" / "aircraft"
ROTOR_ANIMATION_SOURCE_DIR = ROTOR_ANIMATION_SOURCE_ROOT / ROTOR_ANIMATION_DIR_NAME
ROTOR_ANIMATION_BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_rotor_animation_build_user"
ROTOR_ANIMATION_LAUNCH_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_rotor_animation_launch"
ROTOR_ANIMATION_SOURCE_STAMP = ROTOR_ANIMATION_SOURCE_DIR / "_GTVR_WRAITH_ROTOR_ANIMATION_SOURCE_STAMP.txt"

_ORIGINAL_PATCH_TMC = core.patch_tmc
_ORIGINAL_BUILD_BODY = core.build_body
_ORIGINAL_BUILD_SELECTED_NODES = core.build_selected_nodes
_ORIGINAL_LEGACY_ROTOR_PATCH_MAPS = core.legacy_rotor_patch_maps
_ORIGINAL_MSFS_READ_ACCESSOR = msfs_shell.read_accessor
_current_pilot_alignment_x_delta = 0.0
_current_cockpit_x_delta = DEFAULT_COCKPIT_X_DELTA
_current_interior_forward_x_delta = DEFAULT_INTERIOR_FORWARD_X_DELTA
_current_dash_forward_x_delta = DEFAULT_DASH_FORWARD_X_DELTA
_current_animated_control_geometries: dict[str, dict[str, core.Patch]] = {}
_current_live_display_geometries: dict[str, dict[str, core.Patch]] = {}
_current_live_display_pivots: dict[str, tuple[float, float, float]] = {}
_current_stock_display_geometries: dict[str, dict[str, core.Patch]] = {}
_current_center_map_pivot: tuple[float, float, float] | None = None
_current_tail_rotor_pivot: tuple[float, float, float] = TAIL_ROTOR_BASE_PIVOT
_current_main_rotor_pivot: tuple[float, float, float] | None = None
_current_main_rotor_spin_geometry: dict[str, core.Patch] = {}
_current_tail_rotor_spin_geometry: dict[str, core.Patch] = {}


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
    core.build_selected_nodes = build_selected_nodes_for_dev
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
        MAP_PANEL_SOURCE_ROOT,
        MAP_PANEL_SOURCE_DIR,
        MAP_PANEL_BUILD_USER,
        MAP_PANEL_LAUNCH_USER,
        ROTOR_ANIMATION_SOURCE_ROOT,
        ROTOR_ANIMATION_SOURCE_DIR,
        ROTOR_ANIMATION_BUILD_USER,
        ROTOR_ANIMATION_LAUNCH_USER,
        PREVIEW_RENDER_SOURCE_ROOT,
        PREVIEW_RENDER_SOURCE_DIR,
        PREVIEW_RENDER_BUILD_USER,
        PREVIEW_RENDER_LAUNCH_USER,
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


def converted_map_panel_tmb() -> Path:
    return MAP_PANEL_BUILD_USER / "aircraft" / MAP_PANEL_DIR_NAME / f"{MAP_PANEL_DIR_NAME}.tmb"


def converted_rotor_animation_tmb() -> Path:
    return (
        ROTOR_ANIMATION_BUILD_USER
        / "aircraft"
        / ROTOR_ANIMATION_DIR_NAME
        / f"{ROTOR_ANIMATION_DIR_NAME}.tmb"
    )


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


MeshVertex = tuple[float, float, float, float, float, float, float, float]
VertexPolygon = list[MeshVertex]
Point2D = tuple[float, float]


def tapered_floor_aperture_points(
    half_length: float,
    half_width: float,
) -> list[Point2D]:
    points: list[Point2D] = []
    for index in range(COCKPIT_FLOOR_APERTURE_SEGMENTS):
        angle = index / COCKPIT_FLOOR_APERTURE_SEGMENTS * math.tau
        x = COCKPIT_FLOOR_APERTURE_CENTER_X + half_length * math.cos(angle)
        local_half_width = half_width - COCKPIT_FLOOR_APERTURE_TAPER * (
            x - COCKPIT_FLOOR_APERTURE_CENTER_X
        )
        points.append((x, local_half_width * math.sin(angle)))
    return points


def projected_polygon_signed_area(points: list[Point2D]) -> float:
    return 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )


def converted_preview_render_tmb() -> Path:
    return (
        PREVIEW_RENDER_BUILD_USER
        / "aircraft"
        / PREVIEW_RENDER_DIR_NAME
        / f"{PREVIEW_RENDER_DIR_NAME}.tmb"
    )


def projected_vertex_polygon_area(vertices: VertexPolygon) -> float:
    if len(vertices) < 3:
        return 0.0
    return abs(projected_polygon_signed_area([(vertex[0], vertex[1]) for vertex in vertices]))


def validate_convex_aperture(points: list[Point2D]) -> None:
    if len(points) < 3 or projected_polygon_signed_area(points) <= 0.0:
        raise RuntimeError("Cockpit floor aperture must be a counter-clockwise polygon.")
    cross_signs: list[float] = []
    for index in range(len(points)):
        point_a = points[index]
        point_b = points[(index + 1) % len(points)]
        point_c = points[(index + 2) % len(points)]
        cross_signs.append(
            (point_b[0] - point_a[0]) * (point_c[1] - point_b[1])
            - (point_b[1] - point_a[1]) * (point_c[0] - point_b[0])
        )
    if min(cross_signs) <= 1e-9:
        raise RuntimeError("Cockpit floor aperture profile is not strictly convex.")


def interpolate_mesh_vertex(start: MeshVertex, end: MeshVertex, amount: float) -> MeshVertex:
    values = [start[index] + (end[index] - start[index]) * amount for index in range(8)]
    normal_length = math.sqrt(sum(values[index] * values[index] for index in range(3, 6)))
    if normal_length > 1e-12:
        for index in range(3, 6):
            values[index] /= normal_length
    return tuple(values)  # type: ignore[return-value]


def clean_vertex_polygon(vertices: VertexPolygon) -> VertexPolygon:
    cleaned: VertexPolygon = []
    for vertex in vertices:
        if cleaned and sum((vertex[axis] - cleaned[-1][axis]) ** 2 for axis in range(3)) < 1e-18:
            continue
        cleaned.append(vertex)
    if len(cleaned) > 1 and sum(
        (cleaned[0][axis] - cleaned[-1][axis]) ** 2 for axis in range(3)
    ) < 1e-18:
        cleaned.pop()
    return cleaned


def clip_vertex_polygon_to_xy_half_plane(
    vertices: VertexPolygon,
    edge_start: Point2D,
    edge_end: Point2D,
    *,
    keep_inside: bool,
) -> VertexPolygon:
    if not vertices:
        return []

    def distance(vertex: MeshVertex) -> float:
        return (
            (edge_end[0] - edge_start[0]) * (vertex[1] - edge_start[1])
            - (edge_end[1] - edge_start[1]) * (vertex[0] - edge_start[0])
        )

    def kept(value: float) -> bool:
        return value >= -1e-10 if keep_inside else value <= 1e-10

    result: VertexPolygon = []
    previous = vertices[-1]
    previous_distance = distance(previous)
    previous_kept = kept(previous_distance)
    for current in vertices:
        current_distance = distance(current)
        current_kept = kept(current_distance)
        if current_kept != previous_kept:
            denominator = previous_distance - current_distance
            if abs(denominator) > 1e-15:
                result.append(
                    interpolate_mesh_vertex(previous, current, previous_distance / denominator)
                )
        if current_kept:
            result.append(current)
        previous = current
        previous_distance = current_distance
        previous_kept = current_kept
    return clean_vertex_polygon(result)


def subtract_convex_xy_aperture(
    face_vertices: VertexPolygon,
    aperture: list[Point2D],
) -> tuple[list[VertexPolygon], VertexPolygon]:
    inside_candidate = face_vertices
    outside_fragments: list[VertexPolygon] = []
    for edge_index, edge_start in enumerate(aperture):
        if len(inside_candidate) < 3:
            break
        edge_end = aperture[(edge_index + 1) % len(aperture)]
        outside = clip_vertex_polygon_to_xy_half_plane(
            inside_candidate,
            edge_start,
            edge_end,
            keep_inside=False,
        )
        if len(outside) >= 3 and projected_vertex_polygon_area(outside) > 1e-11:
            outside_fragments.append(outside)
        inside_candidate = clip_vertex_polygon_to_xy_half_plane(
            inside_candidate,
            edge_start,
            edge_end,
            keep_inside=True,
        )
    if len(inside_candidate) < 3 or projected_vertex_polygon_area(inside_candidate) <= 1e-11:
        inside_candidate = []
    return outside_fragments, inside_candidate


def append_vertex_polygon(
    patch: core.Patch,
    vertices: VertexPolygon,
    face_attribute: int,
) -> int:
    if len(vertices) < 3 or projected_vertex_polygon_area(vertices) <= 1e-11:
        return 0
    base_index = len(patch.vertices) // 8
    for vertex in vertices:
        patch.vertices.extend(vertex)
    generated_faces = 0
    for vertex_index in range(1, len(vertices) - 1):
        patch.indices.extend(
            [base_index, base_index + vertex_index, base_index + vertex_index + 1]
        )
        patch.face_attributes.append(face_attribute)
        generated_faces += 1
    return generated_faces


def clipped_polygon_is_floor_layer(vertices: VertexPolygon) -> bool:
    if not vertices:
        return False
    vertex_zs = [vertex[2] for vertex in vertices]
    return (
        max(vertex_zs) >= COCKPIT_FLOOR_APERTURE_MIN_CLIPPED_Z - 1e-6
        and min(vertex_zs) <= COCKPIT_FLOOR_APERTURE_MAX_CLIPPED_Z + 1e-6
    )


def face_may_intersect_floor_aperture(
    vertices: VertexPolygon,
    aperture_bounds: tuple[float, float, float, float],
) -> bool:
    min_x, max_x, min_y, max_y = aperture_bounds
    if max(vertex[0] for vertex in vertices) < min_x - 1e-9:
        return False
    if min(vertex[0] for vertex in vertices) > max_x + 1e-9:
        return False
    if max(vertex[1] for vertex in vertices) < min_y - 1e-9:
        return False
    if min(vertex[1] for vertex in vertices) > max_y + 1e-9:
        return False
    if max(vertex[2] for vertex in vertices) < COCKPIT_FLOOR_APERTURE_MIN_CLIPPED_Z - 1e-6:
        return False
    if min(vertex[2] for vertex in vertices) > COCKPIT_FLOOR_APERTURE_MAX_CLIPPED_Z + 1e-6:
        return False
    return True


def count_patch_floor_aperture_faces(
    patch: core.Patch,
    aperture: list[Point2D],
) -> int:
    matches = 0
    aperture_bounds = (
        min(point[0] for point in aperture),
        max(point[0] for point in aperture),
        min(point[1] for point in aperture),
        max(point[1] for point in aperture),
    )
    for face_offset in range(0, len(patch.indices), 3):
        face_indices = patch.indices[face_offset : face_offset + 3]
        if len(face_indices) != 3:
            continue
        face_vertices: VertexPolygon = [
            tuple(patch.vertices[index * 8 : index * 8 + 8])  # type: ignore[misc]
            for index in face_indices
        ]
        if not face_may_intersect_floor_aperture(face_vertices, aperture_bounds):
            continue
        _outside, inside = subtract_convex_xy_aperture(face_vertices, aperture)
        if inside and clipped_polygon_is_floor_layer(inside):
            matches += 1
    return matches


def copy_source_face(
    source_patch: core.Patch,
    target_patch: core.Patch,
    face_indices: list[int],
    face_attribute: int,
    vertex_map: dict[int, int],
) -> None:
    for source_index in face_indices:
        target_index = vertex_map.get(source_index)
        if target_index is None:
            target_index = len(target_patch.vertices) // 8
            vertex_map[source_index] = target_index
            source_offset = source_index * 8
            target_patch.vertices.extend(source_patch.vertices[source_offset : source_offset + 8])
        target_patch.indices.append(target_index)
    target_patch.face_attributes.append(face_attribute)


def clip_patch_to_floor_aperture(
    patch: core.Patch,
    aperture: list[Point2D],
) -> dict[str, int]:
    clipped = core.Patch(patch.material_name)
    vertex_map: dict[int, int] = {}
    modified_faces = 0
    fully_removed_faces = 0
    generated_faces = 0
    source_face_count = len(patch.indices) // 3
    aperture_bounds = (
        min(point[0] for point in aperture),
        max(point[0] for point in aperture),
        min(point[1] for point in aperture),
        max(point[1] for point in aperture),
    )

    for face_offset in range(0, len(patch.indices), 3):
        face_indices = patch.indices[face_offset : face_offset + 3]
        if len(face_indices) != 3:
            continue
        face_attribute = (
            patch.face_attributes[face_offset // 3] if patch.face_attributes else 0
        )
        face_vertices: VertexPolygon = [
            tuple(patch.vertices[index * 8 : index * 8 + 8])  # type: ignore[misc]
            for index in face_indices
        ]
        if not face_may_intersect_floor_aperture(face_vertices, aperture_bounds):
            copy_source_face(
                patch,
                clipped,
                face_indices,
                face_attribute,
                vertex_map,
            )
            continue
        outside_fragments, inside = subtract_convex_xy_aperture(face_vertices, aperture)
        if not inside or not clipped_polygon_is_floor_layer(inside):
            copy_source_face(
                patch,
                clipped,
                face_indices,
                face_attribute,
                vertex_map,
            )
            continue

        modified_faces += 1
        if not outside_fragments:
            fully_removed_faces += 1
        for fragment in outside_fragments:
            generated_faces += append_vertex_polygon(clipped, fragment, face_attribute)

    patch.vertices = clipped.vertices
    patch.indices = clipped.indices
    patch.face_attributes = clipped.face_attributes
    return {
        "source_faces": source_face_count,
        "modified_faces": modified_faces,
        "fully_removed_faces": fully_removed_faces,
        "generated_faces": generated_faces,
        "result_faces": len(patch.indices) // 3,
    }


def lower_shell_surface_triangles(patch: core.Patch) -> list[VertexPolygon]:
    triangles: list[VertexPolygon] = []
    for face_offset in range(0, len(patch.indices), 3):
        face_indices = patch.indices[face_offset : face_offset + 3]
        if len(face_indices) != 3:
            continue
        vertices: VertexPolygon = [
            tuple(patch.vertices[index * 8 : index * 8 + 8])  # type: ignore[misc]
            for index in face_indices
        ]
        if max(vertex[2] for vertex in vertices) < COCKPIT_FLOOR_APERTURE_SURFACE_MIN_Z:
            continue
        if min(vertex[2] for vertex in vertices) > COCKPIT_FLOOR_APERTURE_SURFACE_MAX_Z:
            continue
        if projected_vertex_polygon_area(vertices) <= 1e-11:
            continue
        triangles.append(vertices)
    return triangles


def sample_lower_shell_at_xy(
    triangles: list[VertexPolygon],
    point: Point2D,
) -> tuple[float, tuple[float, float, float]]:
    best: tuple[float, tuple[float, float, float]] | None = None
    px, py = point
    for vertices in triangles:
        ax, ay = vertices[0][0], vertices[0][1]
        bx, by = vertices[1][0], vertices[1][1]
        cx, cy = vertices[2][0], vertices[2][1]
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(denominator) <= 1e-12:
            continue
        weight_a = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
        weight_b = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
        weight_c = 1.0 - weight_a - weight_b
        if min(weight_a, weight_b, weight_c) < -1e-7:
            continue
        z = sum(
            weight * vertex[2]
            for weight, vertex in zip((weight_a, weight_b, weight_c), vertices)
        )
        if not (
            COCKPIT_FLOOR_APERTURE_SURFACE_MIN_Z
            <= z
            <= COCKPIT_FLOOR_APERTURE_SURFACE_MAX_Z
        ):
            continue
        normal = tuple(
            sum(
                weight * vertex[axis]
                for weight, vertex in zip((weight_a, weight_b, weight_c), vertices)
            )
            for axis in range(3, 6)
        )
        normal_length = math.sqrt(sum(component * component for component in normal))
        if normal_length <= 1e-12:
            normal = (0.0, 0.0, -1.0)
        else:
            normal = tuple(component / normal_length for component in normal)
        if best is None or z < best[0]:
            best = (z, normal)  # type: ignore[arg-type]
    if best is None:
        raise RuntimeError(
            f"Cannot project cockpit floor aperture frame onto lower shell at ({px:.6f}, {py:.6f})."
        )
    return best


def sample_floor_aperture_ring(
    primary_triangles: list[VertexPolygon],
    duplicate_triangles: list[VertexPolygon],
    points: list[Point2D],
) -> list[tuple[float, float, float]]:
    sampled: list[tuple[float, float, float]] = []
    for point in points:
        primary_z, _primary_normal = sample_lower_shell_at_xy(primary_triangles, point)
        duplicate_z, _duplicate_normal = sample_lower_shell_at_xy(duplicate_triangles, point)
        if abs(primary_z - duplicate_z) > 1e-4:
            raise RuntimeError(
                "Refusing mismatched paired lower-shell surfaces at cockpit floor aperture: "
                f"body_1 z={primary_z:.6f}, body_2 z={duplicate_z:.6f}."
            )
        sampled.append((point[0], point[1], primary_z))
    return sampled


def build_cockpit_floor_aperture_frame(
    skin_primary: core.Patch,
    skin_duplicate: core.Patch,
    throat_points: list[Point2D],
    clearance_points: list[Point2D],
    outer_points: list[Point2D],
) -> tuple[dict[str, core.Patch], tuple[float, float]]:
    primary_triangles = lower_shell_surface_triangles(skin_primary)
    duplicate_triangles = lower_shell_surface_triangles(skin_duplicate)
    throat_surface = sample_floor_aperture_ring(
        primary_triangles,
        duplicate_triangles,
        throat_points,
    )
    clearance_surface = sample_floor_aperture_ring(
        primary_triangles,
        duplicate_triangles,
        clearance_points,
    )
    outer_surface = sample_floor_aperture_ring(
        primary_triangles,
        duplicate_triangles,
        outer_points,
    )

    def shifted(
        ring: list[tuple[float, float, float]],
        z_offset: float,
    ) -> list[tuple[float, float, float]]:
        return [(x, y, z + z_offset) for x, y, z in ring]

    outer_top = shifted(outer_surface, COCKPIT_FLOOR_APERTURE_TOP_OVERLAP)
    clearance_top = shifted(clearance_surface, COCKPIT_FLOOR_APERTURE_TOP_OVERLAP)
    throat_top = shifted(
        throat_surface,
        -COCKPIT_FLOOR_APERTURE_CHAMFER_DROP,
    )
    throat_bottom = shifted(
        throat_surface,
        -COCKPIT_FLOOR_APERTURE_CHAMFER_DROP
        - COCKPIT_FLOOR_APERTURE_WALL_DEPTH,
    )
    clearance_bottom = shifted(
        clearance_surface,
        -COCKPIT_FLOOR_APERTURE_BOTTOM_OVERLAP,
    )
    outer_bottom = shifted(
        outer_surface,
        -COCKPIT_FLOOR_APERTURE_BOTTOM_OVERLAP,
    )

    frame: dict[str, core.Patch] = {}

    def add_strip(
        ring_a: list[tuple[float, float, float]],
        ring_b: list[tuple[float, float, float]],
    ) -> None:
        for index in range(len(ring_a)):
            next_index = (index + 1) % len(ring_a)
            append_double_sided_auto_quad(
                frame,
                INNER_SHELL_MATERIAL_NAME,
                [
                    ring_a[index],
                    ring_a[next_index],
                    ring_b[next_index],
                    ring_b[index],
                ],
            )

    add_strip(outer_top, clearance_top)
    add_strip(clearance_top, throat_top)
    add_strip(throat_top, throat_bottom)
    add_strip(throat_bottom, clearance_bottom)
    add_strip(clearance_bottom, outer_bottom)
    add_strip(outer_bottom, outer_top)
    all_surface_zs = [point[2] for ring in (throat_surface, clearance_surface, outer_surface) for point in ring]
    return frame, (min(all_surface_zs), max(all_surface_zs))


def carve_cockpit_floor_aperture(
    body: dict[str, core.Patch],
) -> tuple[dict[str, dict[str, int]], dict[str, core.Patch], list[Point2D]]:
    throat_points = tapered_floor_aperture_points(
        COCKPIT_FLOOR_APERTURE_THROAT_HALF_LENGTH,
        COCKPIT_FLOOR_APERTURE_THROAT_HALF_WIDTH,
    )
    clearance_points = tapered_floor_aperture_points(
        COCKPIT_FLOOR_APERTURE_CLEARANCE_HALF_LENGTH,
        COCKPIT_FLOOR_APERTURE_CLEARANCE_HALF_WIDTH,
    )
    outer_points = tapered_floor_aperture_points(
        COCKPIT_FLOOR_APERTURE_OUTER_HALF_LENGTH,
        COCKPIT_FLOOR_APERTURE_OUTER_HALF_WIDTH,
    )
    for points in (throat_points, clearance_points, outer_points):
        validate_convex_aperture(points)

    skin_primary = body.get("body_1")
    skin_duplicate = body.get("body_2")
    if skin_primary is None or skin_duplicate is None:
        raise RuntimeError(
            "Cannot find both paired cockpit floor skin layers for the aperture."
        )
    for material_name in COCKPIT_FLOOR_APERTURE_MATERIALS:
        if material_name not in body:
            raise RuntimeError(
                f"Cannot find cockpit floor layer {material_name!r} for the aperture."
            )

    unexpected_matches: dict[str, int] = {}
    for material_name, patch in body.items():
        if material_name in COCKPIT_FLOOR_APERTURE_MATERIALS:
            continue
        match_count = count_patch_floor_aperture_faces(patch, clearance_points)
        if match_count:
            unexpected_matches[material_name] = match_count
    if unexpected_matches:
        raise RuntimeError(
            "Refusing to cut through unrelated cockpit floor geometry: "
            f"matches={unexpected_matches}."
        )

    frame, frame_surface_z_range = build_cockpit_floor_aperture_frame(
        skin_primary,
        skin_duplicate,
        throat_points,
        clearance_points,
        outer_points,
    )
    clip_stats = {
        material_name: clip_patch_to_floor_aperture(body[material_name], clearance_points)
        for material_name in COCKPIT_FLOOR_APERTURE_MATERIALS
    }
    paired_clip_fields = ("modified_faces", "fully_removed_faces", "generated_faces")
    if any(
        clip_stats["body_1"][field] != clip_stats["body_2"][field]
        for field in paired_clip_fields
    ):
        raise RuntimeError(
            "Refusing mismatched paired cockpit floor skin clipping: "
            f"body_1={clip_stats['body_1']}, body_2={clip_stats['body_2']}."
        )
    if any(stats["modified_faces"] == 0 for stats in clip_stats.values()):
        raise RuntimeError(
            f"Refusing incomplete cockpit floor aperture clipping: {clip_stats}."
        )
    for material_name, expected in COCKPIT_FLOOR_APERTURE_EXPECTED_CLIP_STATS.items():
        stats = clip_stats[material_name]
        actual = (
            stats["modified_faces"],
            stats["fully_removed_faces"],
            stats["generated_faces"],
        )
        if actual != expected:
            raise RuntimeError(
                "Refusing unexpected cockpit floor aperture topology: "
                f"{material_name}={actual}, expected {expected}."
            )
    print(
        "Dev cockpit floor aperture frame: "
        f"sampled body-following surface z {frame_surface_z_range[0]:.3f}.."
        f"{frame_surface_z_range[1]:.3f}."
    )
    return clip_stats, frame, throat_points


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


def append_patch_geometry(target: core.Patch, source: core.Patch) -> None:
    vertex_offset = len(target.vertices) // 8
    target.vertices.extend(source.vertices)
    target.indices.extend(index + vertex_offset for index in source.indices)
    target.face_attributes.extend(source.face_attributes)


def shorten_patch_along_xz_axis(patch: core.Patch, scale: float) -> None:
    points = [patch.vertices[offset : offset + 3] for offset in range(0, len(patch.vertices), 8)]
    if not points:
        return
    mean_x = sum(point[0] for point in points) / len(points)
    mean_z = sum(point[2] for point in points) / len(points)
    covariance_xx = sum((point[0] - mean_x) ** 2 for point in points)
    covariance_zz = sum((point[2] - mean_z) ** 2 for point in points)
    covariance_xz = sum((point[0] - mean_x) * (point[2] - mean_z) for point in points)
    axis_angle = 0.5 * math.atan2(2.0 * covariance_xz, covariance_xx - covariance_zz)
    axis_x = math.cos(axis_angle)
    axis_z = math.sin(axis_angle)
    if axis_z < 0.0:
        axis_x = -axis_x
        axis_z = -axis_z
    projections = [
        (point[0] - mean_x) * axis_x + (point[2] - mean_z) * axis_z for point in points
    ]
    lower_projection = min(projections)
    for point_index, offset in enumerate(range(0, len(patch.vertices), 8)):
        longitudinal_distance = projections[point_index] - lower_projection
        shift = (scale - 1.0) * longitudinal_distance
        patch.vertices[offset] += axis_x * shift
        patch.vertices[offset + 2] += axis_z * shift


def clip_vertex_polygon_below_lower_shell(
    vertices: VertexPolygon,
    shell_index: tuple[float, dict[tuple[int, int], list[VertexPolygon]]],
) -> VertexPolygon:
    if not vertices:
        return []

    def shell_distance(vertex: MeshVertex) -> float:
        shell_z, _normal = sample_indexed_lower_shell_at_xy(
            shell_index,
            (vertex[0], vertex[1]),
        )
        return vertex[2] - (shell_z - REAR_WHEEL_STRUT_SHAVE_SHELL_CLEARANCE)

    clipped: VertexPolygon = []
    previous = vertices[-1]
    previous_distance = shell_distance(previous)
    previous_kept = previous_distance <= 1e-9
    for current in vertices:
        current_distance = shell_distance(current)
        current_kept = current_distance <= 1e-9
        if current_kept != previous_kept:
            denominator = previous_distance - current_distance
            if abs(denominator) > 1e-15:
                intersection = list(
                    interpolate_mesh_vertex(
                        previous,
                        current,
                        previous_distance / denominator,
                    )
                )
                shell_z, _normal = sample_indexed_lower_shell_at_xy(
                    shell_index,
                    (intersection[0], intersection[1]),
                )
                intersection[2] = shell_z - REAR_WHEEL_STRUT_SHAVE_SHELL_CLEARANCE
                clipped.append(tuple(intersection))  # type: ignore[arg-type]
        if current_kept:
            clipped.append(current)
        previous = current
        previous_distance = current_distance
        previous_kept = current_kept
    return clean_vertex_polygon(clipped)


def build_lower_shell_spatial_index(
    triangles: list[VertexPolygon],
) -> tuple[float, dict[tuple[int, int], list[VertexPolygon]]]:
    cell_size = REAR_WHEEL_STRUT_SHAVE_SHELL_INDEX_CELL_SIZE
    cells: dict[tuple[int, int], list[VertexPolygon]] = {}
    for triangle in triangles:
        min_cell_x = math.floor(min(vertex[0] for vertex in triangle) / cell_size)
        max_cell_x = math.floor(max(vertex[0] for vertex in triangle) / cell_size)
        min_cell_y = math.floor(min(vertex[1] for vertex in triangle) / cell_size)
        max_cell_y = math.floor(max(vertex[1] for vertex in triangle) / cell_size)
        for cell_x in range(min_cell_x, max_cell_x + 1):
            for cell_y in range(min_cell_y, max_cell_y + 1):
                cells.setdefault((cell_x, cell_y), []).append(triangle)
    return cell_size, cells


def sample_indexed_lower_shell_at_xy(
    shell_index: tuple[float, dict[tuple[int, int], list[VertexPolygon]]],
    point: Point2D,
) -> tuple[float, tuple[float, float, float]]:
    cell_size, cells = shell_index
    cell = (
        math.floor(point[0] / cell_size),
        math.floor(point[1] / cell_size),
    )
    candidates = cells.get(cell)
    if not candidates:
        raise RuntimeError(
            "Cannot find indexed lower-shell geometry at "
            f"({point[0]:.6f}, {point[1]:.6f})."
        )
    return sample_lower_shell_at_xy(candidates, point)


def vertex_polygon_area_3d(vertices: VertexPolygon) -> float:
    if len(vertices) < 3:
        return 0.0
    origin = vertices[0]
    area = 0.0
    for vertex_index in range(1, len(vertices) - 1):
        edge_a = tuple(
            vertices[vertex_index][axis] - origin[axis] for axis in range(3)
        )
        edge_b = tuple(
            vertices[vertex_index + 1][axis] - origin[axis] for axis in range(3)
        )
        cross = (
            edge_a[1] * edge_b[2] - edge_a[2] * edge_b[1],
            edge_a[2] * edge_b[0] - edge_a[0] * edge_b[2],
            edge_a[0] * edge_b[1] - edge_a[1] * edge_b[0],
        )
        area += 0.5 * math.sqrt(sum(component * component for component in cross))
    return area


def append_vertex_polygon_3d(
    patch: core.Patch,
    vertices: VertexPolygon,
    face_attribute: int,
) -> int:
    if len(vertices) < 3 or vertex_polygon_area_3d(vertices) <= 1e-11:
        return 0
    base_index = len(patch.vertices) // 8
    for vertex in vertices:
        patch.vertices.extend(vertex)
    generated_faces = 0
    for vertex_index in range(1, len(vertices) - 1):
        patch.indices.extend(
            [base_index, base_index + vertex_index, base_index + vertex_index + 1]
        )
        patch.face_attributes.append(face_attribute)
        generated_faces += 1
    return generated_faces


def shave_rear_wheel_strut_at_lower_shell(
    body: dict[str, core.Patch],
    visual_gear: dict[str, core.Patch],
) -> dict[str, int]:
    shell_patch = body.get("body_1")
    gear_patch = visual_gear.get("static_parts")
    if shell_patch is None or gear_patch is None:
        raise RuntimeError(
            "Cannot find body_1 and static_parts geometry for rear-wheel strut shaving."
        )
    shell_triangles = lower_shell_surface_triangles(shell_patch)
    shell_index = build_lower_shell_spatial_index(shell_triangles)
    target_min_x = (
        REAR_WHEEL_STRUT_SHAVE_BASE_X_RANGE[0] + _current_pilot_alignment_x_delta
    )
    target_max_x = (
        REAR_WHEEL_STRUT_SHAVE_BASE_X_RANGE[1] + _current_pilot_alignment_x_delta
    )
    source_face_count = len(gear_patch.indices) // 3
    shaved = core.Patch(gear_patch.material_name)
    vertex_map: dict[int, int] = {}
    modified_faces = 0
    fully_removed_faces = 0
    generated_faces = 0

    for face_offset in range(0, len(gear_patch.indices), 3):
        face_indices = gear_patch.indices[face_offset : face_offset + 3]
        if len(face_indices) != 3:
            continue
        face_attribute = (
            gear_patch.face_attributes[face_offset // 3]
            if gear_patch.face_attributes
            else 0
        )
        face_vertices: VertexPolygon = [
            tuple(gear_patch.vertices[index * 8 : index * 8 + 8])  # type: ignore[misc]
            for index in face_indices
        ]
        if (
            max(vertex[0] for vertex in face_vertices) < target_min_x
            or min(vertex[0] for vertex in face_vertices) > target_max_x
            or max(vertex[1] for vertex in face_vertices)
            < -REAR_WHEEL_STRUT_SHAVE_HALF_WIDTH_Y
            or min(vertex[1] for vertex in face_vertices)
            > REAR_WHEEL_STRUT_SHAVE_HALF_WIDTH_Y
            or max(vertex[2] for vertex in face_vertices)
            < COCKPIT_FLOOR_APERTURE_SURFACE_MIN_Z
            - REAR_WHEEL_STRUT_SHAVE_SHELL_CLEARANCE
        ):
            copy_source_face(
                gear_patch,
                shaved,
                face_indices,
                face_attribute,
                vertex_map,
            )
            continue

        edge_ab = interpolate_mesh_vertex(face_vertices[0], face_vertices[1], 0.5)
        edge_bc = interpolate_mesh_vertex(face_vertices[1], face_vertices[2], 0.5)
        edge_ca = interpolate_mesh_vertex(face_vertices[2], face_vertices[0], 0.5)
        centroid = interpolate_mesh_vertex(edge_ab, face_vertices[2], 1.0 / 3.0)
        sampled_vertices = [*face_vertices, edge_ab, edge_bc, edge_ca, centroid]
        sampled_distances = []
        for vertex in sampled_vertices:
            shell_z, _normal = sample_indexed_lower_shell_at_xy(
                shell_index,
                (vertex[0], vertex[1]),
            )
            sampled_distances.append(
                vertex[2]
                - (shell_z - REAR_WHEEL_STRUT_SHAVE_SHELL_CLEARANCE)
            )
        if max(sampled_distances) <= 1e-9:
            copy_source_face(
                gear_patch,
                shaved,
                face_indices,
                face_attribute,
                vertex_map,
            )
            continue

        modified_faces += 1
        subdivided_faces = (
            [face_vertices[0], edge_ab, centroid],
            [edge_ab, face_vertices[1], centroid],
            [face_vertices[1], edge_bc, centroid],
            [edge_bc, face_vertices[2], centroid],
            [face_vertices[2], edge_ca, centroid],
            [edge_ca, face_vertices[0], centroid],
        )
        generated_for_source_face = 0
        for subdivided_face in subdivided_faces:
            retained = clip_vertex_polygon_below_lower_shell(
                subdivided_face,
                shell_index,
            )
            generated_for_source_face += append_vertex_polygon_3d(
                shaved,
                retained,
                face_attribute,
            )
        if generated_for_source_face == 0:
            fully_removed_faces += 1
        generated_faces += generated_for_source_face

    gear_patch.vertices = shaved.vertices
    gear_patch.indices = shaved.indices
    gear_patch.face_attributes = shaved.face_attributes
    stats = {
        "source_faces": source_face_count,
        "modified_faces": modified_faces,
        "fully_removed_faces": fully_removed_faces,
        "generated_faces": generated_faces,
        "result_faces": len(gear_patch.indices) // 3,
    }
    expected_stats = {
        "source_faces": REAR_WHEEL_STRUT_SHAVE_EXPECTED_SOURCE_FACES,
        "modified_faces": REAR_WHEEL_STRUT_SHAVE_EXPECTED_MODIFIED_FACES,
        "fully_removed_faces": REAR_WHEEL_STRUT_SHAVE_EXPECTED_REMOVED_FACES,
        "generated_faces": REAR_WHEEL_STRUT_SHAVE_EXPECTED_GENERATED_FACES,
        "result_faces": REAR_WHEEL_STRUT_SHAVE_EXPECTED_RESULT_FACES,
    }
    mismatches = [
        f"{name}={stats[name]} (expected {expected})"
        for name, expected in expected_stats.items()
        if stats[name] != expected
    ]
    if mismatches:
        raise RuntimeError(
            "Refusing unexpected rear-wheel strut shave topology: "
            + ", ".join(mismatches)
            + "."
        )
    return stats


def build_selected_nodes_for_dev(
    *,
    gltf: dict,
    buffers: list[bytes],
    mesh_nodes: list[tuple[int, list[float]]],
    materials: dict[int, Material],
    center_x: float,
    center_y: float,
    z_offset: float,
    node_regex: str,
) -> dict[str, core.Patch]:
    selected = re.compile(node_regex, re.IGNORECASE)
    shortened_support_nodes = [
        entry
        for entry in mesh_nodes
        if selected.search(gltf["nodes"][entry[0]].get("name", ""))
        and (
            REAR_STRUT_NODE_RE.fullmatch(gltf["nodes"][entry[0]].get("name", ""))
            or PROTRUDING_MAIN_GEAR_SUPPORT_NODE_RE.fullmatch(
                gltf["nodes"][entry[0]].get("name", "")
            )
        )
    ]
    tire_nodes = [
        entry
        for entry in mesh_nodes
        if selected.search(gltf["nodes"][entry[0]].get("name", ""))
        and TIRE_NODE_RE.fullmatch(gltf["nodes"][entry[0]].get("name", ""))
    ]
    if not shortened_support_nodes and not tire_nodes:
        return _ORIGINAL_BUILD_SELECTED_NODES(
            gltf=gltf,
            buffers=buffers,
            mesh_nodes=mesh_nodes,
            materials=materials,
            center_x=center_x,
            center_y=center_y,
            z_offset=z_offset,
            node_regex=node_regex,
        )

    isolated_node_indices = {entry[0] for entry in shortened_support_nodes + tire_nodes}
    remaining_nodes = [entry for entry in mesh_nodes if entry[0] not in isolated_node_indices]
    patches = _ORIGINAL_BUILD_SELECTED_NODES(
        gltf=gltf,
        buffers=buffers,
        mesh_nodes=remaining_nodes,
        materials=materials,
        center_x=center_x,
        center_y=center_y,
        z_offset=z_offset,
        node_regex=node_regex,
    )
    if shortened_support_nodes:
        shortened_names: list[str] = []
        hidden_side_support_names: list[str] = []
        # Shorten each support separately. Combining the center tail-wheel support
        # with the paired side supports would produce a false PCA axis spanning the
        # length of the aircraft and deform otherwise unrelated landing gear.
        for support_node in shortened_support_nodes:
            support_name = gltf["nodes"][support_node[0]].get("name", "")
            support_patches = _ORIGINAL_BUILD_SELECTED_NODES(
                gltf=gltf,
                buffers=buffers,
                mesh_nodes=[support_node],
                materials=materials,
                center_x=center_x,
                center_y=center_y,
                z_offset=z_offset,
                node_regex=node_regex,
            )
            if PROTRUDING_MAIN_GEAR_SUPPORT_NODE_RE.fullmatch(support_name):
                hidden_side_support_names.append(support_name)
                continue
            for material_name, support_patch in support_patches.items():
                shorten_patch_along_xz_axis(support_patch, REAR_STRUT_LENGTH_SCALE)
                append_patch_geometry(
                    patches.setdefault(material_name, core.Patch(material_name)),
                    support_patch,
                )
            shortened_names.append(support_name)
        if shortened_names:
            print(
                "Dev gear cleanup: shortened visual supports "
                f"{', '.join(shortened_names)} to {REAR_STRUT_LENGTH_SCALE:.0%} length "
                "from their wheel-side anchors."
            )
        if hidden_side_support_names:
            print(
                "Dev gear cleanup: hid protruding side/rear support meshes "
                f"{', '.join(hidden_side_support_names)}."
            )

    if not tire_nodes:
        return patches

    tire_source_patches = _ORIGINAL_BUILD_SELECTED_NODES(
        gltf=gltf,
        buffers=buffers,
        mesh_nodes=tire_nodes,
        materials=materials,
        center_x=center_x,
        center_y=center_y,
        z_offset=z_offset,
        node_regex=node_regex,
    )

    add_generated_material(
        materials,
        name=TIRE_BLACK_MATERIAL,
        texture_name=TIRE_BLACK_MATERIAL,
        color=TIRE_BLACK_COLOR,
        source_uri="generated-gtvr-dev-tire-black",
    )
    tire_patch = core.Patch(TIRE_BLACK_MATERIAL)
    for source_patch in tire_source_patches.values():
        append_patch_geometry(tire_patch, source_patch)
    if tire_patch.indices:
        patches[TIRE_BLACK_MATERIAL] = tire_patch
    return patches


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
    small = load_font(24)
    medium = load_font(34)

    draw.rounded_rectangle((14, 12, 498, 500), radius=18, fill=(5, 12, 15), outline=(74, 190, 190), width=4)
    draw.text((164, 28), "FLIGHT DATA", font=medium, fill=(114, 230, 190))
    draw.text((48, 112), "AIRSPEED", font=small, fill=(130, 240, 240))
    draw.text((378, 112), "KTS", font=small, fill=(130, 240, 240))
    draw.rounded_rectangle((72, 150, 440, 258), radius=12, fill=(1, 5, 7), outline=(225, 245, 238), width=3)
    draw.text((52, 300), "ALTITUDE", font=small, fill=(130, 240, 240))
    draw.text((390, 300), "FT", font=small, fill=(130, 240, 240))
    draw.rounded_rectangle((56, 338, 456, 446), radius=12, fill=(1, 5, 7), outline=(225, 245, 238), width=3)
    draw.line((22, 278, 490, 278), fill=(35, 115, 112), width=2)
    draw.text((163, 468), "GTVR WRAITH", font=small, fill=(80, 235, 170))
    image.save(path)


def write_cockpit_pfd_source_texture(path: Path) -> None:
    """Write the digit atlas and immutable PFD background used by Aerofly's live texture renderer."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1024, 1024), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    digit_font = load_font(82)
    for digit in range(10):
        left = digit * 64
        bounds = draw.textbbox((0, 0), str(digit), font=digit_font)
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        x = left + (64 - width) // 2
        y = (98 - height) // 2 - bounds[1]
        draw.text((x, y), str(digit), font=digit_font, fill=(225, 245, 238))

    background = Image.new("RGB", (512, 512), (4, 8, 10))
    background_path = path.with_name(f"{COCKPIT_PFD_TEXTURE}.png")
    write_cockpit_pfd_texture(background_path)
    with Image.open(background_path) as source_background:
        background.paste(source_background.convert("RGB"))
    image.paste(background, (0, 512))
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

    image = Image.new("RGB", (256, 256), base)
    pixels = image.load()
    for y in range(256):
        for x in range(256):
            grain = ((x * 17 + y * 31 + (x * y) % 19) % 7) - 3
            pixels[x, y] = tuple(max(0, min(255, channel + grain)) for channel in base)

    draw = ImageDraw.Draw(image)
    subtle_grain = tuple((base_channel * 3 + seam_channel) // 4 for base_channel, seam_channel in zip(base, seam))
    for row in range(18, 256, 24):
        points = [(x, row + int(1.5 * math.sin(x * 0.075 + row * 0.11))) for x in range(0, 256, 4)]
        draw.line(points, fill=subtle_grain, width=1)
    for index in range(26):
        x = (index * 73 + 19) % 232
        y = (index * 47 + 31) % 248
        length = 9 + (index % 5) * 3
        draw.line((x, y, min(255, x + length), y + (index % 3) - 1), fill=subtle_grain, width=1)
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

    write_png(core.SOURCE_DIR / f"{CONTROL_SPECULAR_TEXTURE}.png", (0, 0, 0))
    write_png(core.SOURCE_DIR / f"{CONTROL_REFLECTION_TEXTURE}.png", (0, 0, 0))
    write_png(core.SOURCE_DIR / f"{MATTE_BLACK_SURFACE_TEXTURE}.png", (0, 0, 0))
    write_png(core.SOURCE_DIR / f"{LEATHER_SPECULAR_TEXTURE}.png", (24, 20, 18))
    write_png(core.SOURCE_DIR / f"{LEATHER_REFLECTION_TEXTURE}.png", (4, 4, 4))

    write_cockpit_seat_texture(core.SOURCE_DIR / "gtvr_cockpit_seat.png", (30, 18, 12), (38, 24, 17))
    write_cockpit_seat_texture(core.SOURCE_DIR / "gtvr_cockpit_seat_highlight.png", (46, 28, 19), (56, 36, 25))
    write_cockpit_seat_texture(core.SOURCE_DIR / "gtvr_cockpit_seat_shadow.png", (14, 8, 5), (22, 13, 8))

    pfd_path = core.SOURCE_DIR / f"{COCKPIT_PFD_TEXTURE}.png"
    pfd_source_path = core.SOURCE_DIR / f"{COCKPIT_PFD_SOURCE_TEXTURE}.png"
    center_map_path = core.SOURCE_DIR / f"{CENTER_MAP_TEXTURE}.png"
    write_png(core.SOURCE_DIR / f"{STOCK_DISPLAY_TEXTURE}.png", (0, 0, 0))
    write_cockpit_pfd_texture(pfd_path)
    write_cockpit_pfd_source_texture(pfd_source_path)
    write_cockpit_map_texture(center_map_path)
    if not any(material.name == STOCK_DISPLAY_MATERIAL for material in materials.values()):
        materials[next_material_index(materials)] = Material(
            name=STOCK_DISPLAY_MATERIAL,
            texture_name=STOCK_DISPLAY_TEXTURE,
            source_uri="inherited-runtime-display-light",
            color=(0, 0, 0, 255),
        )
    if not any(material.name == COCKPIT_PFD_MATERIAL for material in materials.values()):
        materials[next_material_index(materials)] = Material(
            name=COCKPIT_PFD_MATERIAL,
            texture_name=COCKPIT_PFD_TEXTURE,
            source_uri="generated-gtvr-dev-cockpit-flight",
            color=(24, 170, 180, 255),
        )
    if not any(material.name == COCKPIT_PFD_SOURCE_TEXTURE for material in materials.values()):
        materials[next_material_index(materials)] = Material(
            name=COCKPIT_PFD_SOURCE_TEXTURE,
            texture_name=COCKPIT_PFD_SOURCE_TEXTURE,
            source_uri="generated-gtvr-dev-cockpit-flight-source",
            color=(225, 245, 238, 255),
        )
    if not any(material.name == CENTER_MAP_MATERIAL for material in materials.values()):
        materials[next_material_index(materials)] = Material(
            name=CENTER_MAP_MATERIAL,
            texture_name=CENTER_MAP_TEXTURE,
            source_uri="generated-gtvr-dev-center-map-panel-target",
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


def append_rounded_box(
    body: dict[str, core.Patch],
    material_name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    radius: float,
    *,
    segments: int = 5,
) -> None:
    """Append a closed box with genuinely rounded edges and corners."""
    if segments < 1:
        raise ValueError("segments must be at least 1")
    half = tuple(dimension * 0.5 for dimension in size)
    radius = min(radius, *half)
    if radius <= 1e-9:
        append_box(body, material_name, center, size)
        return
    core = tuple(component - radius for component in half)

    def rounded_point(local: list[float]) -> tuple[float, float, float]:
        closest = [max(-core[axis], min(core[axis], local[axis])) for axis in range(3)]
        offset = [local[axis] - closest[axis] for axis in range(3)]
        length = math.sqrt(sum(component * component for component in offset))
        if length <= 1e-9:
            return tuple(center[axis] + local[axis] for axis in range(3))
        return tuple(
            center[axis] + closest[axis] + offset[axis] / length * radius
            for axis in range(3)
        )

    for fixed_axis in range(3):
        other_axes = [axis for axis in range(3) if axis != fixed_axis]
        axis_u, axis_v = other_axes
        for sign in (-1.0, 1.0):
            for segment_u in range(segments):
                u0 = -half[axis_u] + size[axis_u] * segment_u / segments
                u1 = -half[axis_u] + size[axis_u] * (segment_u + 1) / segments
                for segment_v in range(segments):
                    v0 = -half[axis_v] + size[axis_v] * segment_v / segments
                    v1 = -half[axis_v] + size[axis_v] * (segment_v + 1) / segments
                    local_points: list[list[float]] = []
                    for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
                        local = [0.0, 0.0, 0.0]
                        local[fixed_axis] = sign * half[fixed_axis]
                        local[axis_u] = u
                        local[axis_v] = v
                        local_points.append(local)
                    points = [rounded_point(local) for local in local_points]
                    raw_normal = vector_cross(vector_sub(points[1], points[0]), vector_sub(points[2], points[0]))
                    if raw_normal[fixed_axis] * sign < 0.0:
                        points.reverse()
                    append_auto_quad(body, material_name, points)


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


def append_smooth_tube(
    body: dict[str, core.Patch],
    material_name: str,
    control_points: list[tuple[float, float, float]],
    radius: float,
    *,
    samples_per_segment: int = 6,
    radial_segments: int = 24,
    caps: bool = True,
) -> None:
    """Append a Catmull-Rom swept tube through the supplied control points."""
    if len(control_points) < 2:
        raise ValueError("A smooth tube requires at least two control points")
    if samples_per_segment < 1:
        raise ValueError("samples_per_segment must be at least 1")
    if radial_segments < 3:
        raise ValueError("radial_segments must be at least 3")

    padded = [control_points[0], *control_points, control_points[-1]]
    path: list[tuple[float, float, float]] = []
    for segment_index in range(len(control_points) - 1):
        p0, p1, p2, p3 = padded[segment_index : segment_index + 4]
        for sample_index in range(samples_per_segment):
            t = sample_index / samples_per_segment
            t2 = t * t
            t3 = t2 * t
            path.append(
                tuple(
                    0.5
                    * (
                        2.0 * p1[axis]
                        + (-p0[axis] + p2[axis]) * t
                        + (2.0 * p0[axis] - 5.0 * p1[axis] + 4.0 * p2[axis] - p3[axis]) * t2
                        + (-p0[axis] + 3.0 * p1[axis] - 3.0 * p2[axis] + p3[axis]) * t3
                    )
                    for axis in range(3)
                )
            )
    path.append(control_points[-1])

    patch = patch_for(body, material_name)
    rings: list[list[tuple[float, float, float]]] = []
    ring_normals: list[list[tuple[float, float, float]]] = []
    for point_index, point in enumerate(path):
        if point_index == 0:
            tangent = vector_normalize(vector_sub(path[1], path[0]))
        elif point_index == len(path) - 1:
            tangent = vector_normalize(vector_sub(path[-1], path[-2]))
        else:
            tangent = vector_normalize(vector_sub(path[point_index + 1], path[point_index - 1]))
        reference = (0.0, 1.0, 0.0) if abs(tangent[1]) < 0.92 else (0.0, 0.0, 1.0)
        right = vector_normalize(vector_cross(tangent, reference))
        up = vector_normalize(vector_cross(right, tangent))
        ring: list[tuple[float, float, float]] = []
        normals: list[tuple[float, float, float]] = []
        for radial_index in range(radial_segments):
            angle = radial_index / radial_segments * math.tau
            normal = vector_add(vector_mul(right, math.cos(angle)), vector_mul(up, math.sin(angle)))
            normals.append(normal)
            ring.append(vector_add(point, vector_mul(normal, radius)))
        rings.append(ring)
        ring_normals.append(normals)

    for path_index in range(len(path) - 1):
        for radial_index in range(radial_segments):
            next_radial_index = (radial_index + 1) % radial_segments
            base = len(patch.vertices) // 8
            for point, normal, uv in (
                (
                    rings[path_index][radial_index],
                    ring_normals[path_index][radial_index],
                    (radial_index / radial_segments, path_index / (len(path) - 1)),
                ),
                (
                    rings[path_index][next_radial_index],
                    ring_normals[path_index][next_radial_index],
                    (next_radial_index / radial_segments, path_index / (len(path) - 1)),
                ),
                (
                    rings[path_index + 1][next_radial_index],
                    ring_normals[path_index + 1][next_radial_index],
                    (next_radial_index / radial_segments, (path_index + 1) / (len(path) - 1)),
                ),
                (
                    rings[path_index + 1][radial_index],
                    ring_normals[path_index + 1][radial_index],
                    (radial_index / radial_segments, (path_index + 1) / (len(path) - 1)),
                ),
            ):
                patch.vertices.extend(
                    [point[0], point[1], point[2], normal[0], normal[1], normal[2], uv[0], uv[1]]
                )
            patch.indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])
            patch.face_attributes.extend([0, 0])

    if caps:
        start_tangent = vector_normalize(vector_sub(path[1], path[0]))
        end_tangent = vector_normalize(vector_sub(path[-1], path[-2]))
        append_cap(patch, path[0], list(reversed(rings[0])), vector_mul(start_tangent, -1.0))
        append_cap(patch, path[-1], rings[-1], end_tangent)


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


def add_front_gear_brace_connectors(
    materials: dict[int, Material],
    visual_gear: dict[str, core.Patch],
) -> dict[str, int]:
    """Bridge the existing front-gear diagonals into the fuselage-side mounts."""
    if FRONT_GEAR_BRACE_SOURCE_MATERIAL not in visual_gear:
        raise RuntimeError(
            f"Cannot find {FRONT_GEAR_BRACE_SOURCE_MATERIAL} geometry for front-gear brace connectors."
        )
    existing_patch = visual_gear.get(FRONT_GEAR_BRACE_MATERIAL)
    if existing_patch is not None and existing_patch.indices:
        raise RuntimeError("Front-gear brace connector material already contains geometry.")
    add_generated_material(
        materials,
        name=FRONT_GEAR_BRACE_MATERIAL,
        texture_name=FRONT_GEAR_BRACE_MATERIAL,
        color=FRONT_GEAR_BRACE_COLOR,
        source_uri="generated-gtvr-dev-front-gear-brace-match",
    )

    source_face_count = 0
    connector_count = 0
    for side in (-1.0, 1.0):
        start = (
            FRONT_GEAR_BRACE_BASE_START[0] + _current_pilot_alignment_x_delta,
            side * FRONT_GEAR_BRACE_BASE_START[1],
            FRONT_GEAR_BRACE_BASE_START[2],
        )
        end = (
            FRONT_GEAR_BRACE_BASE_END[0] + _current_pilot_alignment_x_delta,
            side * FRONT_GEAR_BRACE_BASE_END[1],
            FRONT_GEAR_BRACE_BASE_END[2],
        )
        append_cylinder_between(
            visual_gear,
            FRONT_GEAR_BRACE_MATERIAL,
            start,
            end,
            FRONT_GEAR_BRACE_RADIUS,
            segments=FRONT_GEAR_BRACE_SEGMENTS,
            caps=True,
        )
        connector_count += 1

    gear_patch = visual_gear[FRONT_GEAR_BRACE_MATERIAL]
    result_face_count = len(gear_patch.indices) // 3
    added_faces = result_face_count - source_face_count
    if added_faces != FRONT_GEAR_BRACE_EXPECTED_ADDED_FACES:
        raise RuntimeError(
            "Front-gear brace connector topology drifted: "
            f"expected {FRONT_GEAR_BRACE_EXPECTED_ADDED_FACES} added faces, got {added_faces}."
        )
    return {
        "connectors": connector_count,
        "source_faces": source_face_count,
        "added_faces": added_faces,
        "result_faces": result_face_count,
    }


def append_textured_panel(
    body: dict[str, core.Patch],
    material_name: str,
    *,
    center: tuple[float, float, float],
    width_y: float,
    height_z: float,
    uv_rect: tuple[float, float, float, float] | None = None,
    double_sided: bool = True,
) -> None:
    patch = patch_for(body, material_name)
    x, y, z = center
    half_w = width_y * 0.5
    half_h = height_z * 0.5
    u_min, v_min, u_max, v_max = uv_rect or (0.0, 0.0, 1.0, 1.0)
    front = [
        (x, y - half_w, z - half_h),
        (x, y - half_w, z + half_h),
        (x, y + half_w, z + half_h),
        (x, y + half_w, z - half_h),
    ]
    append_quad(patch, front, (-1.0, 0.0, 0.0), [(u_max, v_max), (u_max, v_min), (u_min, v_min), (u_min, v_max)])
    if double_sided:
        append_quad(
            patch,
            list(reversed(front)),
            (1.0, 0.0, 0.0),
            [(u_min, v_max), (u_min, v_min), (u_max, v_min), (u_max, v_max)],
        )


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


def append_double_sided_auto_quad(
    body: dict[str, core.Patch],
    material_name: str,
    points: list[tuple[float, float, float]],
    uvs: list[tuple[float, float]] | None = None,
) -> None:
    append_auto_quad(body, material_name, points, uvs)
    reversed_uvs = list(reversed(uvs)) if uvs is not None else None
    append_auto_quad(body, material_name, list(reversed(points)), reversed_uvs)


def tail_rotor_roll_vector(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vector
    cos_roll = math.cos(TAIL_ROTOR_PLANE_ROLL)
    sin_roll = math.sin(TAIL_ROTOR_PLANE_ROLL)
    return (x, y * cos_roll - z * sin_roll, y * sin_roll + z * cos_roll)


def tail_rotor_axis_vector() -> tuple[float, float, float]:
    return tail_rotor_roll_vector(TAIL_ROTOR_AXIS)


def append_tail_rotor_blade(
    rotor: dict[str, core.Patch],
    *,
    angle: float,
) -> None:
    blade_angle = angle + TAIL_ROTOR_BLADE_PHASE
    radial = tail_rotor_roll_vector((math.cos(blade_angle), 0.0, math.sin(blade_angle)))
    tangent = tail_rotor_roll_vector((-math.sin(blade_angle), 0.0, math.cos(blade_angle)))
    thickness_axis = tail_rotor_axis_vector()
    pivot = _current_tail_rotor_pivot

    def point(
        radius: float,
        width: float,
        side: float,
        thickness: float,
        thickness_side: float,
        sweep: float,
    ) -> tuple[float, float, float]:
        return vector_add(
            pivot,
            vector_add(
                vector_mul(radial, radius),
                vector_add(
                    vector_mul(tangent, sweep + width * 0.5 * side),
                    vector_mul(thickness_axis, thickness * 0.5 * thickness_side),
                ),
            ),
        )

    root_radius = TAIL_ROTOR_PROCEDURAL_ROOT_RADIUS
    mid_radius = (TAIL_ROTOR_PROCEDURAL_ROOT_RADIUS + TAIL_ROTOR_PROCEDURAL_RADIUS) * 0.55
    tip_radius = TAIL_ROTOR_PROCEDURAL_RADIUS
    marker_root = max(root_radius, tip_radius - TAIL_ROTOR_PROCEDURAL_TIP_MARKER)

    stations = [
        (root_radius, TAIL_ROTOR_PROCEDURAL_ROOT_WIDTH, TAIL_ROTOR_PROCEDURAL_ROOT_THICKNESS, 0.000),
        (mid_radius, TAIL_ROTOR_PROCEDURAL_MID_WIDTH, TAIL_ROTOR_PROCEDURAL_MID_THICKNESS, -0.030),
        (marker_root, TAIL_ROTOR_PROCEDURAL_TIP_WIDTH, TAIL_ROTOR_PROCEDURAL_TIP_THICKNESS, -0.060),
        (tip_radius, TAIL_ROTOR_PROCEDURAL_TIP_WIDTH * 0.72, TAIL_ROTOR_PROCEDURAL_TIP_THICKNESS, -0.075),
    ]

    def station_points(station: tuple[float, float, float, float]) -> dict[str, tuple[float, float, float]]:
        radius, width, thickness, sweep = station
        return {
            "leading_top": point(radius, width, -1.0, thickness, 1.0, sweep),
            "trailing_top": point(radius, width, 1.0, thickness, 1.0, sweep),
            "leading_bottom": point(radius, width, -1.0, thickness, -1.0, sweep),
            "trailing_bottom": point(radius, width, 1.0, thickness, -1.0, sweep),
        }

    section_points = [station_points(station) for station in stations]
    for index in range(len(section_points) - 1):
        material_name = "gtvr_cockpit_button_red" if index == len(section_points) - 2 else CONTROL_MATTE_BLACK_MATERIAL
        current = section_points[index]
        next_station = section_points[index + 1]
        u0 = index / (len(section_points) - 1)
        u1 = (index + 1) / (len(section_points) - 1)
        append_double_sided_auto_quad(
            rotor,
            material_name,
            [
                current["leading_top"],
                next_station["leading_top"],
                next_station["trailing_top"],
                current["trailing_top"],
            ],
            [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)],
        )
        append_double_sided_auto_quad(
            rotor,
            material_name,
            [
                current["trailing_bottom"],
                next_station["trailing_bottom"],
                next_station["leading_bottom"],
                current["leading_bottom"],
            ],
            [(u0, 1.0), (u1, 1.0), (u1, 0.0), (u0, 0.0)],
        )
        append_double_sided_auto_quad(
            rotor,
            material_name,
            [
                current["leading_bottom"],
                next_station["leading_bottom"],
                next_station["leading_top"],
                current["leading_top"],
            ],
        )
        append_double_sided_auto_quad(
            rotor,
            material_name,
            [
                current["trailing_top"],
                next_station["trailing_top"],
                next_station["trailing_bottom"],
                current["trailing_bottom"],
            ],
        )

    root = section_points[0]
    tip = section_points[-1]
    for material_name, cap in (
        (CONTROL_MATTE_BLACK_MATERIAL, root),
        ("gtvr_cockpit_button_red", tip),
    ):
        append_double_sided_auto_quad(
            rotor,
            material_name,
            [
                cap["leading_bottom"],
                cap["leading_top"],
                cap["trailing_top"],
                cap["trailing_bottom"],
            ],
        )


def append_tail_rotor_blur_streak(
    rotor: dict[str, core.Patch],
    *,
    angle: float,
) -> None:
    pivot = _current_tail_rotor_pivot
    axis_offset = vector_mul(tail_rotor_axis_vector(), TAIL_ROTOR_PROCEDURAL_TIP_THICKNESS * 1.4)
    blade_angle = angle + TAIL_ROTOR_BLADE_PHASE

    def point(radius: float, theta: float) -> tuple[float, float, float]:
        return vector_add(
            vector_add(pivot, axis_offset),
            tail_rotor_roll_vector((math.cos(theta) * radius, 0.0, math.sin(theta) * radius)),
        )

    inner = TAIL_ROTOR_BLUR_INNER_RADIUS
    outer = TAIL_ROTOR_BLUR_OUTER_RADIUS
    a0 = blade_angle - TAIL_ROTOR_BLUR_SWEEP * 0.5
    a1 = blade_angle + TAIL_ROTOR_BLUR_SWEEP * 0.5
    # Slightly skew the outer edge to mimic a moving blade smear instead of a rigid spoke.
    append_double_sided_auto_quad(
        rotor,
        TAIL_ROTOR_BLUR_MATERIAL,
        [
            point(inner, a0),
            point(outer, a0 + TAIL_ROTOR_BLUR_SWEEP * 0.4),
            point(outer, a1 + TAIL_ROTOR_BLUR_SWEEP * 0.4),
            point(inner, a1),
        ],
    )


def build_procedural_tail_rotor_geometry() -> dict[str, core.Patch]:
    rotor: dict[str, core.Patch] = {}
    pivot = _current_tail_rotor_pivot
    rotor_axis = tail_rotor_axis_vector()
    append_cylinder_between(
        rotor,
        CYCLIC_OPAQUE_MATERIAL,
        vector_add(pivot, vector_mul(rotor_axis, -0.16)),
        vector_add(pivot, vector_mul(rotor_axis, 0.16)),
        0.085,
        segments=32,
    )
    append_cylinder_between(
        rotor,
        CONTROL_MATTE_BLACK_MATERIAL,
        vector_add(pivot, vector_mul(rotor_axis, -0.22)),
        vector_add(pivot, vector_mul(rotor_axis, 0.22)),
        0.045,
        segments=24,
    )
    for blade_index in range(4):
        append_tail_rotor_blade(rotor, angle=blade_index * math.tau / 4.0)
    for streak_index in range(TAIL_ROTOR_BLUR_STREAKS):
        append_tail_rotor_blur_streak(
            rotor,
            angle=streak_index * math.tau / TAIL_ROTOR_BLUR_STREAKS + math.radians(4.0),
        )
    return rotor


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

    append_auto_quad(
        body,
        material_name,
        [
            (min_x, min_y, bottom_z),
            (min_x, max_y, bottom_z),
            (max_x, max_y, bottom_z),
            (max_x, min_y, bottom_z),
        ],
    )


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

    append_auto_quad(
        body,
        material_name,
        [
            (back_x, min_y, min_z),
            (back_x, min_y, max_z),
            (back_x, max_y, max_z),
            (back_x, max_y, min_z),
        ],
    )


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
    append_box(body, "gtvr_cockpit_black", (x + 0.012, y, z), (0.035, width_y + 0.055, height_z + 0.055))
    append_textured_panel(body, material_name, center=(x - 0.008, y, z), width_y=width_y, height_z=height_z)


def add_pfd_source_texture_keepalive(body: dict[str, core.Patch], *, screen_x: float) -> None:
    # Aerofly only converts textures that are used by geometry; this hidden chip keeps the digit atlas available.
    append_textured_panel(
        body,
        COCKPIT_PFD_SOURCE_TEXTURE,
        center=(screen_x - 0.020, 0.0, -0.330),
        width_y=0.010,
        height_z=0.010,
    )


def add_dashboard_frame(body: dict[str, core.Patch], dash_x) -> None:
    panel_x = dash_x(2.47)
    rail_x = dash_x(2.45)

    append_box(body, "gtvr_cockpit_black", (rail_x, 0.0, 0.080), (0.13, 1.22, 0.070))
    append_box(body, "gtvr_cockpit_black", (rail_x, 0.0, -0.330), (0.13, 1.22, 0.075))

    for post_y in (-0.155, 0.155):
        append_box(body, "gtvr_cockpit_black", (rail_x, post_y, -0.125), (0.12, 0.048, 0.390))


def add_pfd_static_overlay(static: dict[str, core.Patch], *, x: float, y: float, z: float) -> None:
    half_w = 0.158
    half_h = 0.158
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

    _current_live_display_pivots["Map"] = (x, y, z)

    append_panel_rect(static, "gtvr_glass_green", x=x, center_y=y, center_z=z, width_y=0.010, height_z=0.036)
    append_panel_triangle(
        static,
        "gtvr_glass_cyan",
        x=x - 0.002,
        points_yz=[(y - 0.014, z - 0.010), (y, z + 0.024), (y + 0.014, z - 0.010)],
    )


def add_live_glass_displays(*, screen_x: float) -> None:
    add_live_pfd_display(screen_x=screen_x, side_y=-0.39, side_name="Left")
    add_live_pfd_display(screen_x=screen_x, side_y=0.39, side_name="Right")
    add_live_map_display(screen_x=screen_x)


def add_stock_display_surfaces(*, screen_x: float) -> None:
    global _current_center_map_pivot
    display_x = screen_x - 0.020
    append_textured_panel(
        stock_display_geometry("DisplayPFDL"),
        STOCK_DISPLAY_MATERIAL,
        center=(display_x, -0.39, -0.12),
        width_y=SIDE_PFD_DISPLAY_WIDTH_Y,
        height_z=SIDE_PFD_DISPLAY_HEIGHT_Z,
        uv_rect=LEFT_PFD_DISPLAY_UV_RECT,
        double_sided=False,
    )
    append_textured_panel(
        stock_display_geometry("DisplayPFDR"),
        STOCK_DISPLAY_MATERIAL,
        center=(display_x, 0.39, -0.12),
        width_y=SIDE_PFD_DISPLAY_WIDTH_Y,
        height_z=SIDE_PFD_DISPLAY_HEIGHT_Z,
        uv_rect=RIGHT_PFD_DISPLAY_UV_RECT,
        double_sided=False,
    )
    _current_center_map_pivot = (display_x, 0.0, -0.12)


def add_static_display_fallback(body: dict[str, core.Patch]) -> None:
    """Keep fixed screen cues visible without duplicating the moving live layers."""
    for geometry_name in live_display_static_geometry_names():
        display_geometry = _current_live_display_geometries[geometry_name]
        fallback = core.copy_patch_map(display_geometry)
        core.translate_patch_map(fallback, DISPLAY_FALLBACK_X_OFFSET, 0.0, 0.0)
        merge_patch_map_into(body, fallback)


def add_upholstered_seat(body: dict[str, core.Patch], base_x: float, seat_y: float) -> None:
    z = lambda value: value + SEAT_Z_LIFT
    seat_bottom_x = base_x - 0.040
    append_box(body, "gtvr_cockpit_black", (seat_bottom_x, seat_y, z(-0.742)), (0.42, 0.34, 0.045))
    append_pillowed_seat_cushion(
        body,
        "gtvr_cockpit_seat",
        center=(base_x - 0.035, seat_y, z(-0.655)),
        size=(0.46, 0.39, 0.120),
    )
    append_pillowed_seat_cushion(
        body,
        "gtvr_cockpit_seat_highlight",
        center=(base_x - 0.020, seat_y, z(-0.605)),
        size=(0.32, 0.235, 0.036),
        segments_x=8,
        segments_y=6,
    )
    append_cylinder_between(
        body,
        "gtvr_cockpit_seat_highlight",
        (base_x + 0.185, seat_y - 0.155, z(-0.610)),
        (base_x + 0.185, seat_y + 0.155, z(-0.610)),
        0.050,
        segments=28,
    )
    for side in (-1.0, 1.0):
        bolster_y = seat_y + side * 0.205
        append_cylinder_between(
            body,
            "gtvr_cockpit_seat_shadow",
            (base_x - 0.225, bolster_y, z(-0.615)),
            (base_x + 0.165, bolster_y, z(-0.615)),
            0.038,
            segments=28,
        )
    for seam_y in (seat_y - 0.105, seat_y, seat_y + 0.105):
        append_cylinder_between(
            body,
            "gtvr_cockpit_seat_shadow",
            (base_x - 0.190, seam_y, z(-0.575)),
            (base_x + 0.125, seam_y, z(-0.575)),
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


def add_cyclic_controls(body: dict[str, core.Patch]) -> None:
    # Retain the exact EC135 floor/animation pivots, then sweep the shaft
    # around the seat cushion before returning the grip to hand height. Use the
    # EC135 TMQ's proven native stick slots so its existing StickTransform and
    # StickTransformCopilot controls animate the mesh independently of collective travel.
    cyclic_references = (
        (-0.39, -0.379, "StickL"),
        (0.39, 0.400, "StickR"),
    )
    for pivot_y, grip_y, geometry_name in cyclic_references:
        floor_pivot = (2.32, pivot_y, -0.785)
        # A compact tapered collar masks the floor joint without extending back
        # into the accepted seat cushion or cockpit-floor aperture.
        for start_z, end_z, radius in (
            (-0.792, -0.770, 0.047),
            (-0.770, -0.746, 0.040),
            (-0.746, -0.724, 0.033),
        ):
            append_cylinder_between(
                body,
                CYCLIC_OPAQUE_MATERIAL,
                (floor_pivot[0], floor_pivot[1], start_z),
                (floor_pivot[0], floor_pivot[1], end_z),
                radius,
                segments=36,
            )

        control = animated_control_geometry(geometry_name)
        append_smooth_tube(
            control,
            CYCLIC_OPAQUE_MATERIAL,
            [
                (2.32, pivot_y, -0.738),
                (2.34, pivot_y, -0.665),
                (2.40, grip_y, -0.540),
                (2.445, grip_y, -0.395),
                (2.395, grip_y, -0.280),
            ],
            0.019,
            samples_per_segment=7,
            radial_segments=28,
        )
        append_smooth_tube(
            control,
            CYCLIC_OPAQUE_MATERIAL,
            [
                (2.395, grip_y, -0.290),
                (2.365, grip_y, -0.235),
                (2.340, grip_y, -0.150),
                (2.350, grip_y, -0.070),
            ],
            0.029,
            samples_per_segment=7,
            radial_segments=30,
        )

        head_center = (2.357, grip_y, -0.025)
        append_rounded_box(
            control,
            CYCLIC_OPAQUE_MATERIAL,
            head_center,
            (0.070, 0.128, 0.076),
            0.014,
            segments=5,
        )
        # EC135-style rear-facing control cluster: central guarded rocker and
        # four round switches, all part of the animated cyclic geometry.
        face_x = head_center[0] - 0.040
        append_rounded_box(
            control,
            "gtvr_cockpit_button_red",
            (face_x, grip_y, head_center[2] + 0.006),
            (0.012, 0.026, 0.044),
            0.005,
            segments=3,
        )
        for button_y, button_z in (
            (grip_y - 0.043, head_center[2] + 0.017),
            (grip_y + 0.043, head_center[2] + 0.017),
            (grip_y - 0.040, head_center[2] - 0.022),
            (grip_y + 0.040, head_center[2] - 0.022),
        ):
            append_cylinder_between(
                control,
                "gtvr_cockpit_metal",
                (face_x - 0.002, button_y, button_z),
                (face_x - 0.010, button_y, button_z),
                0.010,
                segments=20,
            )


def add_collective_controls(body: dict[str, core.Patch], interior_x) -> None:
    grip_z_lift = 0.035
    for lever_y, geometry_name in (
        (-0.10, "LeftCollectiveLever"),
        (0.70, "RightCollectiveLever"),
    ):
        control = animated_control_geometry(geometry_name)
        base = (interior_x(1.34), lever_y, -0.610)
        elbow = (interior_x(1.70), lever_y, -0.485 + grip_z_lift)
        grip_end = (interior_x(1.90), lever_y, -0.445 + grip_z_lift)
        append_cylinder_between(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            (base[0] - 0.043, lever_y - 0.037, base[2] - 0.010),
            (base[0] + 0.043, lever_y + 0.037, base[2] - 0.010),
            0.024,
            segments=28,
        )
        # Preserve the accepted base and animation pivot while lifting the
        # grip/head slightly along a slimmer EC135-style lever path.
        append_smooth_tube(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            [
                base,
                (interior_x(1.50), lever_y, -0.570),
                (interior_x(1.66), lever_y, -0.495),
                elbow,
            ],
            0.019,
            samples_per_segment=6,
            radial_segments=26,
        )
        append_cylinder_between(
            control,
            "gtvr_cockpit_rubber",
            elbow,
            grip_end,
            0.029,
            segments=32,
        )

        grip_vector = vector_sub(grip_end, elbow)
        band_start = vector_add(elbow, vector_mul(grip_vector, 0.48))
        band_end = vector_add(elbow, vector_mul(grip_vector, 0.62))
        append_cylinder_between(
            control,
            "gtvr_glass_yellow",
            band_start,
            band_end,
            0.0305,
            segments=32,
        )

        head_center = (grip_end[0] + 0.004, lever_y, grip_end[2] + 0.017)
        append_rounded_box(
            control,
            CONTROL_MATTE_BLACK_MATERIAL,
            head_center,
            (0.098, 0.102, 0.056),
            0.012,
            segments=5,
        )
        head_top_z = head_center[2] + 0.032
        for button_y, material_name, radius in (
            (lever_y - 0.029, "gtvr_cockpit_button_red", 0.011),
            (lever_y + 0.029, "gtvr_cockpit_metal", 0.012),
        ):
            append_cylinder_between(
                control,
                material_name,
                (head_center[0], button_y, head_top_z - 0.004),
                (head_center[0], button_y, head_top_z + 0.008),
                radius,
                segments=20,
            )
        append_cylinder_between(
            control,
            "gtvr_cockpit_button_red",
            (head_center[0] + 0.050, lever_y, head_center[2] - 0.008),
            (head_center[0] + 0.060, lever_y, head_center[2] - 0.008),
            0.010,
            segments=20,
        )


def add_pedal_set(body: dict[str, core.Patch], interior_x) -> None:
    pz = lambda value: value + PEDAL_Z_LIFT
    # The inherited EC135 TMQ drives these pedal meshes by geometry name.
    # Keep the physical positions unchanged, but assign the opposite pedal names
    # so the generated pads follow the pilot foot animation direction. The
    # support rods stay static so their floor/crossbar anchors do not float.
    for seat_y, left_name, right_name in (
        (-0.40, "LRPedal", "LLPedal"),
        (0.40, "RRPedal", "RLPedal"),
    ):
        crossbar_x = interior_x(2.22) - PEDAL_X_REARWARD
        pad_x = interior_x(2.56) - PEDAL_X_REARWARD
        append_cylinder_between(
            body,
            PEDAL_BLACK_MATERIAL,
            (crossbar_x, seat_y - 0.16, pz(-0.710)),
            (crossbar_x, seat_y + 0.16, pz(-0.710)),
            0.014,
            segments=28,
        )
        for pedal_offset, geometry_name in ((-0.12, left_name), (0.12, right_name)):
            pedal_y = seat_y + pedal_offset
            append_cylinder_between(
                body,
                PEDAL_BLACK_MATERIAL,
                (crossbar_x, pedal_y, pz(-0.710)),
                (pad_x - 0.020, pedal_y, pz(-0.520)),
                0.015,
                segments=28,
            )
            pedal = animated_control_geometry(geometry_name)
            append_pillowed_seat_cushion(
                pedal,
                PEDAL_BLACK_MATERIAL,
                center=(pad_x, pedal_y, pz(-0.482)),
                size=(0.105, 0.170, 0.030),
                segments_x=6,
                segments_y=7,
            )
            append_cylinder_between(
                pedal,
                PEDAL_BLACK_MATERIAL,
                (pad_x - 0.020, pedal_y, pz(-0.520)),
                (pad_x - 0.020, pedal_y, pz(-0.497)),
                0.012,
                segments=20,
            )


def add_cockpit_kit(args: argparse.Namespace, materials: dict[int, Material], body: dict[str, core.Patch]) -> None:
    global _current_animated_control_geometries, _current_live_display_geometries, _current_live_display_pivots
    global _current_stock_display_geometries, _current_center_map_pivot
    global _current_cockpit_x_delta
    global _current_dash_forward_x_delta, _current_interior_forward_x_delta
    _current_animated_control_geometries = {}
    _current_live_display_geometries = {}
    _current_live_display_pivots = {}
    _current_stock_display_geometries = {}
    _current_center_map_pivot = None
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
            material_name="gtvr_cockpit_black",
            center=(screen_x, side_y, -0.12),
            width_y=0.34,
            height_z=0.34,
        )
        append_box(body, "gtvr_cockpit_black", (dash_x(2.43), side_y - 0.215, -0.12), (0.035, 0.026, 0.39))
        append_box(body, "gtvr_cockpit_black", (dash_x(2.43), side_y + 0.215, -0.12), (0.035, 0.026, 0.39))

    add_framed_screen(
        body,
        material_name="gtvr_cockpit_black",
        center=(screen_x, 0.0, -0.12),
        width_y=0.30,
        height_z=0.34,
    )
    add_stock_display_surfaces(screen_x=screen_x)

    add_cyclic_controls(body)
    add_collective_controls(body, interior_x)
    add_pedal_set(body, interior_x)

    print(
        "Dev cockpit kit: added shortened dark-brown leather seats, compact seat-clearing EC135-style cyclics, slightly raised rounded collectives on unchanged pivots, "
        "lowered rearward flat pedal pads, Wraith side PFD screens and a borderless centre ND/map surface."
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


def read_accessor_for_dev(gltf: dict, buffers: list[bytes], accessor_index: int) -> list[tuple]:
    """Decode MSFS optimized VEC2 texture coordinates without changing the shared importer."""
    accessor = gltf["accessors"][accessor_index]
    if (
        accessor.get("componentType") == 5122
        and accessor.get("type") == "VEC2"
        and not accessor.get("normalized", False)
    ):
        buffer_view = gltf["bufferViews"][accessor["bufferView"]]
        offset = buffer_view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        stride = buffer_view.get("byteStride", 4)
        data = buffers[buffer_view["buffer"]]
        decoded = [
            struct.unpack_from("<ee", data, offset + index * stride)
            for index in range(accessor["count"])
        ]
        if not all(math.isfinite(value) for row in decoded for value in row):
            raise RuntimeError(f"Non-finite optimized UV values in accessor {accessor_index}.")
        return decoded
    return _ORIGINAL_MSFS_READ_ACCESSOR(gltf, buffers, accessor_index)


def apply_wraith_livery_overrides(materials: dict[int, Material]) -> int:
    if not WRAITH_LIVERY_PATTERN.exists():
        raise FileNotFoundError(f"Missing Wraith livery artwork: {WRAITH_LIVERY_PATTERN}")

    with Image.open(WRAITH_LIVERY_PATTERN) as source_pattern:
        pattern = source_pattern.convert("RGB").resize(
            WRAITH_LIVERY_SIZE,
            Image.Resampling.LANCZOS,
        )
    pattern = ImageEnhance.Brightness(pattern).enhance(1.32)
    pattern = ImageEnhance.Contrast(pattern).enhance(1.08)

    materials_by_name = {material.name: material for material in materials.values()}
    updated = 0
    for material_name, (expected_stem, target_stem, treatment) in WRAITH_LIVERY_MATERIALS.items():
        material = materials_by_name.get(material_name)
        if material is None:
            raise RuntimeError(f"Missing required Wraith livery material: {material_name}")
        if material.texture_name != expected_stem:
            raise RuntimeError(
                f"Refusing unexpected {material_name} texture: "
                f"{material.texture_name!r} (expected {expected_stem!r})"
            )

        source_path = core.SOURCE_DIR / f"{expected_stem}.png"
        target_path = core.SOURCE_DIR / f"{target_stem}.png"
        if not source_path.exists():
            raise FileNotFoundError(f"Missing Wraith source atlas: {source_path}")
        with Image.open(source_path) as source_image:
            source_rgba = source_image.convert("RGBA")
        if source_rgba.size != WRAITH_LIVERY_SIZE:
            raise RuntimeError(
                f"Refusing unexpected {material_name} atlas size: "
                f"{source_rgba.size} (expected {WRAITH_LIVERY_SIZE})"
            )

        source_rgb = source_rgba.convert("RGB")
        if treatment == "camo":
            preserved_detail = ImageEnhance.Color(source_rgb).enhance(0.28)
            preserved_detail = ImageEnhance.Brightness(preserved_detail).enhance(0.48)
            painted_rgb = Image.blend(pattern, preserved_detail, 0.30)
            painted_rgb = ImageEnhance.Contrast(painted_rgb).enhance(1.06)
        else:
            raise RuntimeError(f"Unknown Wraith livery treatment: {treatment}")

        # Preserve genuinely dark vents, cavities, soot and panel gaps instead of painting over them.
        paint_mask = ImageOps.grayscale(source_rgb).point(
            lambda value: 0 if value <= 30 else 255 if value >= 62 else round((value - 30) * 255 / 32)
        )
        painted_rgb = Image.composite(painted_rgb, source_rgb, paint_mask)

        source_alpha = source_rgba.getchannel("A")
        painted_rgba = painted_rgb.convert("RGBA")
        painted_rgba.putalpha(source_alpha)
        painted_rgba.save(target_path, format="PNG", optimize=True)
        with Image.open(target_path) as check_image:
            if check_image.mode != "RGBA" or check_image.size != WRAITH_LIVERY_SIZE:
                raise RuntimeError(f"Invalid generated Wraith atlas: {target_path}")
            if check_image.getchannel("A").tobytes() != source_alpha.tobytes():
                raise RuntimeError(f"Wraith atlas alpha changed unexpectedly: {target_path}")

        material.texture_name = target_stem
        material.source_uri = f"generated-wraith-stealth-livery-{material_name}"
        updated += 1

    print(
        "Dev Wraith livery: generated "
        f"{updated} low-visibility charcoal/gunmetal exterior atlases from {WRAITH_LIVERY_PATTERN.name}."
    )
    return updated


def build_body_for_dev(args: argparse.Namespace):
    original_core_read_accessor = core.read_accessor
    original_msfs_read_accessor = msfs_shell.read_accessor
    core.read_accessor = read_accessor_for_dev
    msfs_shell.read_accessor = read_accessor_for_dev
    try:
        materials, body, tail_rotor, visual_gear, source_faces, imported_faces = _ORIGINAL_BUILD_BODY(args)
    finally:
        core.read_accessor = original_core_read_accessor
        msfs_shell.read_accessor = original_msfs_read_accessor
    print("Dev MSFS import: decoded optimized half-float exterior UVs.")
    apply_wraith_livery_overrides(materials)
    removed_green_faces = 0
    for material_name in list(body):
        if UNWANTED_GREEN_MATERIAL_RE.fullmatch(material_name):
            removed_green_faces += len(body[material_name].indices) // 3
            del body[material_name]
    materials = {
        material_index: material
        for material_index, material in materials.items()
        if not UNWANTED_GREEN_MATERIAL_RE.fullmatch(material.name)
    }
    if removed_green_faces:
        print(f"Dev exterior cleanup: removed {removed_green_faces} green helper/slime-light faces.")
    shift_visual_shell_for_pilot_alignment(args, body, tail_rotor, visual_gear)
    rear_strut_shave = shave_rear_wheel_strut_at_lower_shell(body, visual_gear)
    print(
        "Dev rear-wheel strut cleanup: "
        f"shaved {rear_strut_shave['modified_faces']} source faces against the lower fuselage skin "
        f"with {REAR_WHEEL_STRUT_SHAVE_SHELL_CLEARANCE * 1000:.1f} mm clearance; "
        f"removed {rear_strut_shave['fully_removed_faces']} fully internal faces."
    )
    front_brace_connectors = add_front_gear_brace_connectors(materials, visual_gear)
    print(
        "Dev front-gear brace connection: "
        f"added {front_brace_connectors['connectors']} mirrored body links "
        f"({front_brace_connectors['added_faces']} faces) without restoring the hidden full-size brackets."
    )
    floor_clip_stats, floor_aperture_frame, floor_aperture_throat = (
        carve_cockpit_floor_aperture(body)
    )
    modified_floor_faces = sum(
        stats["modified_faces"] for stats in floor_clip_stats.values()
    )
    floor_clip_summary = ", ".join(
        f"{name}={stats['modified_faces']}"
        for name, stats in floor_clip_stats.items()
    )
    print(
        "Dev cockpit floor aperture: "
        f"exactly clipped {modified_floor_faces} lower-shell faces across "
        f"{len(floor_clip_stats)} paired/auxiliary layers "
        f"({floor_clip_summary})."
    )
    if args.inner_shell:
        ensure_inner_shell_material(materials)
        duplicated_faces, skipped_materials = make_inner_shell_opaque(
            body,
            args.inner_shell_skip_material_regex,
        )
        inward_blockers = count_patch_floor_aperture_faces(
            body[INNER_SHELL_MATERIAL_NAME],
            floor_aperture_throat,
        )
        if inward_blockers:
            raise RuntimeError(
                "Refusing blocked cockpit floor aperture: "
                f"found {inward_blockers} inward faces after shell duplication."
            )
        print(
            "Dev inner shell: "
            f"duplicated {duplicated_faces} solid faces into {INNER_SHELL_MATERIAL_NAME}."
        )
        print("Dev cockpit floor aperture: verified clear through the inward shell.")
        if skipped_materials:
            skipped_preview = ", ".join(sorted(skipped_materials)[:12])
            suffix = "..." if len(skipped_materials) > 12 else ""
            print(f"Dev inner shell: skipped transparent/non-solid materials: {skipped_preview}{suffix}")
    ensure_inner_shell_material(materials)
    merge_patch_map_into(body, floor_aperture_frame)
    frame_faces = sum(len(patch.indices) // 3 for patch in floor_aperture_frame.values())
    print(
        "Dev cockpit floor aperture: "
        f"added {frame_faces} double-sided body-following matte-black trim faces."
    )
    add_cockpit_kit(args, materials, body)
    return materials, body, tail_rotor, visual_gear, source_faces, imported_faces


def current_interior_x(value: float) -> float:
    return value + _current_cockpit_x_delta + _current_interior_forward_x_delta


def fmt_vector(values: tuple[float, float, float]) -> str:
    return " ".join(f"{value:.6g}" for value in values)


def patch_map_has_faces(patches: dict[str, core.Patch]) -> bool:
    return any(patch.indices for patch in patches.values())


def build_rotor_spin_probe_geometry(
    *,
    pivot: tuple[float, float, float],
    axis: tuple[float, float, float],
    radial: tuple[float, float, float],
    inner_radius: float,
    outer_radius: float,
) -> dict[str, core.Patch]:
    """Build one obvious asymmetric arm without replacing the accepted static rotor."""
    probe: dict[str, core.Patch] = {}
    axis_unit = vector_normalize(axis)
    radial_unit = vector_normalize(radial)
    plane_offset = vector_mul(axis_unit, 0.09)
    start = vector_add(
        vector_add(pivot, plane_offset),
        vector_mul(radial_unit, inner_radius),
    )
    end = vector_add(
        vector_add(pivot, plane_offset),
        vector_mul(radial_unit, outer_radius),
    )
    append_cylinder_between(
        probe,
        ROTOR_ANIMATION_PROBE_MATERIAL,
        start,
        end,
        0.055,
        segments=12,
    )
    return probe


def patch_map_bounds_center(
    patches: dict[str, core.Patch],
    fallback: tuple[float, float, float],
) -> tuple[float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for patch in patches.values():
        for offset in range(0, len(patch.vertices), 8):
            xs.append(patch.vertices[offset])
            ys.append(patch.vertices[offset + 1])
            zs.append(patch.vertices[offset + 2])
    if not xs:
        return fallback
    return (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )


def patch_map_axis_min(patches: dict[str, core.Patch], axis_index: int) -> float | None:
    values: list[float] = []
    for patch in patches.values():
        for offset in range(0, len(patch.vertices), 8):
            values.append(patch.vertices[offset + axis_index])
    if not values:
        return None
    return min(values)


def patch_map_local_axis_max(
    patches: dict[str, core.Patch],
    axis_index: int,
    *,
    x_range: tuple[float, float],
    z_range: tuple[float, float],
) -> float | None:
    values: list[float] = []
    for patch in patches.values():
        for offset in range(0, len(patch.vertices), 8):
            x = patch.vertices[offset]
            z = patch.vertices[offset + 2]
            if x_range[0] <= x <= x_range[1] and z_range[0] <= z <= z_range[1]:
                values.append(patch.vertices[offset + axis_index])
    if not values:
        return None
    return max(values)


def patch_map_highest_point_in_box(
    patches: dict[str, core.Patch],
    *,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    z_range: tuple[float, float],
) -> tuple[float, float, float] | None:
    highest: tuple[float, float, float] | None = None
    for patch in patches.values():
        for offset in range(0, len(patch.vertices), 8):
            point = (
                patch.vertices[offset],
                patch.vertices[offset + 1],
                patch.vertices[offset + 2],
            )
            if (
                x_range[0] <= point[0] <= x_range[1]
                and y_range[0] <= point[1] <= y_range[1]
                and z_range[0] <= point[2] <= z_range[1]
                and (highest is None or point[2] > highest[2])
            ):
                highest = point
    return highest


def patch_map_material_top_center_in_box(
    patches: dict[str, core.Patch],
    *,
    material_names: tuple[str, ...],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    z_range: tuple[float, float],
) -> tuple[float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for material_name in material_names:
        patch = patches.get(material_name)
        if patch is None:
            continue
        for offset in range(0, len(patch.vertices), 8):
            x = patch.vertices[offset]
            y = patch.vertices[offset + 1]
            z = patch.vertices[offset + 2]
            if (
                x_range[0] <= x <= x_range[1]
                and y_range[0] <= y <= y_range[1]
                and z_range[0] <= z <= z_range[1]
            ):
                xs.append(x)
                ys.append(y)
                zs.append(z)
    if not xs:
        return None
    return (
        (min(xs) + max(xs)) * 0.5,
        (min(ys) + max(ys)) * 0.5,
        max(zs),
    )


def append_main_rotor_blade(
    rotor: dict[str, core.Patch],
    *,
    center: tuple[float, float, float],
    angle: float,
) -> None:
    radial = (math.cos(angle), math.sin(angle), 0.0)
    tangent = (-math.sin(angle), math.cos(angle), 0.0)
    vertical = (0.0, 0.0, 1.0)

    def point(
        radius: float,
        width: float,
        side: float,
        thickness_side: float,
        sweep: float,
    ) -> tuple[float, float, float]:
        return vector_add(
            center,
            vector_add(
                vector_mul(radial, radius),
                vector_add(
                    vector_mul(tangent, width * 0.5 * side + sweep),
                    vector_mul(vertical, MAIN_ROTOR_PROCEDURAL_BLADE_THICKNESS * 0.5 * thickness_side),
                ),
            ),
        )

    stations = [
        (
            MAIN_ROTOR_PROCEDURAL_ROOT_RADIUS,
            MAIN_ROTOR_PROCEDURAL_ROOT_WIDTH,
            0.000,
        ),
        (
            MAIN_ROTOR_PROCEDURAL_MID_RADIUS,
            MAIN_ROTOR_PROCEDURAL_MID_WIDTH,
            MAIN_ROTOR_PROCEDURAL_TIP_SWEEP * 0.35,
        ),
        (
            MAIN_ROTOR_PROCEDURAL_RADIUS,
            MAIN_ROTOR_PROCEDURAL_TIP_WIDTH,
            MAIN_ROTOR_PROCEDURAL_TIP_SWEEP,
        ),
    ]

    def station_points(station: tuple[float, float, float]) -> dict[str, tuple[float, float, float]]:
        radius, width, sweep = station
        return {
            "leading_top": point(radius, width, -1.0, 1.0, sweep),
            "trailing_top": point(radius, width, 1.0, 1.0, sweep),
            "leading_bottom": point(radius, width, -1.0, -1.0, sweep),
            "trailing_bottom": point(radius, width, 1.0, -1.0, sweep),
        }

    section_points = [station_points(station) for station in stations]
    for index in range(len(section_points) - 1):
        current = section_points[index]
        next_station = section_points[index + 1]
        u0 = index / (len(section_points) - 1)
        u1 = (index + 1) / (len(section_points) - 1)
        append_double_sided_auto_quad(
            rotor,
            CONTROL_MATTE_BLACK_MATERIAL,
            [
                current["leading_top"],
                next_station["leading_top"],
                next_station["trailing_top"],
                current["trailing_top"],
            ],
            [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)],
        )
        append_double_sided_auto_quad(
            rotor,
            CONTROL_MATTE_BLACK_MATERIAL,
            [
                current["trailing_bottom"],
                next_station["trailing_bottom"],
                next_station["leading_bottom"],
                current["leading_bottom"],
            ],
            [(u0, 1.0), (u1, 1.0), (u1, 0.0), (u0, 0.0)],
        )
        append_double_sided_auto_quad(
            rotor,
            CONTROL_MATTE_BLACK_MATERIAL,
            [
                current["leading_bottom"],
                next_station["leading_bottom"],
                next_station["leading_top"],
                current["leading_top"],
            ],
        )
        append_double_sided_auto_quad(
            rotor,
            CONTROL_MATTE_BLACK_MATERIAL,
            [
                current["trailing_top"],
                next_station["trailing_top"],
                next_station["trailing_bottom"],
                current["trailing_bottom"],
            ],
        )

    for cap in (section_points[0], section_points[-1]):
        append_double_sided_auto_quad(
            rotor,
            CONTROL_MATTE_BLACK_MATERIAL,
            [
                cap["leading_bottom"],
                cap["leading_top"],
                cap["trailing_top"],
                cap["trailing_bottom"],
            ],
        )


def append_main_rotor_blur_streak(
    rotor: dict[str, core.Patch],
    *,
    center: tuple[float, float, float],
    angle: float,
) -> None:
    blur_center = (center[0], center[1], center[2] + MAIN_ROTOR_PROCEDURAL_BLADE_THICKNESS * 1.2)

    def point(radius: float, theta: float) -> tuple[float, float, float]:
        return (
            blur_center[0] + math.cos(theta) * radius,
            blur_center[1] + math.sin(theta) * radius,
            blur_center[2],
        )

    a0 = angle - MAIN_ROTOR_BLUR_SWEEP * 0.5
    a1 = angle + MAIN_ROTOR_BLUR_SWEEP * 0.5
    append_double_sided_auto_quad(
        rotor,
        TAIL_ROTOR_BLUR_MATERIAL,
        [
            point(MAIN_ROTOR_BLUR_INNER_RADIUS, a0),
            point(MAIN_ROTOR_BLUR_OUTER_RADIUS, a0 + MAIN_ROTOR_BLUR_SWEEP * 0.35),
            point(MAIN_ROTOR_BLUR_OUTER_RADIUS, a1 + MAIN_ROTOR_BLUR_SWEEP * 0.35),
            point(MAIN_ROTOR_BLUR_INNER_RADIUS, a1),
        ],
    )


def build_procedural_main_rotor_geometry(
    center: tuple[float, float, float],
) -> dict[str, core.Patch]:
    rotor: dict[str, core.Patch] = {}
    append_cylinder_between(
        rotor,
        CONTROL_MATTE_BLACK_MATERIAL,
        (center[0], center[1], center[2] - MAIN_ROTOR_PROCEDURAL_HUB_HEIGHT * 0.5),
        (center[0], center[1], center[2] + MAIN_ROTOR_PROCEDURAL_HUB_HEIGHT * 0.5),
        MAIN_ROTOR_PROCEDURAL_HUB_RADIUS,
        segments=32,
    )
    for blade_index in range(MAIN_ROTOR_PROCEDURAL_BLADE_COUNT):
        append_main_rotor_blade(
            rotor,
            center=center,
            angle=blade_index * math.tau / MAIN_ROTOR_PROCEDURAL_BLADE_COUNT,
        )
    for streak_index in range(MAIN_ROTOR_BLUR_STREAKS):
        append_main_rotor_blur_streak(
            rotor,
            center=center,
            angle=streak_index * math.tau / MAIN_ROTOR_BLUR_STREAKS + math.radians(3.0),
        )
    return rotor


def add_generated_main_rotor_visual_to_body(
    body: dict[str, core.Patch],
) -> None:
    global _current_main_rotor_pivot, _current_main_rotor_spin_geometry
    mast_height_anchor = patch_map_highest_point_in_box(
        body,
        x_range=MAIN_ROTOR_MAST_HOLE_X_RANGE,
        y_range=MAIN_ROTOR_MAST_HOLE_Y_RANGE,
        z_range=MAIN_ROTOR_MAST_HOLE_Z_RANGE,
    )
    if mast_height_anchor is None:
        print("Dev main rotor visual alignment: skipped; could not find roof mast hole.")
        return
    mast_socket = patch_map_material_top_center_in_box(
        body,
        material_names=MAIN_ROTOR_MAST_SOCKET_MATERIALS,
        x_range=MAIN_ROTOR_MAST_SOCKET_X_RANGE,
        y_range=MAIN_ROTOR_MAST_SOCKET_Y_RANGE,
        z_range=MAIN_ROTOR_MAST_SOCKET_Z_RANGE,
    )
    mast_base = mast_socket or mast_height_anchor

    mast_bottom = (
        mast_base[0],
        mast_base[1],
        mast_base[2] - MAIN_ROTOR_MAST_COLLAR_HALF_HEIGHT,
    )
    mast_top = (
        mast_base[0],
        mast_base[1],
        mast_height_anchor[2] + MAIN_ROTOR_BASE_TO_CENTER_Z - MAIN_ROTOR_CENTER_TO_MAST_TOP_Z,
    )
    rotor_center = (
        mast_top[0],
        mast_top[1],
        mast_top[2] + MAIN_ROTOR_PROCEDURAL_PLANE_Z_OFFSET,
    )
    append_cylinder_between(
        body,
        MAIN_ROTOR_MAST_MATERIAL,
        mast_bottom,
        mast_top,
        MAIN_ROTOR_MAST_RADIUS,
        segments=32,
    )
    append_cylinder_between(
        body,
        MAIN_ROTOR_MAST_MATERIAL,
        (
            mast_base[0],
            mast_base[1],
            mast_base[2] - MAIN_ROTOR_MAST_COLLAR_HALF_HEIGHT,
        ),
        (
            mast_base[0],
            mast_base[1],
            mast_base[2] + MAIN_ROTOR_MAST_COLLAR_HALF_HEIGHT,
        ),
        MAIN_ROTOR_MAST_COLLAR_RADIUS,
        segments=32,
    )
    main_rotor = build_procedural_main_rotor_geometry(rotor_center)
    _current_main_rotor_pivot = rotor_center
    if ROTOR_ANIMATION_PROBE_ONLY:
        merge_patch_map_into(body, main_rotor)
        _current_main_rotor_spin_geometry = build_rotor_spin_probe_geometry(
            pivot=rotor_center,
            axis=(0.0, 0.0, 1.0),
            radial=(1.0, 0.0, 0.0),
            inner_radius=0.28,
            outer_radius=1.15,
        )
    else:
        _current_main_rotor_spin_geometry = core.copy_patch_map(main_rotor)
    print(
        "Dev main rotor visual replacement: "
        f"generated shaft-top four-blade main prop at ({rotor_center[0]:.3f}, "
        f"{rotor_center[1]:.3f}, {rotor_center[2]:.3f}) and hid inherited RotorBlade0-3 geometry."
    )


def control_graphic_groups() -> list[tuple[str, list[str], str]]:
    candidates = [
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

    left_cyclic_pivot = (2.32, -0.39, -0.785)
    right_cyclic_pivot = (2.32, 0.39, -0.785)
    left_collective_pivot = (current_interior_x(1.34), -0.10, -0.610)
    right_collective_pivot = (current_interior_x(1.34), 0.70, -0.610)

    return f"""
            // GTVR generated cockpit visual controls
            <[graphics_input][GTVRVisualCyclicPitchTravel][]
                <[uint32][InputID][StickCyclicPitch.Output]>
                <[float64][Scaling][0.2]>
            >
            <[graphics_input][GTVRVisualCyclicRollTravel][]
                <[uint32][InputID][StickCyclicRoll.Output]>
                <[float64][Scaling][0.2]>
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
                <[float64][Scaling][0.07]>
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


def center_map_dynamic_objects() -> str:
    # DR400/AN2-style moving-map renderers only load from the aircraft's main text TMD.
    # Wraith keeps the EC135 compiled TMQ for its working helicopter systems, so the centre
    # screen must use the already-loaded EC135 runtime display_light feed instead.
    return ""


def center_map_graphics_objects() -> str:
    return ""


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
            "            // GTVR live side displays: numeric knots/feet plus moving speed and altitude tapes.",
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
            "            <[texture_animation][GTVRPFDTextureAnimation][]",
            f"                <[string8][TextureName][{COCKPIT_PFD_TEXTURE}]>",
            "                <[tmvector4d][ClearColor][ 0.004 0.012 0.016 1.0 ]>",
            "                <[tmvector2d][TargetSize][ 512 512 ]>",
            "                <[string8][RenderList][ GTVRPFDBackground GTVRPFDSpeedDigits GTVRPFDAltitudeDigits ]>",
            "            >",
            "            <[texture_animation_rectangle][GTVRPFDBackground][]",
            f"                <[string8][TextureName][{COCKPIT_PFD_SOURCE_TEXTURE}]>",
            "                <[tmvector2d][TargetPosition][ 0 0 ]>",
            "                <[tmvector2d][TargetSize][ 512 512 ]>",
            "                <[tmvector2d][TargetScale][ 512 512 ]>",
            "                <[tmvector2d][SourcePosition][ 0 512 ]>",
            "                <[tmvector2d][SourceSize][ 512 512 ]>",
            "                <[tmvector2d][SourceScale][ 1024 1024 ]>",
            "            >",
            "            <[texture_animation_numeric_display][GTVRPFDSpeedDigits][]",
            f"                <[string8][TextureName][{COCKPIT_PFD_SOURCE_TEXTURE}]>",
            "                <[string8][Input][GTVRGlassAirspeedInput.Output]>",
            "                <[tmvector2d][TargetPosition][ 152 156 ]>",
            "                <[tmvector2d][TargetSize][ 64 98 ]>",
            "                <[tmvector2d][TargetScale][ 512 512 ]>",
            "                <[float64][TargetStride][ 72 ]>",
            "                <[float64][TargetDecimalStride][ 0 ]>",
            "                <[tmvector2d][SourcePosition][ 0 0 ]>",
            "                <[tmvector2d][SourceSize][ 64 98 ]>",
            "                <[tmvector2d][SourceScale][ 1024 1024 ]>",
            "                <[tmvector2d][SourceDotSize][ 1 1 ]>",
            "                <[float64][SourceStride][ 64 ]>",
            "                <[int32][Digits][3]>",
            "                <[int32][DecimalPlaces][0]>",
            "                <[int32][DotPosition][0]>",
            "                <[bool][ShowLeadingZeroes][false]>",
            "                <[float64][Scaling][1.943844]>",
            "            >",
            "            <[texture_animation_numeric_display][GTVRPFDAltitudeDigits][]",
            f"                <[string8][TextureName][{COCKPIT_PFD_SOURCE_TEXTURE}]>",
            "                <[string8][Input][GTVRGlassAltInput.Output]>",
            "                <[tmvector2d][TargetPosition][ 80 344 ]>",
            "                <[tmvector2d][TargetSize][ 64 98 ]>",
            "                <[tmvector2d][TargetScale][ 512 512 ]>",
            "                <[float64][TargetStride][ 72 ]>",
            "                <[float64][TargetDecimalStride][ 0 ]>",
            "                <[tmvector2d][SourcePosition][ 0 0 ]>",
            "                <[tmvector2d][SourceSize][ 64 98 ]>",
            "                <[tmvector2d][SourceScale][ 1024 1024 ]>",
            "                <[tmvector2d][SourceDotSize][ 1 1 ]>",
            "                <[float64][SourceStride][ 64 ]>",
            "                <[int32][Digits][5]>",
            "                <[int32][DecimalPlaces][0]>",
            "                <[int32][DotPosition][0]>",
            "                <[bool][ShowLeadingZeroes][false]>",
            "                <[float64][Scaling][3.280840]>",
            "            >",
            static_block,
            *pfd_blocks,
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
    center_map_dynamic = center_map_dynamic_objects()
    display_graphics = live_display_graphics_objects()
    center_map_graphics = center_map_graphics_objects()
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
{center_map_dynamic}
        >
        <[pointer_list_tmgraphics][GraphicObjects][]
            <[rigidbodygraphics][Fuselage][]
                <[uint32][PositionID][Fuselage.R]>
                <[uint32][OrientationID][Fuselage.Q]>
                <[string8][GeometryList][ {' '.join(static_geometry_names)} ]>
            >
{display_graphics}
{center_map_graphics}
{control_transforms}
{graphic_objects}
        >
    >
>
"""
    path.write_text(text, encoding="utf-8")


def patch_dev_tgi_material_shaders(path: Path) -> tuple[int, int]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    output: list[str] = []
    current_material: str | None = None
    inside_texture_list = False
    patched = 0
    surface_slots = 0
    for line in lines:
        if "<[tmxglmaterial_impexp][element]" in line:
            current_material = None
            inside_texture_list = False
        if current_material is None:
            material_match = re.search(r"<\[string8\]\[name\]\[([^\]]+)\]>", line)
            if material_match:
                current_material = material_match.group(1)
        if current_material in DEV_INTERIOR_SHADER_MATERIALS and "<[string8][shader_hint]" in line:
            line = "                <[string8][shader_hint][standard interior]>"
            patched += 1
        if "<[list_tm_tmtexture_index_pair_impexp][texture_list]" in line:
            inside_texture_list = True
        elif current_material in DEV_MATERIAL_SURFACE_MAPS and inside_texture_list and line == "                >":
            for channel, texture_name in DEV_MATERIAL_SURFACE_MAPS[current_material]:
                output.extend(
                    [
                        "                    <[tm_tmtexture_index_pair_impexp][element][0]",
                        f"                        <[string8][channel][{channel}]>",
                        f"                        <[string8][name][{texture_name}]>",
                        "                        <[bool][repeat_s][true]>",
                        "                        <[bool][repeat_t][true]>",
                        "                        <[float32][uvscaling][1]>",
                        "                    >",
                    ]
                )
                surface_slots += 1
            inside_texture_list = False
        output.append(line)
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    return patched, surface_slots


def fallback_center_map_pivot() -> tuple[float, float, float]:
    return (
        2.47 + DEFAULT_COCKPIT_X_DELTA + DEFAULT_DASH_FORWARD_X_DELTA - 0.020,
        0.0,
        -0.12,
    )


def write_map_panel_source_tmc(path: Path) -> None:
    path.write_text(
        f"""<[file][][]
    <[modelinformation][][]
        <[int32][Version][230]>
        <[list_vector4_float64][ContactSpheres][ (0.0 0.0 0.0 0.05) ]>
        <[stringt8c][ICAO][GTMP]>
        <[string8][DisplayName][Wraith Centre Map Panel]>
        <[string8][DisplayNameFull][Wraith Centre Map Panel]>
        <[float64][MaximumTakeoffMass][1.0]>
        <[uint32][MaximumPersonsOnBoard][0]>
        <[float64][WingSpan][0.30]>
        <[float64][Length][0.01]>
        <[float64][Height][0.34]>
        <[uint32][Year][2026]>
        <[uint32][EngineCount][0]>
        <[float64][EnginePower][0.0]>
        <[float64][MinimumAirspeed][0.0]>
        <[float64][ApproachAirspeed][0.0]>
        <[float64][CruiseAirspeed][0.0]>
        <[float64][CruiseAltitude][0.0]>
        <[float64][CruiseSpeed][0.0]>
        <[float64][MaximumAirspeed][0.0]>
        <[float64][MaximumAltitude][0.0]>
        <[float64][MaximumSpeed][0.0]>
        <[string8][Tags][ panel experimental ]>
    >
>
""",
        encoding="utf-8",
    )


def prepare_dev_map_panel_source(args: argparse.Namespace) -> Path:
    if MAP_PANEL_SOURCE_DIR.exists():
        shutil.rmtree(MAP_PANEL_SOURCE_DIR)
    MAP_PANEL_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    core.ensure_runtime_resources(MAP_PANEL_SOURCE_ROOT)

    center = _current_center_map_pivot or fallback_center_map_pivot()
    surface: dict[str, core.Patch] = {}
    append_textured_panel(
        surface,
        MAP_PANEL_MATERIAL,
        center=(center[0] - 0.006, center[1], center[2]),
        width_y=0.30,
        height_z=0.34,
        uv_rect=(0.0, 0.0, 1.0, 1.0),
        double_sided=False,
    )
    geometries = {"GTVRMapScreen": surface}
    materials = {
        0: Material(
            name=MAP_PANEL_MATERIAL,
            texture_name=MAP_PANEL_TEXTURE,
            source_uri="generated-gtvr-dev-independent-map-panel-light",
            color=(0, 0, 0, 255),
        )
    }

    write_map_panel_source_tmc(MAP_PANEL_SOURCE_DIR / f"{MAP_PANEL_DIR_NAME}.tmc")
    core.write_minimal_tmd(MAP_PANEL_SOURCE_DIR / f"{MAP_PANEL_DIR_NAME}.tmd", sorted(geometries))
    core.write_tgi(MAP_PANEL_SOURCE_DIR / f"{MAP_PANEL_DIR_NAME}.tgi", materials, geometries)
    core.write_model_tmc(MAP_PANEL_SOURCE_DIR / "model.tmc", materials, geometries, args.max_texture_size)
    core.write_root_converter_config(MAP_PANEL_SOURCE_ROOT / "config.tmc", MAP_PANEL_SOURCE_ROOT, MAP_PANEL_BUILD_USER)
    write_png(MAP_PANEL_SOURCE_DIR / f"{MAP_PANEL_TEXTURE}.png", (0, 0, 0))
    MAP_PANEL_SOURCE_STAMP.write_text(
        "\n".join(
            [
                "GTVR Wraith independent centre map panel source prepared.",
                f"texture={MAP_PANEL_TEXTURE}",
                f"center={fmt_vector(center)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote dev centre map panel source: {MAP_PANEL_SOURCE_DIR}")
    return MAP_PANEL_SOURCE_DIR


def write_rotor_animation_source_tmc(path: Path) -> None:
    path.write_text(
        """<[file][][]
    <[modelinformation][][]
        <[int32][Version][230]>
        <[list_vector4_float64][ContactSpheres][ (0.0 0.0 0.0 0.05) ]>
        <[stringt8c][ICAO][GTRA]>
        <[string8][DisplayName][Wraith Rotor Animation]>
        <[string8][DisplayNameFull][Wraith Rotor Animation]>
        <[float64][MaximumTakeoffMass][1.0]>
        <[uint32][MaximumPersonsOnBoard][0]>
        <[float64][WingSpan][9.8]>
        <[float64][Length][0.01]>
        <[float64][Height][2.2]>
        <[uint32][Year][2026]>
        <[uint32][EngineCount][0]>
        <[float64][EnginePower][0.0]>
        <[string8][Tags][ rotor animation experimental ]>
    >
>
""",
        encoding="utf-8",
    )


def rotor_animation_rates() -> tuple[float, float]:
    if ROTOR_ANIMATION_PROBE_ONLY:
        return ROTOR_ANIMATION_MAIN_PROBE_RATE, ROTOR_ANIMATION_TAIL_PROBE_RATE
    return MAIN_ROTOR_VISUAL_SPIN_RATE, TAIL_ROTOR_VISUAL_SPIN_RATE


def prepare_dev_rotor_animation_source(
    args: argparse.Namespace,
    materials: dict[int, Material],
) -> Path:
    if _current_main_rotor_pivot is None:
        raise RuntimeError("Cannot prepare rotor animation option without the main rotor pivot.")
    if not patch_map_has_faces(_current_main_rotor_spin_geometry):
        raise RuntimeError("Cannot prepare rotor animation option without main rotor geometry.")
    if not patch_map_has_faces(_current_tail_rotor_spin_geometry):
        raise RuntimeError("Cannot prepare rotor animation option without tail rotor geometry.")
    for label, actual, locked in (
        ("main", _current_main_rotor_pivot, GTVR_MAIN_ROTOR_LOCKED_PIVOT),
        ("tail", _current_tail_rotor_pivot, GTVR_TAIL_ROTOR_LOCKED_PIVOT),
    ):
        if max(abs(value - expected) for value, expected in zip(actual, locked)) > 5e-5:
            raise RuntimeError(
                f"Refusing to move the accepted {label} rotor pivot: "
                f"computed {fmt_vector(actual)} vs locked {fmt_vector(locked)}"
            )

    if ROTOR_ANIMATION_SOURCE_DIR.exists():
        shutil.rmtree(ROTOR_ANIMATION_SOURCE_DIR)
    ROTOR_ANIMATION_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    core.ensure_runtime_resources(ROTOR_ANIMATION_SOURCE_ROOT)

    geometries = {
        GTVR_MAIN_ROTOR_SPIN_GEOMETRY: core.copy_patch_map(_current_main_rotor_spin_geometry),
        GTVR_TAIL_ROTOR_SPIN_GEOMETRY: core.copy_patch_map(_current_tail_rotor_spin_geometry),
    }
    used_material_names = {
        material_name
        for patches in geometries.values()
        for material_name in patches
    }
    source_materials = {
        index: material
        for index, material in materials.items()
        if material.name in used_material_names
    }
    missing_materials = used_material_names - {material.name for material in source_materials.values()}
    if missing_materials:
        raise RuntimeError(
            "Missing rotor option materials: " + ", ".join(sorted(missing_materials))
        )
    for material in source_materials.values():
        source_texture = core.SOURCE_DIR / f"{material.texture_name}.png"
        if not source_texture.exists():
            raise FileNotFoundError(f"Missing rotor option source texture: {source_texture}")
        shutil.copy2(source_texture, ROTOR_ANIMATION_SOURCE_DIR / source_texture.name)

    write_rotor_animation_source_tmc(
        ROTOR_ANIMATION_SOURCE_DIR / f"{ROTOR_ANIMATION_DIR_NAME}.tmc"
    )
    core.write_minimal_tmd(
        ROTOR_ANIMATION_SOURCE_DIR / f"{ROTOR_ANIMATION_DIR_NAME}.tmd",
        sorted(geometries),
    )
    core.write_tgi(
        ROTOR_ANIMATION_SOURCE_DIR / f"{ROTOR_ANIMATION_DIR_NAME}.tgi",
        source_materials,
        geometries,
    )
    core.write_model_tmc(
        ROTOR_ANIMATION_SOURCE_DIR / "model.tmc",
        source_materials,
        geometries,
        args.max_texture_size,
    )
    core.write_root_converter_config(
        ROTOR_ANIMATION_SOURCE_ROOT / "config.tmc",
        ROTOR_ANIMATION_SOURCE_ROOT,
        ROTOR_ANIMATION_BUILD_USER,
    )
    main_rate, tail_rate = rotor_animation_rates()
    ROTOR_ANIMATION_SOURCE_STAMP.write_text(
        "\n".join(
            [
                "GTVR Wraith independent rotor animation source prepared.",
                f"probe_only={ROTOR_ANIMATION_PROBE_ONLY}",
                f"main_pivot={fmt_vector(_current_main_rotor_pivot)}",
                f"tail_pivot={fmt_vector(_current_tail_rotor_pivot)}",
                f"tail_axis={fmt_vector(tail_rotor_axis_vector())}",
                f"main_rate={main_rate:.6g}",
                f"tail_rate={tail_rate:.6g}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote dev rotor animation option source: {ROTOR_ANIMATION_SOURCE_DIR}")
    return ROTOR_ANIMATION_SOURCE_DIR


def write_preview_render_source_tmc(path: Path) -> None:
    path.write_text(
        f"""<[file][][]
    <[modelinformation][][]
        <[int32][Version][230]>
        <[list_vector4_float64][ContactSpheres][ (0.0 0.0 0.0 0.05) ]>
        <[stringt8c][ICAO][GTWP]>
        <[string8][DisplayName][Wraith Preview Render]>
        <[string8][DisplayNameFull][Wraith Preview Render]>
        <[float64][MaximumTakeoffMass][5000.0]>
        <[uint32][MaximumPersonsOnBoard][0]>
        <[float64][WingSpan][9.8]>
        <[float64][Length][17.61]>
        <[float64][Height][5.26]>
        <[uint32][Year][2026]>
        <[uint32][EngineCount][0]>
        <[float64][EnginePower][0.0]>
        <[string8][Tags][ preview render ]>
    >
>
""",
        encoding="utf-8",
    )


def prepare_dev_preview_render_source(
    args: argparse.Namespace,
    materials: dict[int, Material],
    geometries: dict[str, dict[str, core.Patch]],
) -> Path:
    if not patch_map_has_faces(_current_main_rotor_spin_geometry):
        raise RuntimeError("Cannot prepare the Wraith preview without the accepted main rotor assembly.")
    if not patch_map_has_faces(_current_tail_rotor_spin_geometry):
        raise RuntimeError("Cannot prepare the Wraith preview without the accepted tail rotor assembly.")

    if PREVIEW_RENDER_SOURCE_DIR.exists():
        shutil.rmtree(PREVIEW_RENDER_SOURCE_DIR)
    PREVIEW_RENDER_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    core.ensure_runtime_resources(PREVIEW_RENDER_SOURCE_ROOT)

    preview_geometries = {
        name: core.copy_patch_map(patches)
        for name, patches in geometries.items()
        if patch_map_has_faces(patches)
    }
    preview_geometries["GTVRPreviewMainRotorStatic"] = core.copy_patch_map(
        _current_main_rotor_spin_geometry
    )
    preview_geometries["GTVRPreviewTailRotorStatic"] = core.copy_patch_map(
        _current_tail_rotor_spin_geometry
    )

    copied_textures = 0
    for source_texture in core.SOURCE_DIR.glob("*.png"):
        shutil.copy2(source_texture, PREVIEW_RENDER_SOURCE_DIR / source_texture.name)
        copied_textures += 1
    if not copied_textures:
        raise RuntimeError("Cannot prepare the Wraith preview without source textures.")

    write_preview_render_source_tmc(
        PREVIEW_RENDER_SOURCE_DIR / f"{PREVIEW_RENDER_DIR_NAME}.tmc"
    )
    core.write_minimal_tmd(
        PREVIEW_RENDER_SOURCE_DIR / f"{PREVIEW_RENDER_DIR_NAME}.tmd",
        sorted(preview_geometries),
    )
    preview_tgi = PREVIEW_RENDER_SOURCE_DIR / f"{PREVIEW_RENDER_DIR_NAME}.tgi"
    core.write_tgi(preview_tgi, materials, preview_geometries)
    patch_dev_tgi_material_shaders(preview_tgi)
    core.write_model_tmc(
        PREVIEW_RENDER_SOURCE_DIR / "model.tmc",
        materials,
        preview_geometries,
        args.max_texture_size,
    )
    core.write_root_converter_config(
        PREVIEW_RENDER_SOURCE_ROOT / "config.tmc",
        PREVIEW_RENDER_SOURCE_ROOT,
        PREVIEW_RENDER_BUILD_USER,
    )
    PREVIEW_RENDER_SOURCE_STAMP.write_text(
        "\n".join(
            [
                "GTVR Wraith rotor-inclusive preview source prepared.",
                f"aircraft={DEV_AIRCRAFT_NAME}",
                f"main_pivot={fmt_vector(_current_main_rotor_pivot or GTVR_MAIN_ROTOR_LOCKED_PIVOT)}",
                f"tail_pivot={fmt_vector(_current_tail_rotor_pivot or GTVR_TAIL_ROTOR_LOCKED_PIVOT)}",
                f"livery={WRAITH_LIVERY_PATTERN.name}",
                "runtime_install=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        "Wrote rotor-inclusive dev preview source: "
        f"{PREVIEW_RENDER_SOURCE_DIR} ({len(preview_geometries)} geometries, {copied_textures} textures)."
    )
    return PREVIEW_RENDER_SOURCE_DIR


def prepare_source_for_dev(args: argparse.Namespace) -> None:
    global _current_tail_rotor_pivot
    global _current_main_rotor_pivot
    global _current_main_rotor_spin_geometry
    global _current_tail_rotor_spin_geometry
    _current_main_rotor_pivot = None
    _current_main_rotor_spin_geometry = {}
    _current_tail_rotor_spin_geometry = {}
    if core.SOURCE_DIR.exists():
        shutil.rmtree(core.SOURCE_DIR)
    core.SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    core.ensure_runtime_resources(core.SOURCE_ROOT)

    materials, body, tail_rotor, visual_gear, source_faces, imported_faces = core.build_body(args)
    core.add_flat_materials(materials, core.SOURCE_DIR)
    if not any(material.name == ROTOR_ANIMATION_PROBE_MATERIAL for material in materials.values()):
        write_png(
            core.SOURCE_DIR / f"{ROTOR_ANIMATION_PROBE_MATERIAL}.png",
            ROTOR_ANIMATION_PROBE_COLOR,
        )
        materials[next_material_index(materials)] = Material(
            name=ROTOR_ANIMATION_PROBE_MATERIAL,
            texture_name=ROTOR_ANIMATION_PROBE_MATERIAL,
            source_uri="generated-gtvr-dev-rotor-animation-probe",
            color=(*ROTOR_ANIMATION_PROBE_COLOR, 255),
        )
    _legacy_main_rotor, fallback_tail_rotor = core.legacy_rotor_patch_maps()
    core.translate_patch_map(fallback_tail_rotor, 0.0, 0.0, args.visual_body_lift)
    add_generated_main_rotor_visual_to_body(body)
    visual_tail_rotor = tail_rotor or fallback_tail_rotor
    body_aft_x = patch_map_axis_min(body, 0)
    tail_rotor_x = (
        body_aft_x + TAIL_ROTOR_X_FROM_TAIL_END
        if body_aft_x is not None
        else TAIL_ROTOR_BASE_PIVOT[0] + _current_pilot_alignment_x_delta
    )
    local_tail_side_y = patch_map_local_axis_max(
        body,
        1,
        x_range=(tail_rotor_x - 0.50, tail_rotor_x + 0.50),
        z_range=(TAIL_ROTOR_BASE_PIVOT[2] - 0.75, TAIL_ROTOR_BASE_PIVOT[2] + 0.75),
    )
    _current_tail_rotor_pivot = (
        tail_rotor_x,
        (local_tail_side_y + TAIL_ROTOR_SIDE_CLEARANCE)
        if local_tail_side_y is not None
        else TAIL_ROTOR_BASE_PIVOT[1],
        TAIL_ROTOR_BASE_PIVOT[2],
    )
    generated_tail_rotor = build_procedural_tail_rotor_geometry()
    if ROTOR_ANIMATION_PROBE_ONLY:
        merge_patch_map_into(body, generated_tail_rotor)
        _current_tail_rotor_spin_geometry = build_rotor_spin_probe_geometry(
            pivot=_current_tail_rotor_pivot,
            axis=tail_rotor_axis_vector(),
            radial=tail_rotor_roll_vector((0.0, 0.0, 1.0)),
            inner_radius=0.18,
            outer_radius=0.72,
        )
    else:
        _current_tail_rotor_spin_geometry = core.copy_patch_map(generated_tail_rotor)

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
            geometries[geometry_name] = {}
        elif geometry_name == "TailBlade0":
            geometries[geometry_name] = {}
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
    patched_materials, surface_slots = patch_dev_tgi_material_shaders(tgi_path)
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
                f"- Runtime display geometry groups: `{len(_current_stock_display_geometries)}`",
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
    print(f"Runtime display geometry groups: {len(_current_stock_display_geometries)}")
    if patched_materials:
        print(f"Dev cockpit materials: forced {patched_materials} generated interior/control shaders.")
    if surface_slots:
        print(f"Dev cockpit materials: added {surface_slots} explicit specular/reflection slots.")
    print(f"Imported body faces: {imported_faces}")
    prepare_dev_map_panel_source(args)
    prepare_dev_rotor_animation_source(args, materials)
    if getattr(args, "use_converted_previews", False):
        prepare_dev_preview_render_source(args, materials, geometries)


def write_source_stamp() -> None:
    DEV_SOURCE_STAMP.write_text(
        "\n".join(
            [
                "GTVR Wraith Dev source prepared.",
                f"aircraft={DEV_AIRCRAFT_NAME}",
                f"display={DEV_DISPLAY_NAME}",
                f"livery=low-visibility fractured charcoal/gunmetal Wraith scheme from {WRAITH_LIVERY_PATTERN.name}",
                "msfs_import=optimized half-float exterior UVs decoded in the dev path",
                f"preview=rotor-inclusive static render source {PREVIEW_RENDER_DIR_NAME}; runtime aircraft remains animation-option driven",
                f"inner_shell=solid materials are duplicated inward into {INNER_SHELL_MATERIAL_NAME}",
                "tyres=front and rear tyre mesh nodes use dedicated solid matte-black rubber material",
                "exterior_cleanup=opaque UH-60 boolean-helper and slime-light faces removed; tail-wheel support is shortened, paired protruding side/rear gear-support meshes stay hidden, the remaining central rear-wheel mount is shaved to the lower fuselage skin, and colour-matched single-piece mirrored links connect the surviving front-gear diagonals to the fuselage mounts",
                "floor_aperture=exactly clipped body-following tapered oval with a matte-black beveled trim collar",
                "main_rotor=inherited RotorBlade0-3 visual geometry is hidden; a generated black shaft-top four-blade main prop with blur streaks is baked into the Fuselage mesh",
                "tail_rotor=generated close-coupled side-mounted four-blade tapered physical tail rotor with red blade tips, corrected positive blade-angle tilt and grey motion-blur streaks is placed against the tail side and baked into the Fuselage mesh",
                f"rotor_animation=independent default option {ROTOR_ANIMATION_DIR_NAME}; probe_only={ROTOR_ANIMATION_PROBE_ONLY}",
                "cockpit_kit=generated shortened dark-brown leather seats, no lower shelf/dash braces, slightly raised and rearward-adjusted compact EC135-style cyclics with rounded heads, slightly raised rounded collectives on unchanged pivots, unchanged-position flat pedal pads, Wraith side PFD screens and an independent centre map panel mount",
                "animated_controls=cyclic floor pivots remain unchanged while the raised/rearward meshes occupy the EC135 TMQ's native StickL/StickR slots driven by StickTransform/StickTransformCopilot cyclic pitch-roll controls; collective geometry remains independently bound only to CollectivePitchLever.Output; unchanged-travel pedals use dev visual groups; inherited EC135 handle clickspots are suppressed in the dev package",
                "runtime_displays=DisplayPFDL and DisplayPFDR use independent PFD-only atlas windows for live speed/altitude/attitude/heading-tape side displays; the centre map is handled by an independent panel option",
                "center_map=gtvr_map_panel option includes its own compiled screen TMB and native texture_animation_map_display renderer targeting gtvr_map_panel_light",
                "display_states=dev state files force pilot/copilot PFD and ND display inputs on by default",
                "glass_fallback=placeholder display cues are not merged over the runtime display surfaces",
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

    panel_tmb_path = converted_map_panel_tmb()
    if not panel_tmb_path.exists():
        raise FileNotFoundError(
            f"Missing centre map panel converter output: {panel_tmb_path}. "
            "Run the full converter with --convert, or pass --allow-stale-tmb intentionally."
        )
    if MAP_PANEL_SOURCE_STAMP.exists() and panel_tmb_path.stat().st_mtime < MAP_PANEL_SOURCE_STAMP.stat().st_mtime:
        raise RuntimeError(
            f"Refusing to assemble stale centre map panel TMB: {panel_tmb_path} is older than {MAP_PANEL_SOURCE_STAMP}. "
            "Run the full converter with --convert, or pass --allow-stale-tmb intentionally."
        )

    rotor_tmb_path = converted_rotor_animation_tmb()
    if not rotor_tmb_path.exists():
        raise FileNotFoundError(
            f"Missing rotor animation option converter output: {rotor_tmb_path}. "
            "Run the full converter with --convert, or pass --allow-stale-tmb intentionally."
        )
    if not ROTOR_ANIMATION_SOURCE_STAMP.exists():
        raise FileNotFoundError(
            f"Missing rotor animation source stamp: {ROTOR_ANIMATION_SOURCE_STAMP}. "
            "Run --prepare-source before assembling."
        )
    if rotor_tmb_path.stat().st_mtime < ROTOR_ANIMATION_SOURCE_STAMP.stat().st_mtime:
        raise RuntimeError(
            f"Refusing to assemble stale rotor animation option TMB: {rotor_tmb_path} "
            f"is older than {ROTOR_ANIMATION_SOURCE_STAMP}. Run the full converter with --convert."
        )


def run_converter(timeout: float, use_converted_previews: bool = False) -> int:
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
    if completed.returncode != 0:
        return completed.returncode

    if MAP_PANEL_SOURCE_DIR.exists():
        panel_command = [
            sys.executable,
            str(ROOT / "tools" / "run_aerofly_converter.py"),
            MAP_PANEL_DIR_NAME,
            str(MAP_PANEL_SOURCE_ROOT),
            "--userfolder",
            str(MAP_PANEL_LAUNCH_USER),
            "--timeout",
            str(timeout),
        ]
        print("Running full Aerofly converter for Wraith independent centre map panel:")
        print(" ".join(panel_command))
        panel_completed = subprocess.run(panel_command, cwd=ROOT, check=False)
        if panel_completed.returncode != 0:
            return panel_completed.returncode

    if ROTOR_ANIMATION_SOURCE_DIR.exists():
        rotor_command = [
            sys.executable,
            str(ROOT / "tools" / "run_aerofly_converter.py"),
            ROTOR_ANIMATION_DIR_NAME,
            str(ROTOR_ANIMATION_SOURCE_ROOT),
            "--userfolder",
            str(ROTOR_ANIMATION_LAUNCH_USER),
            "--timeout",
            str(timeout),
        ]
        print("Running full Aerofly converter for Wraith independent rotor animation option:")
        print(" ".join(rotor_command))
        rotor_completed = subprocess.run(rotor_command, cwd=ROOT, check=False)
        if rotor_completed.returncode != 0:
            return rotor_completed.returncode

    if use_converted_previews:
        if not PREVIEW_RENDER_SOURCE_DIR.exists():
            raise FileNotFoundError(
                f"Missing rotor-inclusive preview source: {PREVIEW_RENDER_SOURCE_DIR}"
            )
        preview_command = [
            sys.executable,
            str(ROOT / "tools" / "run_aerofly_converter.py"),
            PREVIEW_RENDER_DIR_NAME,
            str(PREVIEW_RENDER_SOURCE_ROOT),
            "--userfolder",
            str(PREVIEW_RENDER_LAUNCH_USER),
            "--timeout",
            str(timeout),
        ]
        print("Running full Aerofly converter for the rotor-inclusive Wraith preview:")
        print(" ".join(preview_command))
        preview_completed = subprocess.run(preview_command, cwd=ROOT, check=False)
        if preview_completed.returncode != 0:
            return preview_completed.returncode

    return 0


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
                "Exterior paint uses a low-visibility fractured charcoal/gunmetal Wraith military scheme while weapons, sensors and auxiliary fixtures retain their accepted finish.",
                "The dev import decodes the source aircraft's optimized half-float exterior UVs so the livery follows the intended atlas mapping.",
                "Preview textures come from a separate static render source containing both accepted rotor assemblies; it is not installed and does not duplicate the runtime rotors.",
                "Solid shell materials include inward-facing matte black faces for cockpit-side opacity.",
                "Front and rear tyre mesh nodes use a dedicated solid matte-black rubber material; rims and struts retain their imported finish.",
                "Opaque UH-60 boolean-helper and slime-light geometry is removed; the tail-wheel support is shortened, both layers of each protruding side/rear gear-support mesh remain hidden, the remaining central rear-wheel mount is shaved to the lower fuselage skin, and colour-matched single-piece mirrored links connect the surviving front-gear diagonals to the fuselage mounts.",
                "The lower-cockpit opening follows the tapered belly contour, uses exact triangle clipping for a coherent edge, and has a body-following matte-black beveled trim collar.",
                "A generated close-coupled side-mounted four-blade tapered physical tail rotor with red blade tips, corrected positive blade-angle tilt and grey motion-blur streaks is placed against the tail side and baked into the Fuselage mesh.",
                f"The independent {ROTOR_ANIMATION_DIR_NAME} default option runs the runtime rotor animation proof; probe_only={ROTOR_ANIMATION_PROBE_ONLY}.",
                "Generated cockpit kit includes shortened dark-brown leather seats, no lower shelf/pedestal slab, slightly raised and rearward-adjusted compact EC135-style cyclics with rounded heads, slightly raised rounded collectives on unchanged pivots, unchanged-position flat pedal pads, Wraith side PFD screens and an independent centre map panel mount.",
                "Cyclic floor pivots remain unchanged while the raised/rearward meshes occupy the EC135 TMQ's native StickL and StickR slots driven by StickTransform and StickTransformCopilot cyclic pitch-roll controls; collective geometry remains independently bound only to CollectivePitchLever.Output; pedals retain unchanged travel.",
                "Inherited EC135 visible cockpit stick/collective/pedal visuals are removed from the dev model TMD static render list, and their click handles are reduced in controls.tmd so the dev-generated controls are the visible ones.",
                "Left and right screens populate DisplayPFDL and DisplayPFDR with independent PFD-only atlas windows for live speed/altitude/attitude/heading-tape data; the center map is a separate gtvr_map_panel option with its own compiled screen TMB.",
                "The gtvr_map_panel option hosts a native texture_animation_map_display renderer targeting its own gtvr_map_panel_light texture; it does not copy the C172 compiled panel TMB or add duplicate avionics dynamic objects.",
                "Pilot/copilot PFD and ND display state inputs are forced on in the dev state files.",
                "Placeholder display cues are not merged over the runtime display surfaces.",
                f"Dev pilot uses {DEV_PILOT}, the known-good EC135 pilot object.",
                f"Visual shell is shifted X {DEFAULT_PILOT_ALIGNMENT_X_DELTA:.2f}m for pilot/window alignment.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def copy_dev_auxiliary_textures() -> int:
    converted_dir = converted_tmb().parent
    copied = 0
    for texture_name in DEV_AUXILIARY_TEXTURE_NAMES:
        source = converted_dir / f"{texture_name}.ttx"
        if not source.exists():
            raise FileNotFoundError(f"Missing converted dev material texture: {source}")
        shutil.copy2(source, DEV_PACKAGE_DIR / source.name)
        copied += 1
    return copied


def copy_center_map_texture_to_package() -> Path:
    source = converted_tmb().parent / f"{CENTER_MAP_TEXTURE}.ttx"
    target = DEV_PACKAGE_DIR / source.name
    if not source.exists():
        raise FileNotFoundError(f"Missing converted centre-map texture: {source}")
    shutil.copy2(source, target)
    return target


def empty_modelmanager_tmd() -> str:
    return """<[file][][]
    <[modelmanager][][]
        <[pointer_list_tmuniverse][DynamicObjects][]
        >
        <[pointer_list_tmgraphics][GraphicObjects][]
        >
    >
>
"""


def dev_map_panel_system_tmd() -> str:
    size = MAP_PANEL_DISPLAY_SIZE
    return f"""<[file][][]
    <[modelmanager][][]
        <[pointer_list_tmuniverse][DynamicObjects][]
            // Keep the AN2 phone-map inputs as a real dynamic chain.  A literal value in the
            // graphics graph is not a valid substitute for an Aerofly object output.
            <[input_discrete][GTVRMapPanelZoom][]
                <[string8][Message][GPS.Zoom]>
                <[string8][Range][ -5.0 4.0 ]>
                <[float64][Value][-1.0]>
                <[bool][Toggle][true]>
            >
            <[output_free][GTVRMapPanelZoomOutput][]
                <[string8][Input][GTVRMapPanelZoom.Output]>
            >
            <[heading_indicator][GTVRMapPanelHeadingIndicator][]
                <[string8][Body][Fuselage]>
            >
            <[output][GTVRMapPanelHeadingAngle][]
                <[string8][Input][GTVRMapPanelHeadingIndicator.MagneticHeading]>
            >
        >
        <[pointer_list_tmgraphics][GraphicObjects][]
            // Independent centre panel using the AN2 phone's proven direct map-render chain.
            <[rigidbodygraphics][GTVRMapPanelScreen][]
                <[uint32][PositionID][Fuselage.R]>
                <[uint32][OrientationID][Fuselage.Q]>
                <[string8][GeometryList][ GTVRMapScreen ]>
            >
            <[texture_animation][GTVRMapPanelTexture][]
                <[string8][TextureName][{MAP_PANEL_TEXTURE}]>
                <[tmvector2d][TargetSize][ {size} {size} ]>
                <[string8][RenderList][ GTVRMapPanelMovingMap GTVRMapPanelOverlay ]>
            >
            <[graphics_input][GTVRMapPanelZoomInput][]
                <[uint32][InputID][GTVRMapPanelZoom.Output]>
                // Aerofly map zoom is base-2 logarithmic.  +log2(1.5) shows 50% more
                // map range than the AN2 original while preserving overlay alignment.
                <[float64][Offset][0.5849625]>
            >
            <[texture_animation_map_display][GTVRMapPanelMovingMap][]
                <[uint32][PositionID][Fuselage.R]>
                <[uint32][OrientationID][Fuselage.Q]>
                <[tmvector2d][TargetPosition][ 0 0 ]>
                <[tmvector2d][TargetSize][ 1.0 1.0 ]>
                <[tmvector2d][TargetScale][ {size} {size} ]>
                <[string8][InputZoom][GTVRMapPanelZoomInput.Output]>
            >
            <[graphics_input][GTVRMapPanelHeadingInput][]
                <[uint32][InputID][GTVRMapPanelHeadingAngle.Output]>
            >
            <[display_c172][GTVRMapPanelOverlay][]
                <[tmvector2d][TargetPosition][ 0 0 ]>
                <[tmvector2d][TargetSize][ {size} {size} ]>
                <[tmvector2d][TargetScale][ {size} {size} ]>
                // The AN2 aircraft symbol is a display glyph; 60 is 50% larger than its
                // original size of 40.  All unwanted text glyph categories remain transparent.
                <[float64][FontSize][ 60 ]>
                <[tmvector4f][ColorAircraft][ 0.373 0.992 0.000 1.0 ]>
                // Keep the useful aircraft/route overlay but suppress the AN2 phone's dense
                // navaid and airport label layer on the much smaller Wraith centre screen.
                <[tmvector4f][ColorVOR][ 0.200 1.000 1.000 0.0 ]>
                <[tmvector4f][ColorNDB][ 1.000 0.500 0.500 0.0 ]>
                // Airport labels from this option-hosted overlay do not receive the moving
                // map's live position transform, so keep them hidden rather than show false
                // static locations over moving terrain.
                <[tmvector4f][ColorAirport][ 1.000 1.000 1.000 0.0 ]>
                <[tmvector4f][ColorRoute][ 0.373 0.992 0.000 1.0 ]>
                <[tmvector4f][ColorWaypoint][ 1.000 1.000 1.000 0.0 ]>
                <[tmvector4f][ColorNextWaypoint][ 1.000 0.314 0.141 0.0 ]>
                <[tmvector4f][ColorRouteWaypoint][ 0.373 0.992 0.000 0.0 ]>
                <[string8][InputHeading][GTVRMapPanelHeadingInput.Output]>
                <[string8][InputZoom][GTVRMapPanelZoomInput.Output]>
            >
        >
    >
>
"""


def rotor_animation_system_tmd() -> str:
    main_rate, tail_rate = rotor_animation_rates()
    return f"""<[file][][]
    <[modelmanager][][]
        <[pointer_list_tmuniverse][DynamicObjects][]
            // Stock LJ45 fan pattern: an aircraft-side integral exposed to graphics by name.
            <[integral][GTVRMainRotorAnimationAngle][]
                <[string8][Input][{main_rate:.6g}]>
                <[float64][Value][0.0]>
            >
            <[output_free][GTVRMainRotorAnimationAngleOutput][]
                <[string8][Input][GTVRMainRotorAnimationAngle.Output]>
            >
            <[integral][GTVRTailRotorAnimationAngle][]
                <[string8][Input][{tail_rate:.6g}]>
                <[float64][Value][0.0]>
            >
            <[output_free][GTVRTailRotorAnimationAngleOutput][]
                <[string8][Input][GTVRTailRotorAnimationAngle.Output]>
            >
        >
        <[pointer_list_tmgraphics][GraphicObjects][]
            <[graphics_input][GTVRMainRotorAnimationAngleInput][]
                <[uint32][InputID][GTVRMainRotorAnimationAngle.Output]>
            >
            <[graphics_rotation][GTVRMainRotorAnimationTransform][]
                <[string8][Input][GTVRMainRotorAnimationAngleInput.Output]>
                <[tmvector3d][Axis][ 0.0 0.0 1.0 ]>
                <[tmvector3d][Pivot][ {fmt_vector(GTVR_MAIN_ROTOR_LOCKED_PIVOT)} ]>
            >
            <[rigidbodygraphics][GTVRMainRotorAnimationGraphics][]
                <[string8][GeometryList][ {GTVR_MAIN_ROTOR_SPIN_GEOMETRY} ]>
                <[uint32][PositionID][Fuselage.R]>
                <[uint32][OrientationID][Fuselage.Q]>
                <[string8][InputTransform][GTVRMainRotorAnimationTransform.Output]>
            >
            <[graphics_input][GTVRTailRotorAnimationAngleInput][]
                <[uint32][InputID][GTVRTailRotorAnimationAngle.Output]>
            >
            <[graphics_rotation][GTVRTailRotorAnimationTransform][]
                <[string8][Input][GTVRTailRotorAnimationAngleInput.Output]>
                <[tmvector3d][Axis][ {fmt_vector(GTVR_TAIL_ROTOR_LOCKED_AXIS)} ]>
                <[tmvector3d][Pivot][ {fmt_vector(GTVR_TAIL_ROTOR_LOCKED_PIVOT)} ]>
            >
            <[rigidbodygraphics][GTVRTailRotorAnimationGraphics][]
                <[string8][GeometryList][ {GTVR_TAIL_ROTOR_SPIN_GEOMETRY} ]>
                <[uint32][PositionID][Fuselage.R]>
                <[uint32][OrientationID][Fuselage.Q]>
                <[string8][InputTransform][GTVRTailRotorAnimationTransform.Output]>
            >
        >
    >
>
"""


def write_dev_map_panel_option() -> Path:
    panel_dir = DEV_PACKAGE_DIR / MAP_PANEL_DIR_NAME
    if panel_dir.exists():
        shutil.rmtree(panel_dir)
    panel_dir.mkdir(parents=True)

    (panel_dir / "option.tmc").write_text(
        """<[file][][]
  <[object][][]
    <[string8][Description][Wraith Centre Map]>
    <[string8][Type][default]>
    <[string8][Tags][panel]>
  >
>
""",
        encoding="utf-8",
    )
    (panel_dir / "system.tmd").write_text(dev_map_panel_system_tmd(), encoding="utf-8")
    (panel_dir / "controls.tmd").write_text(
        """<[file][][]
    <[modelmanager][][]
        <[pointer_list_tmcontrol][ControlObjects][]
        >
    >
>
""",
        encoding="utf-8",
    )
    (panel_dir / "system_cold.tmd").write_text(empty_modelmanager_tmd(), encoding="utf-8")
    (panel_dir / "system_start.tmd").write_text(empty_modelmanager_tmd(), encoding="utf-8")

    panel_tmb = converted_map_panel_tmb()
    if not panel_tmb.exists():
        raise FileNotFoundError(f"Missing converted centre map panel TMB: {panel_tmb}")
    shutil.copy2(panel_tmb, panel_dir / panel_tmb.name)

    panel_texture = panel_tmb.parent / f"{MAP_PANEL_TEXTURE}.ttx"
    if not panel_texture.exists():
        raise FileNotFoundError(f"Missing converted centre map panel texture: {panel_texture}")
    shutil.copy2(panel_texture, panel_dir / panel_texture.name)

    return panel_dir


def write_dev_rotor_animation_option() -> Path:
    option_dir = DEV_PACKAGE_DIR / ROTOR_ANIMATION_DIR_NAME
    if option_dir.exists():
        shutil.rmtree(option_dir)
    option_dir.mkdir(parents=True)

    (option_dir / "option.tmc").write_text(
        """<[file][][]
  <[object][][]
    <[string8][Description][Wraith Rotor Animation]>
    <[string8][Type][default]>
    <[string8][Tags][rotor]>
  >
>
""",
        encoding="utf-8",
    )
    (option_dir / "system.tmd").write_text(rotor_animation_system_tmd(), encoding="utf-8")
    (option_dir / "controls.tmd").write_text(
        """<[file][][]
    <[modelmanager][][]
        <[pointer_list_tmcontrol][ControlObjects][]
        >
    >
>
""",
        encoding="utf-8",
    )
    (option_dir / "system_cold.tmd").write_text(empty_modelmanager_tmd(), encoding="utf-8")
    (option_dir / "system_start.tmd").write_text(empty_modelmanager_tmd(), encoding="utf-8")

    option_tmb = converted_rotor_animation_tmb()
    if not option_tmb.exists():
        raise FileNotFoundError(f"Missing converted rotor animation option TMB: {option_tmb}")
    shutil.copy2(option_tmb, option_dir / option_tmb.name)
    expected_texture_names = {
        texture.stem
        for texture in ROTOR_ANIMATION_SOURCE_DIR.glob("*.png")
    }
    for texture_name in sorted(expected_texture_names):
        texture = option_tmb.parent / f"{texture_name}.ttx"
        if not texture.exists():
            raise FileNotFoundError(
                f"Missing converted rotor animation option texture: {texture}"
            )
        shutil.copy2(texture, option_dir / texture.name)
    return option_dir


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


def force_dev_stock_display_state(path: Path) -> int:
    if not path.exists():
        return 0

    text = path.read_text(encoding="utf-8", errors="replace")
    changed = 0
    for input_name in STOCK_DISPLAY_STATE_INPUTS:
        pattern = re.compile(
            rf"(<\[(?:input_binary|input_switch)\]\[{re.escape(input_name)}\]\[\]\s*)"
            r"<\[float64\]\[Value\]\[[^\]]+\]\>",
            re.MULTILINE,
        )
        text, replacements = pattern.subn(r"\1<[float64][Value][1.0]>", text)
        changed += replacements

    for object_type, input_name, value in EC135_ND_MAP_STATE_INPUTS:
        value_text = f"{value:.1f}"
        existing_pattern = re.compile(
            rf"(<\[[^\]]+\]\[{re.escape(input_name)}\]\[\](?:(?!\n\s*<\[[^\]]+\]\[[^\]]+\]\[\]).)*?"
            r"<\[float64\]\[Value\]\[)[^\]]+(\]>)",
            re.DOTALL,
        )
        text, replacements = existing_pattern.subn(rf"\g<1>{value_text}\2", text, count=1)
        if replacements:
            changed += replacements
            continue

        closing_pattern = re.compile(r"(\n\s{8}>\s*\n\s{4}>\s*\n>\s*)\Z")
        block = (
            f"\n            <[{object_type}][{input_name}][]\n"
            f"                <[float64][Value][{value_text}]>\n"
            "            >"
        )
        text, replacements = closing_pattern.subn(block + r"\1", text, count=1)
        changed += replacements

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


def preserve_installed_dev_previews(user_root: Path) -> int:
    installed_dev = user_root / "aircraft" / DEV_AIRCRAFT_NAME
    if installed_dev.name != DEV_AIRCRAFT_NAME:
        raise RuntimeError(f"Refusing unexpected installed Dev preview source: {installed_dev}")
    if not installed_dev.exists():
        return 0

    preserved = 0
    for filename in DEV_PREVIEW_FILENAMES:
        source = installed_dev / filename
        if not source.exists():
            continue
        if source.stat().st_size <= 0:
            raise RuntimeError(f"Refusing empty installed Dev preview: {source}")
        shutil.copy2(source, DEV_PACKAGE_DIR / filename)
        preserved += 1
    return preserved


def install_converted_dev_previews() -> int:
    if not PREVIEW_RENDER_SOURCE_STAMP.exists():
        raise FileNotFoundError(
            f"Missing rotor-inclusive preview source stamp: {PREVIEW_RENDER_SOURCE_STAMP}"
        )
    source_stamp_time = PREVIEW_RENDER_SOURCE_STAMP.stat().st_mtime
    preview_tmb = converted_preview_render_tmb()
    if not preview_tmb.exists() or preview_tmb.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing rotor-inclusive preview TMB: {preview_tmb}")
    if preview_tmb.stat().st_mtime < source_stamp_time:
        raise RuntimeError(f"Refusing stale rotor-inclusive preview TMB: {preview_tmb}")

    master_preview = PREVIEW_RENDER_SOURCE_DIR / f"preview_{PREVIEW_RENDER_DIR_NAME}.tif"
    if not master_preview.exists() or master_preview.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing converted dev preview master: {master_preview}")
    if master_preview.stat().st_mtime < source_stamp_time:
        raise RuntimeError(f"Refusing stale dev preview master: {master_preview}")

    with Image.open(master_preview) as preview_image:
        if preview_image.format != "TIFF":
            raise RuntimeError(f"Unexpected dev preview format: {preview_image.format}")
        if preview_image.mode != "RGBA" or preview_image.size != (4096, 4096):
            raise RuntimeError(
                f"Unexpected dev preview master layout: {preview_image.mode} {preview_image.size}"
            )
        if preview_image.getchannel("A").getbbox() is None:
            raise RuntimeError(f"Refusing fully transparent dev preview master: {master_preview}")
        if ImageOps.grayscale(preview_image.convert("RGB")).getbbox() is None:
            raise RuntimeError(f"Refusing blank dev preview master: {master_preview}")

    converted_dir = preview_tmb.parent
    copied = 0
    for filename in DEV_PREVIEW_FILENAMES:
        source = converted_dir / filename
        if not source.exists() or source.stat().st_size <= 0:
            raise FileNotFoundError(f"Missing converted dev preview texture: {source}")
        if source.stat().st_mtime < source_stamp_time:
            raise RuntimeError(f"Refusing stale converted dev preview texture: {source}")
        shutil.copy2(source, DEV_PACKAGE_DIR / filename)
        copied += 1
    return copied


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
    required_package_paths = (
        source_dir / "_GTVR_WRAITH_DEV.txt",
        source_dir / f"{DEV_AIRCRAFT_NAME}.tmb",
        source_dir / MAP_PANEL_DIR_NAME / f"{MAP_PANEL_DIR_NAME}.tmb",
        source_dir / ROTOR_ANIMATION_DIR_NAME / f"{ROTOR_ANIMATION_DIR_NAME}.tmb",
        *(source_dir / filename for filename in DEV_PREVIEW_FILENAMES),
    )
    missing_package_paths = [
        path for path in required_package_paths if not path.exists() or path.stat().st_size <= 0
    ]
    if missing_package_paths:
        missing = ", ".join(str(path.relative_to(source_dir)) for path in missing_package_paths)
        raise RuntimeError(
            f"Refusing to install incomplete dev package {source_dir}; missing or empty: {missing}"
        )
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
    parser.add_argument(
        "--use-converted-previews",
        action="store_true",
        help="Validate and package the fresh converter-rendered dev previews instead of preserving installed previews.",
    )
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
            result = run_converter(args.converter_timeout, args.use_converted_previews)
            if result != 0:
                return result

        if args.assemble_package:
            assert_fresh_converted_tmb(args.allow_stale_tmb)
            core.assemble_package(args)
            if args.use_converted_previews:
                if args.allow_stale_tmb:
                    raise RuntimeError("Fresh converted previews cannot be used with --allow-stale-tmb.")
                converted_previews = install_converted_dev_previews()
                print(
                    "Dev previews: "
                    f"validated the 4096px rotor-inclusive converter render and packaged {converted_previews} fresh preview textures."
                )
            else:
                preserved_previews = preserve_installed_dev_previews(args.user_root)
            if not args.use_converted_previews and preserved_previews:
                print(
                    "Dev previews: "
                    f"preserved {preserved_previews} accepted installed preview textures."
                )
            map_panel_dir = write_dev_map_panel_option()
            print(f"Dev centre map: packaged independent panel {map_panel_dir.name} using {MAP_PANEL_TEXTURE}.ttx.")
            rotor_option_dir = write_dev_rotor_animation_option()
            mode = "probe" if ROTOR_ANIMATION_PROBE_ONLY else "complete assemblies"
            print(
                f"Dev rotors: packaged independent runtime animation option "
                f"{rotor_option_dir.name} using {mode}."
            )
            copied_surface_textures = copy_dev_auxiliary_textures()
            print(f"Dev cockpit materials: packaged {copied_surface_textures} auxiliary surface textures.")
            hidden_clickspots = patch_dev_controls_tmd(DEV_PACKAGE_DIR / "controls.tmd")
            if hidden_clickspots:
                print(f"Dev controls: hid {hidden_clickspots} inherited EC135 cockpit click/handle visuals.")
            display_state_updates = 0
            for state_path in DEV_PACKAGE_DIR.glob(f"{DEV_AIRCRAFT_NAME}_*.tmd"):
                display_state_updates += force_dev_stock_display_state(state_path)
            if display_state_updates:
                print(f"Dev displays: forced {display_state_updates} PFD/ND state inputs on.")
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
