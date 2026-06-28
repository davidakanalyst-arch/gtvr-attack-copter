from __future__ import annotations

import argparse
import ctypes
import subprocess
import time
from pathlib import Path

from find_aerofly_converter import find_converter


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USERFOLDER = ROOT / "tools" / "vendor" / "converter_launch"


def quote_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/") + "/"


def read_log_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, PermissionError):
        return ""


def click_convert_button(timeout: float, x: int, y: int) -> bool:
    user32 = ctypes.windll.user32
    wm_lbuttondown = 0x0201
    wm_lbuttonup = 0x0202
    mk_lbutton = 0x0001
    deadline = time.time() + timeout

    while time.time() < deadline:
        hwnd = user32.FindWindowW(None, "Aerofly FS 4 Aircraft Converter")
        if hwnd:
            time.sleep(5.0)
            lparam = (y << 16) | x
            user32.PostMessageW(hwnd, wm_lbuttondown, mk_lbutton, lparam)
            user32.PostMessageW(hwnd, wm_lbuttonup, 0, lparam)
            return True
        time.sleep(0.25)

    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Aerofly FS 4 aircraft converter GUI non-interactively.")
    parser.add_argument("model", help="Source aircraft folder name passed as model='<name>'.")
    parser.add_argument("source_root", type=Path, help="Folder passed as dir='<source_root>/'.")
    parser.add_argument(
        "--userfolder",
        type=Path,
        default=DEFAULT_USERFOLDER,
        help="Converter launch/log folder. The converter's source-root config controls output.",
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--button-x", type=int, default=82)
    parser.add_argument("--button-y", type=int, default=533)
    args = parser.parse_args()

    converters = find_converter()
    if not converters:
        print("No Aerofly aircraft converter executable found.")
        return 2

    converter = converters[0]
    args.userfolder.mkdir(parents=True, exist_ok=True)
    log_path = args.userfolder / "tm_aircraft_converter.log"
    if log_path.exists():
        try:
            log_path.unlink()
        except PermissionError:
            pass

    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    command = [
        str(converter),
        f"-userfolder='{quote_path(args.userfolder)}'",
        f"model='{args.model}'",
        f"dir='{quote_path(args.source_root)}'",
    ]
    process = subprocess.Popen(command, cwd=str(converter.parent))
    clicked = click_convert_button(timeout=30.0, x=args.button_x, y=args.button_y)

    completed = False
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if "all done" in read_log_text(log_path):
            completed = True
            break
        if process.poll() is not None:
            break
        time.sleep(1.0)

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()

    print(f"converter={converter}")
    print(f"clicked={clicked}")
    print(f"completed={completed}")
    print(f"log={log_path}")
    return 0 if clicked and completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
