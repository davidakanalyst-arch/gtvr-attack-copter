from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_gtvr_source_project as aircraft_source


ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "gtvr_repaint_textures"
DISPLAY_NAME = "GTVR Repaint Textures"
DEFAULT_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_repaint_source" / "aircraft"
DEFAULT_USER_DIR = ROOT / "tools" / "vendor" / "gtvr_repaint_test_user"

REPAINT_VARIANTS = {
    "olive": {
        "materials": {
            "ext01_fuselage": {"shader": "standard exterior", "base": (12, 15, 15)},
            "ext02_fuselage": {"shader": "standard exterior", "base": (9, 11, 12)},
            "ext03_fuselage": {"shader": "standard exterior", "base": (14, 16, 15)},
        },
        "style": {
            "gradient_lift": (48, 56, 49),
            "panel_colors": [(18, 24, 23), (25, 31, 29), (49, 62, 45), (31, 36, 32)],
            "feature_panel": (28, 34, 31),
            "belt": (46, 56, 39),
            "bar": (40, 51, 37),
            "bay": (7, 9, 9),
        },
    },
    "black": {
        "materials": {
            "ext01_fuselage": {"shader": "standard exterior", "base": (4, 5, 5)},
            "ext02_fuselage": {"shader": "standard exterior", "base": (3, 4, 4)},
            "ext03_fuselage": {"shader": "standard exterior", "base": (5, 5, 5)},
        },
        "style": {
            "gradient_lift": (24, 25, 25),
            "panel_colors": [(8, 9, 9), (13, 14, 14), (20, 21, 21), (28, 29, 29)],
            "feature_panel": (13, 14, 14),
            "belt": (12, 13, 13),
            "bar": (14, 15, 15),
            "bay": (4, 5, 5),
        },
    },
}


def load_font(size: int) -> ImageFont.ImageFont:
    font_candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def blend(base: tuple[int, int, int], overlay: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    return tuple(int(base[index] * (1.0 - alpha) + overlay[index] * alpha) for index in range(3))


def draw_translucent_polygon(
    image: Image.Image,
    points: list[tuple[int, int]],
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None = None,
    alpha: int = 255,
) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.polygon(points, fill=(*fill, alpha), outline=(*outline, alpha) if outline else None)
    image.alpha_composite(overlay)


def draw_gradient(image: Image.Image, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for y in range(height):
        t = y / max(height - 1, 1)
        color = blend(top, bottom, t)
        draw.line((0, y, width, y), fill=color)


def draw_armor_panels(image: Image.Image, seed: int, panel_colors: list[tuple[int, int, int]]) -> None:
    rng = random.Random(seed)
    size = image.size[0]

    fixed_panels = [
        [(90, 130), (820, 90), (950, 380), (240, 455)],
        [(1040, 205), (1920, 155), (1840, 520), (1110, 590)],
        [(80, 1180), (780, 1095), (980, 1450), (210, 1605)],
        [(1060, 1250), (1900, 1160), (1960, 1540), (1160, 1660)],
        [(370, 690), (930, 610), (1110, 860), (520, 960)],
    ]
    for index, points in enumerate(fixed_panels):
        color = panel_colors[index % len(panel_colors)]
        draw_translucent_polygon(image, points, color, outline=(47, 54, 51), alpha=208)

    for _ in range(15):
        x = rng.randrange(-120, size - 260)
        y = rng.randrange(70, size - 260)
        width = rng.randrange(260, 620)
        height = rng.randrange(95, 260)
        skew = rng.randrange(-120, 160)
        points = [
            (x, y),
            (x + width, y + rng.randrange(-30, 30)),
            (x + width + skew, y + height),
            (x + skew, y + height + rng.randrange(-20, 45)),
        ]
        color = rng.choice(panel_colors)
        draw_translucent_polygon(image, points, color, outline=(38, 45, 43), alpha=rng.randrange(92, 150))


def draw_attack_slashes(image: Image.Image, seed: int) -> None:
    rng = random.Random(seed + 1000)
    size = image.size[0]
    colors = [(132, 16, 12), (174, 26, 18), (86, 12, 10)]
    for index, offset in enumerate(range(-size, size * 2, 510)):
        width = 92 if index % 3 else 138
        points = [
            (offset, size),
            (offset + width, size),
            (offset + size + width, 0),
            (offset + size, 0),
        ]
        draw_translucent_polygon(image, points, colors[index % len(colors)], alpha=205 if index % 3 else 235)

    for _ in range(9):
        x = rng.randrange(-260, size)
        y = rng.randrange(100, size - 200)
        width = rng.randrange(340, 760)
        points = [
            (x, y),
            (x + width, y - 85),
            (x + width + 52, y - 20),
            (x + 52, y + 68),
        ]
        draw_translucent_polygon(image, points, rng.choice(colors), alpha=138)


def draw_panel_grid(draw: ImageDraw.ImageDraw, size: int) -> None:
    line = (37, 43, 41)
    for step in range(256, size, 256):
        draw.line((step, 0, step, size), fill=line, width=3)
        draw.line((0, step, size, step), fill=line, width=3)
    for step in range(128, size, 256):
        draw.line((step, 0, step, size), fill=(25, 30, 29), width=1)
        draw.line((0, step, size, step), fill=(25, 30, 29), width=1)


def draw_fasteners(draw: ImageDraw.ImageDraw, size: int) -> None:
    for x in range(64, size, 128):
        for y in range(64, size, 128):
            if (x // 128 + y // 128) % 3:
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(57, 63, 59))


def draw_chevrons(draw: ImageDraw.ImageDraw, size: int) -> None:
    red = (151, 18, 13)
    dark = (8, 10, 10)
    for y in (164, 1772):
        for x in range(90, size - 160, 190):
            draw.polygon([(x, y), (x + 70, y + 36), (x, y + 72)], fill=red)
            draw.polygon([(x + 44, y), (x + 114, y + 36), (x + 44, y + 72)], fill=dark)


def draw_sensor_marks(draw: ImageDraw.ImageDraw) -> None:
    red = (150, 22, 16)
    pale = (156, 164, 154)
    for cx, cy, radius in ((1640, 360, 88), (360, 1460, 70), (1710, 1710, 54)):
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=red, width=8)
        draw.line((cx - radius - 35, cy, cx + radius + 35, cy), fill=red, width=5)
        draw.line((cx, cy - radius - 35, cx, cy + radius + 35), fill=red, width=5)
        draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), outline=pale, width=4)


def draw_stencils(draw: ImageDraw.ImageDraw, size: int) -> None:
    stencil_large = load_font(104)
    stencil_medium = load_font(76)
    stencil_small = load_font(42)
    pale = (172, 179, 168)
    subdued = (86, 95, 83)
    red = (145, 20, 15)
    low_vis_red = (101, 13, 10)

    for x, y, label in (
        (1180, 190, "GT-04"),
        (150, 1660, "GTVR"),
        (1530, 1460, "04"),
    ):
        draw.text((x, y), label, fill=pale, font=stencil_large)

    for x, y in ((520, 1540), (930, 470)):
        draw.text((x + 4, y + 4), "ATTACK COPTER", fill=(16, 18, 17), font=stencil_medium)
        draw.text((x, y), "ATTACK COPTER", fill=low_vis_red, font=stencil_medium)

    for x, y, label in (
        (165, 520, "NO STEP"),
        (1210, 610, "LIFT"),
        (880, 1740, "ARM"),
        (1480, 950, "FUEL"),
    ):
        draw.text((x, y), label, fill=subdued, font=stencil_small)
        draw.rectangle((x - 22, y + 10, x - 4, y + 28), fill=red)

    draw.rectangle((132, 132, 430, 188), outline=red, width=8)
    draw.line((132, 188, 430, 132), fill=red, width=8)


def write_texture(
    path: Path,
    material_name: str,
    base: tuple[int, int, int],
    style: dict[str, object],
) -> None:
    size = 2048
    seed = sum(ord(char) for char in material_name)
    image = Image.new("RGBA", (size, size), (*base, 255))
    draw_gradient(
        image,
        blend(base, (0, 0, 0), 0.15),
        blend(base, style["gradient_lift"], 0.22),
    )
    draw_armor_panels(image, seed, style["panel_colors"])
    draw_attack_slashes(image, seed)
    draw = ImageDraw.Draw(image)
    draw_panel_grid(draw, size)
    draw_fasteners(draw, size)
    draw_chevrons(draw, size)
    draw_sensor_marks(draw)

    if material_name == "ext01_fuselage":
        draw.rectangle((0, 0, size, 118), fill=(7, 9, 9))
        draw.rectangle((0, size - 130, size, size), fill=(8, 10, 10))
        draw.polygon([(80, 700), (520, 620), (610, 840), (160, 930)], fill=style["feature_panel"])
    elif material_name == "ext02_fuselage":
        draw.rectangle((0, 850, size, 990), fill=style["belt"])
        draw.rectangle((105, 145, 520, 520), outline=(116, 16, 13), width=20)
    else:
        for x in range(230, 1900, 330):
            draw.rectangle((x, 560, x + 78, 1490), fill=style["bay"])
        draw.rectangle((210, 250, 1840, 390), fill=style["bar"])

    draw_stencils(draw, size)

    image.convert("RGB").save(path)


def write_model_tmc(path: Path, materials: dict[str, dict[str, object]]) -> None:
    texture_names = "\n".join(f"                                    {name}_color" for name in materials)
    text = f"""<[file][][]
    <[convert_model_settings][][]
        <[float64][BumpMapScaling][1]>
        <[list_convert_target_settings][Targets][]
            <[convert_target_settings][element][0]
                <[string8][Target][Desktop]>
                <[list_string8][Repaints][]>
                <[list_convert_texture_settings][FileOptions][]
                    <[convert_texture_settings][element][0]
                        <[int32][MaxTextureSize][2048]>
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


def build_dummy_geometry(materials: dict[str, dict[str, object]]) -> dict[str, dict[str, aircraft_source.Patch]]:
    patch_map: dict[str, aircraft_source.Patch] = {}
    for index, material_name in enumerate(materials):
        x = float(index) * 0.2
        patch_map[material_name] = aircraft_source.Patch(
            material_name=material_name,
            vertices=[
                x,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                x + 0.1,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                1.0,
                0.0,
                x,
                0.1,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                1.0,
            ],
            indices=[0, 1, 2],
            face_attributes=[0],
        )
    return {"RepaintProbe": patch_map}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build source PNGs for the safe GTVR tactical repaint.")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--user-dir", type=Path, default=DEFAULT_USER_DIR)
    parser.add_argument("--variant", choices=sorted(REPAINT_VARIANTS), default="olive")
    args = parser.parse_args()

    variant = REPAINT_VARIANTS[args.variant]
    materials = variant["materials"]
    style = variant["style"]

    out_aircraft_dir = args.source_root / MODEL_NAME
    if out_aircraft_dir.exists():
        shutil.rmtree(out_aircraft_dir)
    out_aircraft_dir.mkdir(parents=True, exist_ok=True)

    aircraft_source.ensure_runtime_resources(args.source_root)
    aircraft_source.MATERIALS = {
        name: {"shader": settings["shader"], "color": settings["base"]}
        for name, settings in materials.items()
    }

    geometries = build_dummy_geometry(materials)
    aircraft_source.write_aircraft_tmc(out_aircraft_dir / f"{MODEL_NAME}.tmc", MODEL_NAME, DISPLAY_NAME)
    aircraft_source.write_minimal_tmd(out_aircraft_dir / f"{MODEL_NAME}.tmd", sorted(geometries))
    aircraft_source.write_tgi(out_aircraft_dir / f"{MODEL_NAME}.tgi", geometries)
    write_model_tmc(out_aircraft_dir / "model.tmc", materials)
    aircraft_source.write_root_converter_config(args.source_root / "config.tmc", args.source_root, args.user_dir)

    for material_name, settings in materials.items():
        write_texture(
            out_aircraft_dir / f"{material_name}_color.png",
            material_name,
            settings["base"],
            style,
        )

    print(f"Wrote {args.variant} repaint source project: {out_aircraft_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
