from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path


STABLE_NAME = "gtvr_wraith_ec135_core"
DEV_NAME = "gtvr_wraith_dev"
DEV_DISPLAY_NAME = "GTVR Wraith Dev"
DEV_ICAO = "GTWD"
DEFAULT_USER_ROOT = Path.home() / "Documents" / "Aerofly FS 4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def replace_one(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not patch {label} in restored dev TMC.")
    return updated


def assert_aircraft_child(path: Path, aircraft_root: Path, expected_name: str) -> None:
    if path.name != expected_name or path.parent.resolve() != aircraft_root.resolve():
        raise RuntimeError(f"Refusing unexpected aircraft path: {path}")


def rename_stable_files(package_dir: Path) -> None:
    for child in list(package_dir.iterdir()):
        if child.is_file() and child.name.startswith(STABLE_NAME):
            suffix = child.name[len(STABLE_NAME) :]
            child.rename(package_dir / f"{DEV_NAME}{suffix}")


def patch_dev_identity(package_dir: Path) -> None:
    tmc = package_dir / f"{DEV_NAME}.tmc"
    text = tmc.read_text(encoding="utf-8", errors="replace")
    text = replace_one(
        text,
        r"<\[stringt8c\]\[ICAO\]\[[^\]]+\]>",
        f"<[stringt8c][ICAO][{DEV_ICAO}]>",
        "ICAO",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[DisplayName\]\[[^\]]+\]>",
        f"<[string8][DisplayName][{DEV_DISPLAY_NAME}]>",
        "DisplayName",
    )
    text = replace_one(
        text,
        r"<\[string8\]\[DisplayNameFull\]\[[^\]]+\]>",
        f"<[string8][DisplayNameFull][{DEV_DISPLAY_NAME}]>",
        "DisplayNameFull",
    )
    tmc.write_text(text, encoding="utf-8")

    stable_marker = package_dir / "_GTVR_WRAITH_EC135_CORE.txt"
    if stable_marker.exists():
        stable_marker.unlink()
    (package_dir / "_GTVR_WRAITH_DEV.txt").write_text(
        "\n".join(
            [
                DEV_DISPLAY_NAME,
                "",
                "Restored directly from the accepted installed GTVR Wraith stable aircraft.",
                "Only the folder, aircraft filenames, ICAO and display name use the dev identity.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def validate_restored_dev(package_dir: Path, stable_tmb_hash: str) -> None:
    required = [
        package_dir / f"{DEV_NAME}.tmc",
        package_dir / f"{DEV_NAME}.tmb",
        package_dir / f"{DEV_NAME}.tmq",
        package_dir / f"{DEV_NAME}_clean.tmd",
        package_dir / f"{DEV_NAME}_cold.tmd",
        package_dir / f"{DEV_NAME}_landing.tmd",
        package_dir / f"{DEV_NAME}_start.tmd",
        package_dir / f"{DEV_NAME}_takeoff.tmd",
        package_dir / "controls.tmd",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Restored dev package is missing: " + ", ".join(missing))
    if sha256(package_dir / f"{DEV_NAME}.tmb") != stable_tmb_hash:
        raise RuntimeError("Restored dev TMB does not match stable.")
    text = (package_dir / f"{DEV_NAME}.tmc").read_text(encoding="utf-8", errors="replace")
    for fragment in (
        f"<[stringt8c][ICAO][{DEV_ICAO}]>",
        f"<[string8][DisplayName][{DEV_DISPLAY_NAME}]>",
        f"<[string8][DisplayNameFull][{DEV_DISPLAY_NAME}]>",
    ):
        if fragment not in text:
            raise RuntimeError(f"Restored dev identity is missing: {fragment}")


def restore(user_root: Path, force: bool) -> Path:
    aircraft_root = (user_root / "aircraft").resolve()
    stable = aircraft_root / STABLE_NAME
    dev = aircraft_root / DEV_NAME
    staging = aircraft_root / f".{DEV_NAME}.restore_tmp"
    assert_aircraft_child(stable, aircraft_root, STABLE_NAME)
    assert_aircraft_child(dev, aircraft_root, DEV_NAME)
    assert_aircraft_child(staging, aircraft_root, f".{DEV_NAME}.restore_tmp")

    stable_tmb = stable / f"{STABLE_NAME}.tmb"
    if not stable_tmb.exists():
        raise FileNotFoundError(f"Missing installed stable aircraft: {stable_tmb}")
    stable_tmb_hash = sha256(stable_tmb)
    if dev.exists() and not force:
        raise FileExistsError(f"Dev install exists; rerun with --force: {dev}")

    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(stable, staging)
    rename_stable_files(staging)
    patch_dev_identity(staging)
    validate_restored_dev(staging, stable_tmb_hash)

    if dev.exists():
        shutil.rmtree(dev)
    staging.rename(dev)
    validate_restored_dev(dev, stable_tmb_hash)
    return dev


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore installed Wraith stable back over Wraith Dev.")
    parser.add_argument("--user-root", type=Path, default=DEFAULT_USER_ROOT)
    parser.add_argument("--force", action="store_true", help="Replace the installed dev aircraft.")
    args = parser.parse_args()
    try:
        restored = restore(args.user_root, args.force)
        print(f"Restored stable aircraft to dev: {restored}")
    except (FileExistsError, FileNotFoundError, RuntimeError) as error:
        print(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
