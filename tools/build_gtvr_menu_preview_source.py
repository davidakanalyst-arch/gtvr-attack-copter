from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "menu-previews"
DEFAULT_SOURCE_ROOT = ROOT / "tools" / "vendor" / "gtvr_menu_preview_source" / "aircraft"
DEFAULT_USER_DIR = ROOT / "tools" / "vendor" / "gtvr_menu_preview_user"
MODEL_NAME = "gtvr_menu_preview"
DISPLAY_NAME = "GTVR Menu Preview"
PREVIEW_VARIANTS = {
    "black": ASSET_DIR / "gtvr_attack_black_preview.png",
    "camo": ASSET_DIR / "gtvr_attack_camo_preview.png",
    "desert": ASSET_DIR / "gtvr_attack_desert_preview.png",
}

sys.path.insert(0, str(ROOT / "tools"))
import build_gtvr_repaint_source as repaint_source  # noqa: E402
import build_gtvr_source_project as aircraft_source  # noqa: E402


def write_model_tmc(path: Path, variant_names: list[str]) -> None:
    large_textures = "\n".join(f"                                    {name}_preview_color" for name in variant_names)
    small_textures = "\n".join(f"                                    {name}_preview_small_color" for name in variant_names)
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


def copy_preview_assets(out_aircraft_dir: Path, variant_names: list[str]) -> None:
    for name in variant_names:
        source = PREVIEW_VARIANTS[name]
        if not source.exists():
            raise FileNotFoundError(f"Missing menu preview source image: {source}")

        image = Image.open(source).convert("RGBA")
        for suffix, size in (("", (2048, 2048)), ("_small", (256, 256))):
            resized = image.resize(size, Image.Resampling.LANCZOS)
            color_path = out_aircraft_dir / f"{name}_preview{suffix}_color.png"
            alpha_path = out_aircraft_dir / f"{name}_preview{suffix}_color_alpha.png"
            resized.convert("RGB").save(color_path)
            resized.getchannel("A").save(alpha_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Aerofly converter source for GTVR menu preview images.")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--user-dir", type=Path, default=DEFAULT_USER_DIR)
    args = parser.parse_args()

    out_aircraft_dir = args.source_root / MODEL_NAME
    if out_aircraft_dir.exists():
        shutil.rmtree(out_aircraft_dir)
    out_aircraft_dir.mkdir(parents=True, exist_ok=True)

    variant_names = sorted(PREVIEW_VARIANTS)
    materials = {
        f"{name}_preview": {"shader": "standard exterior", "base": (80, 72, 58)}
        for name in variant_names
    }
    materials.update(
        {
            f"{name}_preview_small": {"shader": "standard exterior", "base": (80, 72, 58)}
            for name in variant_names
        }
    )

    aircraft_source.ensure_runtime_resources(args.source_root)
    aircraft_source.MATERIALS = {
        name: {"shader": settings["shader"], "color": settings["base"]}
        for name, settings in materials.items()
    }

    geometries = repaint_source.build_dummy_geometry(materials)
    aircraft_source.write_aircraft_tmc(out_aircraft_dir / f"{MODEL_NAME}.tmc", MODEL_NAME, DISPLAY_NAME)
    aircraft_source.write_minimal_tmd(out_aircraft_dir / f"{MODEL_NAME}.tmd", sorted(geometries))
    aircraft_source.write_tgi(out_aircraft_dir / f"{MODEL_NAME}.tgi", geometries)
    write_model_tmc(out_aircraft_dir / "model.tmc", variant_names)
    aircraft_source.write_root_converter_config(args.source_root / "config.tmc", args.source_root, args.user_dir)
    copy_preview_assets(out_aircraft_dir, variant_names)

    print(f"Wrote GTVR menu preview source project: {out_aircraft_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
