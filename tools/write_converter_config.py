from __future__ import annotations

import argparse
from pathlib import Path


def quote_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/") + "/"


def write_config(
    config_dir: Path,
    intermediate_dir: Path,
    user_dir: Path,
    temp_dir: Path | None = None,
    aircraft: str = "",
    mobile_aircraft: str = "",
) -> Path:
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.tmc"
    convert_settings = ""
    if aircraft or mobile_aircraft:
        convert_settings = (
            "    <[convert_convert_settings][][]>\n"
            f"        <[string8][AircraftDesktop][{aircraft}]>\n"
            f"        <[string8][AircraftMobile][{mobile_aircraft}]>\n"
            "    >\n"
        )
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
        <[string8][TempFolder][{quote_path(temp_dir or config_dir)}]>
    >
{convert_settings.rstrip()}
>
"""
    config_path.write_text(text, encoding="utf-8")
    return config_path


def write_convert_job(config_dir: Path, aircraft: str, mobile_aircraft: str = "") -> Path:
    config_dir.mkdir(parents=True, exist_ok=True)
    convert_path = config_dir / "convert.tmc"
    text = f"""<[file][][]
    <[convert_convert_settings][][]>
        <[string8][AircraftDesktop][{aircraft}]>
        <[string8][AircraftMobile][{mobile_aircraft}]>
    >
>
"""
    convert_path.write_text(text, encoding="utf-8")
    return convert_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write an explicit Aerofly aircraft converter config.tmc.")
    parser.add_argument("config_dir", type=Path)
    parser.add_argument("intermediate_dir", type=Path)
    parser.add_argument("--aircraft", help="Set AircraftDesktop in config.tmc.")
    parser.add_argument("--temp-dir", type=Path, help="Folder used by the converter for convert.tmc jobs.")
    parser.add_argument(
        "--write-convert-job",
        action="store_true",
        help="Also write the experimental convert.tmc job file.",
    )
    parser.add_argument(
        "--user-dir",
        type=Path,
        default=Path.home() / "Documents" / "Aerofly FS 4",
    )
    args = parser.parse_args()
    config_path = write_config(
        args.config_dir,
        args.intermediate_dir,
        args.user_dir,
        temp_dir=args.temp_dir,
        aircraft=args.aircraft or "",
    )
    print(config_path)
    if args.aircraft and args.write_convert_job:
        convert_path = write_convert_job(args.config_dir, args.aircraft)
        print(convert_path)


if __name__ == "__main__":
    main()
