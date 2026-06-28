from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_gtvr_source_project as aircraft_source


ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "gtvr_repaint_textures"
DISPLAY_NAME = "GTVR Repaint Textures"
DEFAULT_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_repaint_source" / "aircraft"
DEFAULT_USER_DIR = ROOT / "tools" / "vendor" / "gtvr_repaint_test_user"

REPAINT_MATERIALS = {
    "ext01_fuselage": {
        "shader": "standard exterior",
        "base": (17, 20, 20),
        "accent": (73, 91, 58),
    },
    "ext02_fuselage": {
        "shader": "standard exterior",
        "base": (11, 13, 14),
        "accent": (92, 20, 18),
    },
    "ext03_fuselage": {
        "shader": "standard exterior",
        "base": (21, 23, 22),
        "accent": (45, 56, 40),
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


def draw_diagonal_stripes(draw: ImageDraw.ImageDraw, size: int, color: tuple[int, int, int]) -> None:
    for offset in range(-size, size * 2, 240):
        points = [
            (offset, size),
            (offset + 86, size),
            (offset + size + 86, 0),
            (offset + size, 0),
        ]
        draw.polygon(points, fill=color)


def draw_cross_stripes(draw: ImageDraw.ImageDraw, size: int, red: tuple[int, int, int]) -> None:
    for offset in range(-size, size * 2, 360):
        points = [
            (offset, 0),
            (offset + 62, 0),
            (offset - size + 62, size),
            (offset - size, size),
        ]
        draw.polygon(points, fill=(82, 12, 10))

    for offset in range(-size, size * 2, 420):
        points = [
            (offset, size),
            (offset + 120, size),
            (offset + size + 120, 0),
            (offset + size, 0),
        ]
        draw.polygon(points, fill=red)


def draw_panel_grid(draw: ImageDraw.ImageDraw, size: int) -> None:
    line = (45, 50, 48)
    for step in range(256, size, 256):
        draw.line((step, 0, step, size), fill=line, width=4)
        draw.line((0, step, size, step), fill=line, width=4)
    for step in range(128, size, 256):
        draw.line((step, 0, step, size), fill=(27, 31, 31), width=2)
        draw.line((0, step, size, step), fill=(27, 31, 31), width=2)


def write_texture(path: Path, material_name: str, base: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    size = 2048
    image = Image.new("RGB", (size, size), base)
    draw = ImageDraw.Draw(image)
    draw_panel_grid(draw, size)
    draw_cross_stripes(draw, size, (148, 17, 12))
    draw_diagonal_stripes(draw, size, (95, 14, 10))

    draw.rectangle((0, 0, size, 120), fill=(9, 11, 11))
    draw.rectangle((0, size - 140, size, size), fill=(10, 12, 12))

    if material_name == "ext01_fuselage":
        draw.rectangle((110, 150, 720, 430), fill=accent)
        draw.rectangle((1320, 1260, 1920, 1600), fill=(29, 34, 33))
    elif material_name == "ext02_fuselage":
        draw.rectangle((0, 870, size, 1010), fill=(66, 77, 52))
        draw.rectangle((110, 145, 520, 520), outline=(130, 19, 15), width=22)
    else:
        for x in range(260, 1900, 360):
            draw.rectangle((x, 580, x + 86, 1480), fill=(8, 10, 10))
        draw.rectangle((230, 260, 1810, 410), fill=accent)

    small_font = load_font(82)
    stencil = (178, 184, 176)
    draw.text((1320, 170), "GT-04", fill=stencil, font=small_font)
    draw.text((150, 1710), "GTVR", fill=(82, 92, 75), font=small_font)

    image.save(path)


def write_model_tmc(path: Path) -> None:
    texture_names = "\n".join(f"                                    {name}_color" for name in REPAINT_MATERIALS)
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


def build_dummy_geometry() -> dict[str, dict[str, aircraft_source.Patch]]:
    patch_map: dict[str, aircraft_source.Patch] = {}
    for index, material_name in enumerate(REPAINT_MATERIALS):
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
    args = parser.parse_args()

    out_aircraft_dir = args.source_root / MODEL_NAME
    if out_aircraft_dir.exists():
        shutil.rmtree(out_aircraft_dir)
    out_aircraft_dir.mkdir(parents=True, exist_ok=True)

    aircraft_source.ensure_runtime_resources(args.source_root)
    aircraft_source.MATERIALS = {
        name: {"shader": settings["shader"], "color": settings["base"]}
        for name, settings in REPAINT_MATERIALS.items()
    }

    geometries = build_dummy_geometry()
    aircraft_source.write_aircraft_tmc(out_aircraft_dir / f"{MODEL_NAME}.tmc", MODEL_NAME, DISPLAY_NAME)
    aircraft_source.write_minimal_tmd(out_aircraft_dir / f"{MODEL_NAME}.tmd", sorted(geometries))
    aircraft_source.write_tgi(out_aircraft_dir / f"{MODEL_NAME}.tgi", geometries)
    write_model_tmc(out_aircraft_dir / "model.tmc")
    aircraft_source.write_root_converter_config(args.source_root / "config.tmc", args.source_root, args.user_dir)

    for material_name, settings in REPAINT_MATERIALS.items():
        write_texture(
            out_aircraft_dir / f"{material_name}_color.png",
            material_name,
            settings["base"],
            settings["accent"],
        )

    print(f"Wrote repaint source project: {out_aircraft_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
