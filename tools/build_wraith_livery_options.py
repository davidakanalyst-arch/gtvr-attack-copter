from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageOps

import build_gtvr_repaint_source as repaint_source
import build_gtvr_source_project as aircraft_source


ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "gtvr_wraith_liveries"
DISPLAY_NAME = "GTVR Wraith Liveries"
DEFAULT_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_wraith_liveries_source" / "aircraft"
DEFAULT_SOURCE_DIR = DEFAULT_SOURCE_ROOT / MODEL_NAME
DEFAULT_BUILD_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_liveries_build_user"
DEFAULT_LAUNCH_USER = ROOT / "tools" / "vendor" / "gtvr_wraith_liveries_launch"
DEFAULT_COMPILED_DIR = DEFAULT_BUILD_USER / "aircraft" / MODEL_NAME
SOURCE_STAMP_NAME = "_GTVR_WRAITH_LIVERIES_SOURCE_STAMP.txt"
BODY_TEXTURE_TARGETS = (
    "gtvr_wraith_livery_body_1.ttx",
    "gtvr_wraith_livery_body_2.ttx",
)
LEGACY_REPAINT_DIRS = ("adac", "drf", "german_army", "police", "sheriff")


@dataclass(frozen=True)
class Variant:
    key: str
    folder: str
    description: str


VARIANTS = (
    Variant("red_camo", "wraith_red_camo", "Wraith Red Camo"),
    Variant("black", "wraith_black", "Wraith Black"),
)


def body_material_name(variant: Variant, atlas_index: int) -> str:
    return f"wraith_{variant.key}_body_{atlas_index}"


def preview_material_name(variant: Variant, *, small: bool = False) -> str:
    suffix = "preview_small" if small else "preview"
    return f"wraith_{variant.key}_{suffix}"


def source_stamp(source_dir: Path = DEFAULT_SOURCE_DIR) -> Path:
    return source_dir / SOURCE_STAMP_NAME


def converted_tmb(compiled_dir: Path = DEFAULT_COMPILED_DIR) -> Path:
    return compiled_dir / f"{MODEL_NAME}.tmb"


def converted_body_texture(
    variant: Variant,
    atlas_index: int,
    compiled_dir: Path = DEFAULT_COMPILED_DIR,
) -> Path:
    return compiled_dir / f"{body_material_name(variant, atlas_index)}_color.ttx"


def converted_preview_texture(
    variant: Variant,
    *,
    small: bool = False,
    compiled_dir: Path = DEFAULT_COMPILED_DIR,
) -> Path:
    return compiled_dir / f"{preview_material_name(variant, small=small)}_color.ttx"


def material_names() -> tuple[str, ...]:
    names: list[str] = []
    for variant in VARIANTS:
        names.extend(body_material_name(variant, index) for index in (1, 2))
        names.append(preview_material_name(variant))
        names.append(preview_material_name(variant, small=True))
    return tuple(names)


def write_model_tmc(path: Path) -> None:
    large_names: list[str] = []
    small_names: list[str] = []
    for variant in VARIANTS:
        large_names.extend(body_material_name(variant, index) for index in (1, 2))
        large_names.append(preview_material_name(variant))
        small_names.append(preview_material_name(variant, small=True))
    large_textures = "\n".join(f"                                    {name}_color" for name in large_names)
    small_textures = "\n".join(f"                                    {name}_color" for name in small_names)
    path.write_text(
        f"""<[file][][]
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
""",
        encoding="utf-8",
    )


def save_converter_texture(path: Path, image: Image.Image) -> None:
    rgba = image.convert("RGBA")
    rgba.convert("RGB").save(path)
    rgba.getchannel("A").save(path.with_name(f"{path.stem}_alpha.png"))


def paint_mask(source_rgb: Image.Image) -> Image.Image:
    return ImageOps.grayscale(source_rgb).point(
        lambda value: 0
        if value <= 30
        else 255
        if value >= 62
        else round((value - 30) * 255 / 32)
    )


def red_camo_pattern(pattern_path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(pattern_path) as source:
        pattern = source.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    gray = ImageEnhance.Contrast(ImageOps.grayscale(pattern)).enhance(1.18)
    red = ImageOps.colorize(gray, black=(12, 2, 5), white=(166, 28, 42))
    return ImageEnhance.Color(red).enhance(1.16)


def render_variant_atlas(
    source_path: Path,
    pattern_path: Path,
    variant: Variant,
) -> Image.Image:
    with Image.open(source_path) as source_image:
        source_rgba = source_image.convert("RGBA")
    source_rgb = source_rgba.convert("RGB")
    if variant.key == "red_camo":
        pattern = red_camo_pattern(pattern_path, source_rgba.size)
        preserved_detail = ImageEnhance.Color(source_rgb).enhance(0.10)
        preserved_detail = ImageEnhance.Brightness(preserved_detail).enhance(0.42)
        painted_rgb = Image.blend(pattern, preserved_detail, 0.24)
        painted_rgb = ImageEnhance.Contrast(painted_rgb).enhance(1.10)
    elif variant.key == "black":
        detail = ImageEnhance.Contrast(ImageOps.grayscale(source_rgb)).enhance(1.08)
        painted_rgb = ImageOps.colorize(detail, black=(2, 3, 4), white=(31, 34, 37))
        painted_rgb = ImageEnhance.Brightness(painted_rgb).enhance(0.88)
    else:  # pragma: no cover - guarded by the fixed variant table
        raise ValueError(f"Unsupported Wraith livery variant: {variant.key}")

    painted_rgb = Image.composite(painted_rgb, source_rgb, paint_mask(source_rgb))
    painted_rgba = painted_rgb.convert("RGBA")
    painted_rgba.putalpha(source_rgba.getchannel("A"))
    return painted_rgba


def neutral_preview_mask(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    gray = ImageOps.grayscale(rgb)
    saturation = rgb.convert("HSV").getchannel("S")
    neutral = saturation.point(
        lambda value: 255
        if value <= 42
        else 0
        if value >= 104
        else round((104 - value) * 255 / 62)
    )
    visible_midtones = gray.point(
        lambda value: 0
        if value <= 22
        else 255
        if value >= 62
        else round((value - 22) * 255 / 40)
    )
    return ImageChops.multiply(
        image.convert("RGBA").getchannel("A"),
        ImageChops.multiply(neutral, visible_midtones),
    )


def render_variant_preview(master: Image.Image, variant: Variant) -> Image.Image:
    rgba = master.convert("RGBA")
    rgb = rgba.convert("RGB")
    gray = ImageOps.grayscale(rgb)
    if variant.key == "red_camo":
        target = ImageOps.colorize(gray, black=(5, 2, 3), white=(185, 31, 45))
        target = ImageEnhance.Contrast(target).enhance(1.06)
    elif variant.key == "black":
        target = ImageOps.colorize(gray, black=(1, 2, 3), white=(49, 53, 57))
        target = ImageEnhance.Brightness(target).enhance(0.78)
    else:  # pragma: no cover - guarded by the fixed variant table
        raise ValueError(f"Unsupported Wraith preview variant: {variant.key}")
    recolored = Image.composite(target, rgb, neutral_preview_mask(rgba)).convert("RGBA")
    recolored.putalpha(rgba.getchannel("A"))
    return recolored


def write_preview_images(
    preview_master: Path | None,
    source_dir: Path = DEFAULT_SOURCE_DIR,
) -> None:
    if preview_master is None:
        master = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
    else:
        if not preview_master.exists() or preview_master.stat().st_size <= 0:
            raise FileNotFoundError(f"Missing Wraith livery preview master: {preview_master}")
        with Image.open(preview_master) as source_preview:
            master = source_preview.convert("RGBA")
        if master.getchannel("A").getbbox() is None:
            raise RuntimeError(f"Wraith livery preview master is fully transparent: {preview_master}")

    for variant in VARIANTS:
        variant_preview = render_variant_preview(master, variant)
        for small, size in ((False, (2048, 2048)), (True, (256, 256))):
            resized = variant_preview.resize(size, Image.Resampling.LANCZOS)
            output = source_dir / f"{preview_material_name(variant, small=small)}_color.png"
            save_converter_texture(output, resized)


def write_source_stamp(
    source_dir: Path = DEFAULT_SOURCE_DIR,
    *,
    preview_master: Path | None,
) -> Path:
    texture_hashes: list[str] = []
    for texture in sorted(source_dir.glob("*_color.png")):
        digest = hashlib.sha256(texture.read_bytes()).hexdigest()
        texture_hashes.append(f"{texture.name}={digest}")
    stamp = source_stamp(source_dir)
    stamp.write_text(
        "\n".join(
            [
                "GTVR Wraith repaint option source prepared.",
                "base_livery=accepted charcoal/gunmetal Wraith camouflage",
                "variants=wraith_red_camo,wraith_black",
                "preview_source=rotor-inclusive accepted Wraith preview render",
                f"preview_master={preview_master or 'placeholder'}",
                *texture_hashes,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return stamp


def prepare_source(
    source_atlases: tuple[Path, Path],
    pattern_path: Path,
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    build_user: Path = DEFAULT_BUILD_USER,
    preview_master: Path | None = None,
) -> Path:
    if len(source_atlases) != 2 or any(not path.exists() for path in source_atlases):
        raise FileNotFoundError(
            "Missing one or more Wraith source atlases: "
            + ", ".join(str(path) for path in source_atlases)
        )
    if not pattern_path.exists():
        raise FileNotFoundError(f"Missing accepted Wraith camouflage pattern: {pattern_path}")
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True, exist_ok=True)
    aircraft_source.ensure_runtime_resources(source_root)

    materials = {
        name: {"shader": "standard exterior", "base": (24, 24, 24)}
        for name in material_names()
    }
    original_materials = aircraft_source.MATERIALS
    try:
        aircraft_source.MATERIALS = {
            name: {"shader": settings["shader"], "color": settings["base"]}
            for name, settings in materials.items()
        }
        geometries = repaint_source.build_dummy_geometry(materials)
        aircraft_source.write_aircraft_tmc(
            source_dir / f"{MODEL_NAME}.tmc",
            MODEL_NAME,
            DISPLAY_NAME,
        )
        aircraft_source.write_minimal_tmd(
            source_dir / f"{MODEL_NAME}.tmd",
            sorted(geometries),
        )
        aircraft_source.write_tgi(source_dir / f"{MODEL_NAME}.tgi", geometries)
    finally:
        aircraft_source.MATERIALS = original_materials

    write_model_tmc(source_dir / "model.tmc")
    aircraft_source.write_root_converter_config(
        source_root / "config.tmc",
        source_root,
        build_user,
    )
    for variant in VARIANTS:
        for atlas_index, source_atlas in enumerate(source_atlases, start=1):
            output = source_dir / f"{body_material_name(variant, atlas_index)}_color.png"
            save_converter_texture(
                output,
                render_variant_atlas(source_atlas, pattern_path, variant),
            )
    write_preview_images(preview_master if preview_master and preview_master.exists() else None, source_dir)
    write_source_stamp(
        source_dir,
        preview_master=preview_master if preview_master and preview_master.exists() else None,
    )
    return source_dir


def refresh_previews(
    preview_master: Path,
    source_dir: Path = DEFAULT_SOURCE_DIR,
) -> None:
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing prepared Wraith livery source: {source_dir}")
    write_preview_images(preview_master, source_dir)
    write_source_stamp(source_dir, preview_master=preview_master)


def expected_converted_paths(compiled_dir: Path = DEFAULT_COMPILED_DIR) -> tuple[Path, ...]:
    paths: list[Path] = [converted_tmb(compiled_dir)]
    for variant in VARIANTS:
        paths.extend(converted_body_texture(variant, index, compiled_dir) for index in (1, 2))
        paths.append(converted_preview_texture(variant, compiled_dir=compiled_dir))
        paths.append(converted_preview_texture(variant, small=True, compiled_dir=compiled_dir))
    return tuple(paths)


def assert_fresh_conversion(
    *,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    compiled_dir: Path = DEFAULT_COMPILED_DIR,
) -> None:
    stamp = source_stamp(source_dir)
    if not stamp.exists():
        raise FileNotFoundError(f"Missing Wraith livery source stamp: {stamp}")
    missing = [
        path
        for path in expected_converted_paths(compiled_dir)
        if not path.exists() or path.stat().st_size <= 0
    ]
    if missing:
        raise FileNotFoundError(
            "Missing converted Wraith livery outputs: " + ", ".join(str(path) for path in missing)
        )
    stale = [
        path
        for path in expected_converted_paths(compiled_dir)
        if path.stat().st_mtime < stamp.stat().st_mtime
    ]
    if stale:
        raise RuntimeError(
            "Refusing stale Wraith livery outputs: " + ", ".join(str(path) for path in stale)
        )


def remove_legacy_repaints(package_dir: Path) -> tuple[str, ...]:
    removed: list[str] = []
    for name in LEGACY_REPAINT_DIRS:
        repaint_dir = package_dir / name
        if not repaint_dir.exists():
            continue
        option_path = repaint_dir / "option.tmc"
        option_text = option_path.read_text(encoding="utf-8", errors="replace") if option_path.exists() else ""
        if "<[string8][Type][repaint]>" not in option_text:
            raise RuntimeError(f"Refusing to remove non-repaint option: {repaint_dir}")
        shutil.rmtree(repaint_dir)
        removed.append(name)
    return tuple(removed)


def write_option_tmc(path: Path, description: str) -> None:
    path.write_text(
        f"""<[file][][]
  <[object][][]
    <[string8][Description][{description}]>
    <[string8][Type][repaint]>
  >
>
""",
        encoding="utf-8",
    )


def assemble_options(
    package_dir: Path,
    *,
    compiled_dir: Path = DEFAULT_COMPILED_DIR,
) -> tuple[Path, ...]:
    assert_fresh_conversion(compiled_dir=compiled_dir)
    option_dirs: list[Path] = []
    for variant in VARIANTS:
        option_dir = package_dir / variant.folder
        if option_dir.exists():
            shutil.rmtree(option_dir)
        option_dir.mkdir(parents=True)
        write_option_tmc(option_dir / "option.tmc", variant.description)
        for atlas_index, target_name in enumerate(BODY_TEXTURE_TARGETS, start=1):
            shutil.copy2(
                converted_body_texture(variant, atlas_index, compiled_dir),
                option_dir / target_name,
            )
        shutil.copy2(
            converted_preview_texture(variant, compiled_dir=compiled_dir),
            option_dir / "preview.ttx",
        )
        shutil.copy2(
            converted_preview_texture(variant, small=True, compiled_dir=compiled_dir),
            option_dir / "preview_small.ttx",
        )
        option_dirs.append(option_dir)
    return tuple(option_dirs)
