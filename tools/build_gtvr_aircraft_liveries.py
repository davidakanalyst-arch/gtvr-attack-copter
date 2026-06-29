from __future__ import annotations

import argparse
import shutil
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
MENU_PREVIEW_DIR = ROOT / "assets" / "menu-previews"
sys.path.insert(0, str(ROOT / "tools"))

import build_gtvr_repaint_source as repaint_source  # noqa: E402
import build_gtvr_source_project as aircraft_source  # noqa: E402


MODEL_NAME = "gtvr_aircraft_liveries"
DISPLAY_NAME = "GTVR Aircraft Livery Library"
DEFAULT_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_aircraft_liveries_source" / "aircraft"
DEFAULT_USER_DIR = ROOT / "tools" / "vendor" / "gtvr_aircraft_liveries_user"
DEFAULT_COMPILED_DIR = DEFAULT_USER_DIR / "aircraft" / MODEL_NAME
DEFAULT_LIVERY_ROOT = ROOT / "Liveries"
STOCK_AIRCRAFT_ROOT = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Aerofly FS 4 Flight Simulator\aircraft"
)


@dataclass(frozen=True)
class Variant:
    key: str
    label: str
    f15e_base: tuple[int, int, int]
    mb339_base: tuple[int, int, int]
    lj45_base: tuple[int, int, int]
    c90gtx_base: tuple[int, int, int]


@dataclass(frozen=True)
class AircraftLivery:
    key: str
    aircraft_folder: str
    source_repaint: str
    theme: str
    target_prefix: str
    display_prefix: str
    texture_bases: tuple[str, ...]
    variants: tuple[str, ...]
    requirements: str | None = None


VARIANTS = (
    Variant("black", "Black", (9, 11, 13), (12, 13, 12), (12, 13, 14), (14, 13, 10)),
    Variant("camo", "Camo", (44, 57, 49), (39, 52, 42), (58, 65, 50), (79, 75, 46)),
    Variant("desert", "Desert", (151, 127, 82), (145, 119, 74), (154, 126, 76), (150, 119, 65)),
    Variant("ruby_red", "Ruby Red", (93, 4, 18), (93, 4, 18), (128, 6, 24), (128, 6, 24)),
    Variant("gold_bling", "Gold Bling", (176, 126, 24), (176, 126, 24), (176, 126, 24), (196, 146, 32)),
)

MB339_PREVIEW_SOURCES = {
    "black": MENU_PREVIEW_DIR / "gtvr_assault_black_source.jpg",
    "camo": MENU_PREVIEW_DIR / "gtvr_assault_camo_source.jpg",
    "desert": MENU_PREVIEW_DIR / "gtvr_assault_desert_source.jpg",
}
LJ45_PREVIEW_SOURCES = {
    "ruby_red": MENU_PREVIEW_DIR / "gtvr_ruby_red_learjet_source.jpg",
}
C90GTX_PREVIEW_SOURCES = {
    "gold_bling": MENU_PREVIEW_DIR / "gtvr_gold_bling_kingair_source.jpg",
}
VARIANT_BY_KEY = {variant.key: variant for variant in VARIANTS}

AIRCRAFT = (
    AircraftLivery(
        key="f15e",
        aircraft_folder="f15e",
        source_repaint="splinter",
        theme="strike",
        target_prefix="gtvr_strike",
        display_prefix="GTVR Strike",
        texture_bases=(
            "mapone",
            "maptwo",
            "mapthree",
            "mapfour",
            "mapfive",
            "mapsix",
            "mapseven",
            "mapeight",
            "mapnine",
        ),
        variants=("black", "camo", "desert"),
    ),
    AircraftLivery(
        key="mb339",
        aircraft_folder="mb339",
        source_repaint="new_zealand",
        theme="assault",
        target_prefix="gtvr_assault",
        display_prefix="GTVR Assault",
        texture_bases=("fuselage", "decals", "tank", "outer_tank", "pylon"),
        variants=("black", "camo", "desert"),
        requirements=" decals_none nose_cone load_tip_tanks tail_antenna ",
    ),
    AircraftLivery(
        key="lj45",
        aircraft_folder="lj45",
        source_repaint="black_red",
        theme="ruby",
        target_prefix="gtvr",
        display_prefix="GTVR",
        texture_bases=("learjet_exterior_001", "learjet_exterior_002"),
        variants=("ruby_red",),
    ),
    AircraftLivery(
        key="c90gtx",
        aircraft_folder="c90gtx",
        source_repaint="red_black",
        theme="bling",
        target_prefix="gtvr",
        display_prefix="GTVR",
        texture_bases=("ka_ext_001", "ka_ext_002"),
        variants=("gold_bling",),
    ),
)


def material_name(aircraft: AircraftLivery, variant: Variant, texture_base: str) -> str:
    return f"{aircraft.key}_{aircraft.theme}_{variant.key}_{texture_base}"


def preview_name(aircraft: AircraftLivery, variant: Variant, small: bool = False) -> str:
    suffix = "preview_small" if small else "preview"
    return f"{aircraft.key}_{aircraft.theme}_{variant.key}_{suffix}"


def variants_for(aircraft: AircraftLivery) -> tuple[Variant, ...]:
    return tuple(VARIANT_BY_KEY[key] for key in aircraft.variants)


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf") if bold else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf") if bold else Path(r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def blend(a: tuple[int, int, int], b: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    return tuple(int(a[index] * (1.0 - alpha) + b[index] * alpha) for index in range(3))


def rgba(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return (*color, alpha)


def draw_gradient(image: Image.Image, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for y in range(height):
        t = y / max(height - 1, 1)
        draw.line((0, y, width, y), fill=blend(top, bottom, t))


def draw_panel_grid(draw: ImageDraw.ImageDraw, size: int, color: tuple[int, int, int]) -> None:
    major = blend(color, (255, 255, 255), 0.13)
    minor = blend(color, (0, 0, 0), 0.17)
    for step in range(256, size, 256):
        draw.line((step, 0, step, size), fill=major, width=2)
        draw.line((0, step, size, step), fill=major, width=2)
    for step in range(128, size, 256):
        draw.line((step, 0, step, size), fill=minor, width=1)
        draw.line((0, step, size, step), fill=minor, width=1)


def draw_fasteners(draw: ImageDraw.ImageDraw, size: int, color: tuple[int, int, int]) -> None:
    dot = blend(color, (255, 255, 255), 0.24)
    for x in range(80, size, 160):
        for y in range(80, size, 160):
            if (x // 160 + y // 160) % 2:
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=dot)


def polygon_overlay(image: Image.Image, points: list[tuple[int, int]], fill: tuple[int, int, int], alpha: int) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).polygon(points, fill=rgba(fill, alpha))
    image.alpha_composite(overlay)


def line_overlay(
    image: Image.Image,
    xy: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    width: int,
    alpha: int,
) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).line(xy, fill=rgba(fill, alpha), width=width)
    image.alpha_composite(overlay)


def draw_rotated_text(
    image: Image.Image,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    angle: float,
    alpha: int = 255,
) -> None:
    bbox = font.getbbox(text)
    width = bbox[2] - bbox[0] + 32
    height = bbox[3] - bbox[1] + 32
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.text((16 - bbox[0], 16 - bbox[1]), text, font=font, fill=rgba(fill, alpha))
    rotated = layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    image.alpha_composite(rotated, xy)


def draw_strike_texture(path: Path, texture_base: str, base: tuple[int, int, int]) -> None:
    size = 2048
    image = Image.new("RGBA", (size, size), (*base, 255))
    draw_gradient(image, blend(base, (255, 255, 255), 0.08), blend(base, (0, 0, 0), 0.18))
    draw = ImageDraw.Draw(image)

    cold = (95, 187, 218)
    pale = (205, 217, 219)
    gunmetal = blend(base, (0, 0, 0), 0.38)
    dark = blend(base, (0, 0, 0), 0.58)

    for offset in range(-400, 2400, 520):
        polygon_overlay(
            image,
            [(offset, 90), (offset + 610, 20), (offset + 710, 145), (offset + 120, 220)],
            pale,
            108,
        )
        polygon_overlay(
            image,
            [(offset - 120, 1510), (offset + 470, 1390), (offset + 570, 1520), (offset, 1650)],
            cold,
            130,
        )

    for index, y in enumerate((380, 680, 1180, 1480)):
        line_overlay(image, (-120, y, 2160, y - 270), cold if index % 2 else pale, 18, 155)
        line_overlay(image, (-80, y + 70, 2120, y - 190), dark, 42, 145)

    for x in (300, 900, 1500):
        draw.arc((x, 300, x + 480, 780), 18, 305, fill=rgba(cold, 155), width=9)
        draw.line((x + 240, 230, x + 240, 850), fill=rgba(cold, 115), width=4)
        draw.line((x - 60, 540, x + 540, 540), fill=rgba(cold, 115), width=4)

    draw_panel_grid(draw, size, base)
    draw_fasteners(draw, size, base)

    title = load_font(104, bold=True)
    code = load_font(92, bold=True)
    small = load_font(44, bold=True)
    map_hash = sum(ord(char) for char in texture_base)
    if map_hash % 3 == 0:
        draw_rotated_text(image, (190, 1230), "GTVR STRIKE", title, pale, -8, 230)
    elif map_hash % 3 == 1:
        draw.text((1260, 260), "ST-15", fill=rgba(pale, 235), font=code)
        draw.text((1262, 354), "LOW OBS / FAST ENTRY", fill=rgba(cold, 190), font=small)
    else:
        draw.text((180, 1710), "NO STEP", fill=rgba(blend(base, (255, 255, 255), 0.28), 190), font=small)
        draw.text((1320, 1660), "LASER / STRIKE", fill=rgba(cold, 190), font=small)

    if "eight" in texture_base or "nine" in texture_base:
        draw.rectangle((1120, 180, 1770, 300), fill=rgba(gunmetal, 210))
        draw.text((1160, 194), "GTVR", fill=rgba(pale, 245), font=code)

    image.convert("RGB").save(path)


def draw_assault_texture(path: Path, texture_base: str, base: tuple[int, int, int]) -> None:
    size = 2048
    image = Image.new("RGBA", (size, size), (*base, 255))
    draw_gradient(image, blend(base, (255, 255, 255), 0.06), blend(base, (0, 0, 0), 0.22))
    draw = ImageDraw.Draw(image)

    amber = (228, 154, 46)
    hazard = (226, 194, 72)
    soot = blend(base, (0, 0, 0), 0.62)
    olive = blend(base, (65, 88, 56), 0.45)
    offwhite = (210, 205, 183)

    for x in range(-260, 2400, 430):
        polygon_overlay(
            image,
            [(x, 0), (x + 260, 0), (x + 170, 2048), (x - 90, 2048)],
            olive if x % 2 else soot,
            115,
        )

    for y in (260, 760, 1290, 1690):
        draw.rectangle((0, y, size, y + 84), fill=rgba(soot, 210))
        for x in range(-60, size, 180):
            polygon_overlay(
                image,
                [(x, y), (x + 88, y), (x + 18, y + 84), (x - 70, y + 84)],
                hazard,
                210,
            )

    for x, y in ((220, 430), (1160, 410), (440, 1320), (1390, 1280)):
        draw.rectangle((x, y, x + 430, y + 280), outline=rgba(amber, 170), width=8)
        draw.line((x + 35, y + 225, x + 385, y + 45), fill=rgba(amber, 150), width=7)

    draw_panel_grid(draw, size, base)
    draw_fasteners(draw, size, base)

    title = load_font(96, bold=True)
    code = load_font(102, bold=True)
    small = load_font(42, bold=True)
    map_hash = sum(ord(char) for char in texture_base)
    if map_hash % 3 == 0:
        draw.text((220, 1460), "GTVR ASSAULT", fill=rgba(offwhite, 232), font=title)
        draw.text((228, 1560), "CLOSE SUPPORT", fill=rgba(amber, 210), font=small)
    elif map_hash % 3 == 1:
        draw.text((1320, 250), "AS-39", fill=rgba(offwhite, 235), font=code)
        draw.text((1323, 350), "LOW LEVEL", fill=rgba(amber, 205), font=small)
    else:
        draw_rotated_text(image, (160, 920), "ASSAULT", title, amber, -6, 208)
        draw.text((1460, 1720), "GTVR", fill=rgba(offwhite, 225), font=code)

    if "tank" in texture_base or "pylon" in texture_base:
        draw.rectangle((80, 820, 1960, 990), fill=rgba(soot, 225))
        for x in range(140, 1900, 220):
            draw.polygon([(x, 855), (x + 95, 905), (x, 955)], fill=rgba(amber, 230))

    image.convert("RGB").save(path)


def draw_ruby_texture(path: Path, texture_base: str, base: tuple[int, int, int]) -> None:
    size = 2048
    image = Image.new("RGBA", (size, size), (*base, 255))
    draw_gradient(image, blend(base, (255, 255, 255), 0.16), blend(base, (0, 0, 0), 0.28))
    draw = ImageDraw.Draw(image)

    ruby_dark = blend(base, (0, 0, 0), 0.55)
    ruby_shadow = blend(base, (0, 0, 0), 0.72)
    ruby_gloss = blend(base, (255, 255, 255), 0.24)
    champagne = (222, 183, 94)
    warm_white = (235, 229, 205)
    smoke = (36, 24, 26)

    for y in (310, 670, 1030, 1390, 1750):
        line_overlay(image, (-180, y + 105, 2240, y - 90), ruby_gloss, 18, 70)
        line_overlay(image, (-220, y + 165, 2180, y - 145), ruby_dark, 44, 125)

    for y in (610, 1180):
        line_overlay(image, (-120, y, 2160, y - 180), champagne, 14, 235)
        line_overlay(image, (-120, y + 46, 2160, y - 134), warm_white, 5, 205)

    for offset in range(-320, 2200, 520):
        polygon_overlay(
            image,
            [(offset, 0), (offset + 220, 0), (offset + 510, 2048), (offset + 260, 2048)],
            ruby_shadow,
            62,
        )

    draw_panel_grid(draw, size, base)
    draw_fasteners(draw, size, base)

    title = load_font(104, bold=True)
    code = load_font(78, bold=True)
    small = load_font(42, bold=True)
    if texture_base.endswith("001"):
        draw.rectangle((120, 710, 1940, 870), fill=rgba(smoke, 165))
        for x in range(250, 1700, 135):
            draw.rounded_rectangle((x, 735, x + 70, 820), radius=14, fill=rgba((170, 217, 226), 230))
            draw.rounded_rectangle((x + 7, 742, x + 63, 813), radius=11, outline=rgba(warm_white, 180), width=3)
        draw.text((1320, 250), "GTVR RUBY", fill=rgba(warm_white, 235), font=title)
        draw.text((1325, 360), "LEARJET 45", fill=rgba(champagne, 215), font=small)
        draw.rectangle((210, 1510, 780, 1620), outline=rgba(warm_white, 230), width=9)
        draw.text((245, 1530), "G-VRTR", fill=rgba(warm_white, 235), font=code)
    else:
        draw.rectangle((250, 260, 1820, 440), fill=rgba(ruby_shadow, 165))
        draw.text((320, 295), "RUBY RED", fill=rgba(warm_white, 235), font=title)
        draw.text((330, 405), "GTVR EXECUTIVE", fill=rgba(champagne, 220), font=small)
        draw.line((240, 760, 1780, 540), fill=rgba(champagne, 245), width=16)
        draw.line((260, 815, 1800, 595), fill=rgba(warm_white, 195), width=5)
        draw.ellipse((1430, 1260, 1810, 1640), outline=rgba(champagne, 200), width=10)
        draw.text((1518, 1390), "45", fill=rgba(warm_white, 230), font=title)

    image.convert("RGB").save(path)


def draw_bling_texture(path: Path, texture_base: str, base: tuple[int, int, int]) -> None:
    size = 2048
    image = Image.new("RGBA", (size, size), (*base, 255))
    draw_gradient(image, blend(base, (255, 255, 255), 0.22), blend(base, (0, 0, 0), 0.22))
    draw = ImageDraw.Draw(image)

    bright_gold = (246, 196, 58)
    pale_gold = (255, 226, 130)
    bronze = blend(base, (92, 48, 8), 0.45)
    smoked = (18, 15, 11)
    wine = (95, 14, 20)
    ivory = (244, 235, 204)

    for offset in range(-360, 2400, 460):
        polygon_overlay(
            image,
            [(offset, 0), (offset + 180, 0), (offset + 520, 2048), (offset + 310, 2048)],
            pale_gold,
            56,
        )
        polygon_overlay(
            image,
            [(offset + 80, 0), (offset + 180, 0), (offset + 40, 2048), (offset - 80, 2048)],
            bronze,
            74,
        )

    for y in (430, 880, 1330):
        line_overlay(image, (-160, y, 2160, y - 250), smoked, 54, 185)
        line_overlay(image, (-160, y + 58, 2160, y - 192), wine, 20, 210)
        line_overlay(image, (-160, y + 88, 2160, y - 162), pale_gold, 10, 240)

    for x, y in ((170, 360), (1120, 310), (430, 1260), (1280, 1210)):
        draw.ellipse((x, y, x + 430, y + 260), outline=rgba(pale_gold, 150), width=8)
        draw.line((x + 65, y + 210, x + 370, y + 45), fill=rgba(pale_gold, 120), width=7)

    draw_panel_grid(draw, size, base)
    draw_fasteners(draw, size, base)

    title = load_font(110, bold=True)
    code = load_font(86, bold=True)
    small = load_font(42, bold=True)
    if texture_base.endswith("001"):
        draw.rectangle((1050, 210, 1870, 360), fill=rgba(smoked, 170))
        draw.text((1090, 230), "GTVR BLING", fill=rgba(ivory, 240), font=code)
        draw.text((1092, 318), "GOLD EXECUTIVE", fill=rgba(pale_gold, 215), font=small)
        for x in range(260, 1220, 165):
            draw.ellipse((x, 700, x + 76, 782), fill=rgba((38, 61, 73), 225), outline=rgba(ivory, 190), width=4)
        draw.text((210, 1550), "G-BLNG", fill=rgba(ivory, 238), font=code)
    else:
        draw.rectangle((250, 250, 1700, 440), fill=rgba(smoked, 170))
        draw.text((315, 285), "GOLD BLING", fill=rgba(ivory, 240), font=title)
        draw.line((180, 760, 1860, 530), fill=rgba(pale_gold, 245), width=18)
        draw.line((190, 820, 1870, 590), fill=rgba(wine, 220), width=26)
        draw.line((190, 854, 1870, 624), fill=rgba(ivory, 185), width=6)
        draw.ellipse((1380, 1230, 1810, 1660), outline=rgba(pale_gold, 200), width=10)
        draw.text((1480, 1385), "KA", fill=rgba(ivory, 232), font=title)

    image.convert("RGB").save(path)


def write_texture(path: Path, aircraft: AircraftLivery, variant: Variant, texture_base: str) -> None:
    if aircraft.key == "c90gtx":
        draw_bling_texture(path, texture_base, variant.c90gtx_base)
    elif aircraft.key == "lj45":
        draw_ruby_texture(path, texture_base, variant.lj45_base)
    elif aircraft.theme == "strike":
        base = variant.f15e_base
        draw_strike_texture(path, texture_base, base)
    else:
        base = variant.mb339_base
        draw_assault_texture(path, texture_base, base)


def draw_reflection(source: Image.Image, opacity: float = 0.22) -> Image.Image:
    reflection = source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    alpha = reflection.getchannel("A").point(lambda value: int(value * opacity))
    width, height = source.size
    fade = Image.new("L", (width, height), 0)
    fade_draw = ImageDraw.Draw(fade)
    for y in range(height):
        fade_draw.line((0, y, width, y), fill=max(0, int(255 * (1 - y / max(height * 0.72, 1)))))
    alpha = Image.composite(alpha, Image.new("L", (width, height), 0), fade)
    reflection.putalpha(alpha)
    return reflection.filter(ImageFilter.GaussianBlur(radius=1.2))


def draw_asset_reflection(source: Image.Image, opacity: float = 0.20) -> Image.Image:
    reflection = source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    alpha = reflection.getchannel("A").point(lambda value: int(value * opacity))
    width, height = reflection.size
    fade = Image.new("L", (width, height), 0)
    fade_draw = ImageDraw.Draw(fade)
    for y in range(height):
        fade_draw.line((0, y, width, y), fill=max(0, int(255 * (1 - y / max(height * 0.78, 1)))))
    alpha = Image.composite(alpha, Image.new("L", (width, height), 0), fade)
    reflection.putalpha(alpha)
    return reflection.filter(ImageFilter.GaussianBlur(radius=0.75))


def draw_f15e_preview(path: Path, variant: Variant, small: bool = False) -> None:
    size = 256 if small else 2048
    scale = size / 2048
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    craft = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(craft)

    def p(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [(int(x * scale), int(y * scale)) for x, y in points]

    base = variant.f15e_base
    pale = (205, 217, 219)
    cold = (85, 183, 219)
    dark = blend(base, (0, 0, 0), 0.55)

    body = p([(170, 930), (700, 770), (1290, 785), (1770, 875), (1875, 940), (1725, 1005), (720, 1020)])
    nose = p([(130, 935), (275, 875), (250, 998)])
    wing = p([(750, 910), (1280, 585), (1435, 620), (1045, 960)])
    wing2 = p([(770, 985), (1350, 1230), (1490, 1190), (1025, 965)])
    tail = p([(1520, 805), (1655, 520), (1745, 830)])
    stab = p([(1485, 970), (1790, 1060), (1560, 1090)])

    draw.polygon(wing2, fill=rgba(blend(base, (255, 255, 255), 0.08), 235))
    draw.polygon(wing, fill=rgba(blend(base, (0, 0, 0), 0.12), 245))
    draw.polygon(body, fill=rgba(base, 255))
    draw.polygon(nose, fill=rgba(blend(base, (255, 255, 255), 0.08), 255))
    draw.polygon(tail, fill=rgba(blend(base, (0, 0, 0), 0.04), 255))
    draw.polygon(stab, fill=rgba(blend(base, (0, 0, 0), 0.2), 245))
    draw.ellipse(tuple(int(v * scale) for v in (540, 795, 760, 910)), fill=rgba((42, 77, 96), 230))
    draw.line(tuple(int(v * scale) for v in (305, 950, 1775, 910)), fill=rgba(dark, 220), width=max(2, int(20 * scale)))
    draw.line(tuple(int(v * scale) for v in (420, 910, 1560, 735)), fill=rgba(cold, 215), width=max(1, int(17 * scale)))
    draw.line(tuple(int(v * scale) for v in (540, 1010, 1560, 1190)), fill=rgba(pale, 200), width=max(1, int(14 * scale)))
    draw.line(tuple(int(v * scale) for v in (980, 785, 1695, 880)), fill=rgba(pale, 170), width=max(1, int(9 * scale)))
    draw.line(tuple(int(v * scale) for v in (1260, 590, 1428, 625)), fill=rgba(cold, 220), width=max(1, int(20 * scale)))
    font_big = load_font(max(12, int(88 * scale)), bold=True)
    font_small = load_font(max(10, int(58 * scale)), bold=True)
    draw.text((int(900 * scale), int(830 * scale)), "ST-15", fill=rgba(pale, 245), font=font_big)
    draw.text((int(1180 * scale), int(915 * scale)), "GTVR", fill=rgba(pale, 232), font=font_small)

    image.alpha_composite(craft)
    reflection = draw_reflection(craft, opacity=0.2)
    image.alpha_composite(reflection, (0, int(1030 * scale)))
    save_rgba_with_alpha_sidecar(image, path)


def draw_mb339_preview(path: Path, variant: Variant, small: bool = False) -> None:
    size = 256 if small else 2048
    scale = size / 2048
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    craft = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(craft)

    def p(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [(int(x * scale), int(y * scale)) for x, y in points]

    base = variant.mb339_base
    amber = (228, 154, 46)
    hazard = (226, 194, 72)
    dark = blend(base, (0, 0, 0), 0.55)
    pale = (215, 210, 188)

    body = p([(155, 1000), (335, 900), (915, 840), (1490, 890), (1815, 1015), (1420, 1085), (460, 1085)])
    nose = p([(105, 1012), (245, 935), (250, 1070)])
    wing = p([(830, 1000), (1325, 710), (1460, 760), (1110, 1040)])
    wing2 = p([(850, 1070), (1370, 1250), (1490, 1210), (1050, 1040)])
    tail = p([(1510, 875), (1645, 590), (1745, 910)])
    tank_left = tuple(int(v * scale) for v in (600, 1110, 900, 1170))
    tank_right = tuple(int(v * scale) for v in (1180, 1105, 1570, 1175))

    draw.polygon(wing2, fill=rgba(blend(base, (0, 0, 0), 0.05), 238))
    draw.polygon(wing, fill=rgba(blend(base, (255, 255, 255), 0.08), 245))
    draw.polygon(body, fill=rgba(base, 255))
    draw.polygon(nose, fill=rgba(blend(base, (255, 255, 255), 0.06), 255))
    draw.polygon(tail, fill=rgba(blend(base, (0, 0, 0), 0.02), 255))
    draw.ellipse(tank_left, fill=rgba(dark, 240))
    draw.ellipse(tank_right, fill=rgba(dark, 240))
    draw.ellipse(tuple(int(v * scale) for v in (455, 842, 790, 955)), fill=rgba((55, 88, 99), 220))
    draw.rectangle(tuple(int(v * scale) for v in (290, 1038, 1625, 1080)), fill=rgba(dark, 220))
    for x in range(350, 1480, 190):
        draw.polygon(p([(x, 1038), (x + 86, 1038), (x + 16, 1080), (x - 70, 1080)]), fill=rgba(hazard, 230))
    draw.line(tuple(int(v * scale) for v in (410, 980, 1525, 900)), fill=rgba(amber, 230), width=max(1, int(18 * scale)))
    draw.line(tuple(int(v * scale) for v in (540, 1070, 1450, 1235)), fill=rgba(amber, 190), width=max(1, int(12 * scale)))
    font_big = load_font(max(12, int(82 * scale)), bold=True)
    font_small = load_font(max(10, int(54 * scale)), bold=True)
    draw.text((int(900 * scale), int(910 * scale)), "AS-39", fill=rgba(pale, 242), font=font_big)
    draw.text((int(1160 * scale), int(1008 * scale)), "GTVR", fill=rgba(pale, 230), font=font_small)

    image.alpha_composite(craft)
    reflection = draw_reflection(craft, opacity=0.18)
    image.alpha_composite(reflection, (0, int(1110 * scale)))
    save_rgba_with_alpha_sidecar(image, path)


def save_rgba_with_alpha_sidecar(image: Image.Image, color_path: Path) -> None:
    color_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(color_path)
    image.getchannel("A").save(color_path.with_name(f"{color_path.stem}_alpha.png"))


def remove_light_preview_background(image: Image.Image) -> Image.Image:
    return remove_connected_background(
        image,
        lambda r, g, b, _x, _y, _w, _h: max(r, g, b) > 180 and max(r, g, b) - min(r, g, b) < 42,
    )


def remove_connected_background(image: Image.Image, is_background_candidate) -> Image.Image:
    rgba_image = image.convert("RGBA")
    pixels = rgba_image.load()
    width, height = rgba_image.size
    visited = bytearray(width * height)
    background = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def index(x: int, y: int) -> int:
        return y * width + x

    def try_enqueue(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= width or y >= height:
            return
        idx = index(x, y)
        if visited[idx]:
            return
        visited[idx] = 1
        r, g, b, _alpha = pixels[x, y]
        if is_background_candidate(r, g, b, x, y, width, height):
            background[idx] = 1
            queue.append((x, y))

    for x in range(width):
        try_enqueue(x, 0)
        try_enqueue(x, height - 1)
    for y in range(height):
        try_enqueue(0, y)
        try_enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        try_enqueue(x + 1, y)
        try_enqueue(x - 1, y)
        try_enqueue(x, y + 1)
        try_enqueue(x, y - 1)

    for y in range(height):
        for x in range(width):
            idx = index(x, y)
            if background[idx]:
                r, g, b, _alpha = pixels[x, y]
                pixels[x, y] = (r, g, b, 0)
    return rgba_image


def remove_white_preview_fill(image: Image.Image) -> Image.Image:
    pixels = image.load()
    width, height = image.size
    protected_top = int(height * 0.34)
    candidates: set[tuple[int, int]] = set()
    for y in range(protected_top, height):
        for x in range(width):
            r, g, b, alpha = pixels[x, y]
            if alpha == 0:
                continue
            brightness = max(r, g, b)
            contrast = max(r, g, b) - min(r, g, b)
            if brightness > 232 and contrast < 34:
                candidates.add((x, y))

    visited: set[tuple[int, int]] = set()
    for start in list(candidates):
        if start in visited:
            continue
        stack = [start]
        component: list[tuple[int, int]] = []
        visited.add(start)
        while stack:
            x, y = stack.pop()
            component.append((x, y))
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                point = (nx, ny)
                if point in candidates and point not in visited:
                    visited.add(point)
                    stack.append(point)
        if len(component) < 900:
            continue
        for x, y in component:
            r, g, b, _alpha = pixels[x, y]
            pixels[x, y] = (r, g, b, 0)
    return image


def soften_alpha(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(radius=0.55))
    image.putalpha(alpha)
    return image


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value > 8 else 0).getbbox()
    if bbox is None:
        return (0, 0, image.width, image.height)
    return bbox


def place_preview_image(source: Image.Image, size: int) -> Image.Image:
    bbox = alpha_bbox(source)
    crop = source.crop(bbox)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    target_width = int(size * 0.88)
    target_height = int(size * 0.74)
    scale = min(target_width / crop.width, target_height / crop.height)
    scaled_size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
    crop = crop.resize(scaled_size, Image.Resampling.LANCZOS)
    x = (size - scaled_size[0]) // 2
    y = int(size * 0.52 - scaled_size[1] / 2)
    canvas.alpha_composite(crop, (x, max(0, y)))
    return canvas


def place_preview_with_generated_reflection(source: Image.Image, size: int, split: float = 0.60) -> Image.Image:
    bbox = alpha_bbox(source)
    crop = source.crop(bbox)
    aircraft = crop.crop((0, 0, crop.width, max(1, int(crop.height * split))))
    aircraft_bbox = alpha_bbox(aircraft)
    aircraft = aircraft.crop(aircraft_bbox)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    target_width = int(size * 0.88)
    target_height = int(size * 0.48)
    scale = min(target_width / aircraft.width, target_height / aircraft.height)
    scaled_size = (max(1, int(aircraft.width * scale)), max(1, int(aircraft.height * scale)))
    aircraft = aircraft.resize(scaled_size, Image.Resampling.LANCZOS)

    x = (size - scaled_size[0]) // 2
    y = int(size * 0.49 - scaled_size[1] / 2)
    canvas.alpha_composite(aircraft, (x, max(0, y)))

    reflection = draw_asset_reflection(aircraft, opacity=0.22)
    reflection_y = max(0, y + scaled_size[1] - int(size * 0.035))
    canvas.alpha_composite(reflection, (x, reflection_y))
    return canvas


def write_asset_preview(path: Path, source_path: Path, variant: Variant, small: bool) -> bool:
    if not source_path.exists():
        return False
    source = Image.open(source_path)
    cutout = remove_light_preview_background(source)
    if variant.key in {"camo", "desert", "ruby_red", "gold_bling"}:
        cutout = remove_white_preview_fill(cutout)
    cutout = soften_alpha(cutout)
    size = 256 if small else 2048
    if variant.key == "gold_bling":
        save_rgba_with_alpha_sidecar(place_preview_with_generated_reflection(cutout, size, split=0.58), path)
        return True
    save_rgba_with_alpha_sidecar(place_preview_image(cutout, size), path)
    return True


def write_preview(path: Path, aircraft: AircraftLivery, variant: Variant, small: bool = False) -> None:
    if aircraft.key == "mb339" and write_asset_preview(path, MB339_PREVIEW_SOURCES[variant.key], variant, small):
        return
    if aircraft.key == "lj45" and write_asset_preview(path, LJ45_PREVIEW_SOURCES[variant.key], variant, small):
        return
    if aircraft.key == "c90gtx" and write_asset_preview(path, C90GTX_PREVIEW_SOURCES[variant.key], variant, small):
        return
    if aircraft.key == "f15e":
        draw_f15e_preview(path, variant, small=small)
    elif aircraft.key == "lj45":
        draw_f15e_preview(path, variant, small=small)
    else:
        draw_mb339_preview(path, variant, small=small)


def write_model_tmc(path: Path, texture_names: list[str]) -> None:
    large = [name for name in texture_names if not name.endswith("_preview_small")]
    small = [name for name in texture_names if name.endswith("_preview_small")]
    large_textures = "\n".join(f"                                    {name}_color" for name in large)
    small_textures = "\n".join(f"                                    {name}_color" for name in small)
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
{large_textures}
                                              ]>
                    >
                    <[convert_texture_settings][element][1]
                        <[int32][MaxTextureSize][256]>
                        <[float64][BumpMapScaling][1.0]>
                        <[list_string8][Files][
{small_textures}
                                              ]>
                    >
                >
            >
        >
    >
>
"""
    path.write_text(text, encoding="utf-8")


def build_source(source_root: Path, user_dir: Path) -> None:
    out_aircraft_dir = source_root / MODEL_NAME
    if out_aircraft_dir.exists():
        shutil.rmtree(out_aircraft_dir)
    out_aircraft_dir.mkdir(parents=True, exist_ok=True)
    aircraft_source.ensure_runtime_resources(source_root)

    materials: dict[str, dict[str, object]] = {}
    texture_names: list[str] = []
    for aircraft in AIRCRAFT:
        for variant in variants_for(aircraft):
            for texture_base in aircraft.texture_bases:
                name = material_name(aircraft, variant, texture_base)
                materials[name] = {"shader": "standard exterior", "base": (96, 96, 96)}
                texture_names.append(name)
            for small in (False, True):
                name = preview_name(aircraft, variant, small=small)
                materials[name] = {"shader": "standard exterior", "base": (96, 96, 96)}
                texture_names.append(name)

    aircraft_source.MATERIALS = {
        name: {"shader": settings["shader"], "color": settings["base"]}
        for name, settings in materials.items()
    }
    geometries = repaint_source.build_dummy_geometry(materials)
    aircraft_source.write_aircraft_tmc(out_aircraft_dir / f"{MODEL_NAME}.tmc", MODEL_NAME, DISPLAY_NAME)
    aircraft_source.write_minimal_tmd(out_aircraft_dir / f"{MODEL_NAME}.tmd", sorted(geometries))
    aircraft_source.write_tgi(out_aircraft_dir / f"{MODEL_NAME}.tgi", geometries)
    write_model_tmc(out_aircraft_dir / "model.tmc", texture_names)
    aircraft_source.write_root_converter_config(source_root / "config.tmc", source_root, user_dir)

    for aircraft in AIRCRAFT:
        for variant in variants_for(aircraft):
            for texture_base in aircraft.texture_bases:
                write_texture(
                    out_aircraft_dir / f"{material_name(aircraft, variant, texture_base)}_color.png",
                    aircraft,
                    variant,
                    texture_base,
                )
            write_preview(out_aircraft_dir / f"{preview_name(aircraft, variant)}_color.png", aircraft, variant)
            write_preview(
                out_aircraft_dir / f"{preview_name(aircraft, variant, small=True)}_color.png",
                aircraft,
                variant,
                small=True,
            )

    print(f"Wrote livery source project: {out_aircraft_dir}")
    print(f"Converter output target from config: {user_dir / 'aircraft' / MODEL_NAME}")


def option_tmc(display_name: str, requirements: str | None = None) -> str:
    requirements_line = f"    <[string8][Requirements][{requirements}]>\n" if requirements else ""
    return f"""<[file][][]
  <[object][][]
    <[string8][Description][{display_name}]>
    <[string8][Type][repaint]>
{requirements_line}  >
>
"""


def remove_target_folder(path: Path, livery_root: Path) -> None:
    resolved_root = livery_root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"Refusing to remove folder outside livery root: {resolved_path}") from exc
    if resolved_path.exists():
        shutil.rmtree(resolved_path)


def copy_required(compiled_dir: Path, source_name: str, target: Path) -> None:
    source = compiled_dir / source_name
    if not source.exists():
        raise FileNotFoundError(f"Missing converted texture: {source}")
    shutil.copy2(source, target)


def assemble_liveries(compiled_dir: Path, livery_root: Path, stock_root: Path) -> None:
    livery_root.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for aircraft in AIRCRAFT:
        source_repaint = stock_root / aircraft.aircraft_folder / aircraft.source_repaint
        if not source_repaint.exists():
            raise FileNotFoundError(f"Missing stock repaint folder: {source_repaint}")

        for variant in variants_for(aircraft):
            target_dir = livery_root / aircraft.aircraft_folder / f"{aircraft.target_prefix}_{variant.key}"
            remove_target_folder(target_dir, livery_root)
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_repaint, target_dir)

            display_name = f"{aircraft.display_prefix} {variant.label}"
            (target_dir / "option.tmc").write_text(option_tmc(display_name, aircraft.requirements), encoding="utf-8")

            for texture_base in aircraft.texture_bases:
                copy_required(
                    compiled_dir,
                    f"{material_name(aircraft, variant, texture_base)}_color.ttx",
                    target_dir / f"{texture_base}_color.ttx",
                )

            copy_required(compiled_dir, f"{preview_name(aircraft, variant)}_color.ttx", target_dir / "preview.ttx")
            copy_required(
                compiled_dir,
                f"{preview_name(aircraft, variant, small=True)}_color.ttx",
                target_dir / "preview_small.ttx",
            )
            created.append(target_dir)

    print("Created livery folders:")
    for path in created:
        print(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GTVR F-15E and MB-339 livery packages.")
    parser.add_argument("command", choices=("build-source", "assemble"), nargs="?", default="build-source")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--user-dir", type=Path, default=DEFAULT_USER_DIR)
    parser.add_argument("--compiled-dir", type=Path, default=DEFAULT_COMPILED_DIR)
    parser.add_argument("--livery-root", type=Path, default=DEFAULT_LIVERY_ROOT)
    parser.add_argument("--stock-root", type=Path, default=STOCK_AIRCRAFT_ROOT)
    args = parser.parse_args()

    if args.command == "build-source":
        build_source(args.source_root, args.user_dir)
    else:
        assemble_liveries(args.compiled_dir, args.livery_root, args.stock_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
