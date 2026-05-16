"""Transparent, click-through crosshair overlay for Windows."""

from __future__ import annotations

import ctypes
import json
import signal
import sys
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
CLICK_THROUGH_STYLE = WS_EX_LAYERED | WS_EX_TRANSPARENT
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
QUIT_HOTKEY_ID = 1
QUIT_VK = 0x58  # X — Ctrl+Shift+X

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.json"
LOCAL_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "local.json"


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def load_config() -> dict:
    path = LOCAL_CONFIG_PATH if LOCAL_CONFIG_PATH.exists() else CONFIG_PATH
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def overlay_hwnd(window: tk.Tk) -> int:
    """HWND used for hit-testing (parent of the Tk widget on Windows)."""
    window.update_idletasks()
    wid = window.winfo_id()
    parent = ctypes.windll.user32.GetParent(wid)
    return parent if parent else wid


def ensure_click_through(window: tk.Tk) -> None:
    """Keep mouse clicks passing through — geometry() resets this on Windows."""
    user32 = ctypes.windll.user32
    hwnd = overlay_hwnd(window)
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if (style & CLICK_THROUGH_STYLE) != CLICK_THROUGH_STYLE:
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | CLICK_THROUGH_STYLE)


def register_quit_hotkey() -> bool:
    user32 = ctypes.windll.user32
    modifiers = MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT
    # Thread-wide hotkey (hwnd=NULL) works with our message pump in tick().
    if user32.RegisterHotKey(None, QUIT_HOTKEY_ID, modifiers, QUIT_VK):
        return True
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    return bool(user32.RegisterHotKey(hwnd, QUIT_HOTKEY_ID, modifiers, QUIT_VK))


def unregister_quit_hotkey() -> None:
    user32 = ctypes.windll.user32
    user32.UnregisterHotKey(None, QUIT_HOTKEY_ID)


def get_cursor_pos() -> tuple[int, int]:
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def move_to_cursor(root: tk.Tk, width: int, height: int, x: int, y: int) -> None:
    root.geometry(f"{width}x{height}+{x - width // 2}+{y - height // 2}")
    ensure_click_through(root)


def place_at_cursor(root: tk.Tk, width: int, height: int) -> tuple[int, int]:
    x, y = get_cursor_pos()
    move_to_cursor(root, width, height, x, y)
    root.update()
    return x, y


def tick(
    root: tk.Tk,
    width: int,
    height: int,
    last_pos: list[int],
    follow_mouse: bool,
    poll_ms: int,
) -> None:
    msg = wintypes.MSG()
    user32 = ctypes.windll.user32
    PM_REMOVE = 0x0001

    while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
        if msg.message == WM_HOTKEY and msg.wParam == QUIT_HOTKEY_ID:
            root.quit()
            return

    if follow_mouse:
        x, y = get_cursor_pos()
        if x != last_pos[0] or y != last_pos[1]:
            last_pos[0], last_pos[1] = x, y
            move_to_cursor(root, width, height, x, y)

    root.after(
        poll_ms,
        lambda: tick(root, width, height, last_pos, follow_mouse, poll_ms),
    )


def enable_ctrl_c(root: tk.Tk) -> None:
    def _handler(_signum: int, _frame: object) -> None:
        root.after(0, root.quit)

    signal.signal(signal.SIGINT, _handler)

    def _pulse() -> None:
        root.update_idletasks()
        root.after(250, _pulse)

    _pulse()


def draw_cross(canvas: tk.Canvas, size: int, gap: int, thickness: int, dot: bool) -> None:
    center = size
    canvas.config(width=size * 2, height=size * 2)

    arm = size - gap
    color = canvas.crosshair_color  # type: ignore[attr-defined]
    line_kw = {"fill": color, "width": thickness}

    canvas.create_line(gap, center, gap + arm, center, **line_kw)
    canvas.create_line(size + gap, center, size + arm, center, **line_kw)
    canvas.create_line(center, gap, center, gap + arm, **line_kw)
    canvas.create_line(center, size + gap, center, size + arm, **line_kw)

    if dot:
        r = max(1, thickness)
        canvas.create_oval(center - r, center - r, center + r, center + r, fill=color, outline=color)


def draw_dot(canvas: tk.Canvas, size: int, thickness: int) -> None:
    center = size
    canvas.config(width=size * 2, height=size * 2)
    r = max(2, thickness * 2)
    color = canvas.crosshair_color  # type: ignore[attr-defined]
    canvas.create_oval(center - r, center - r, center + r, center + r, fill=color, outline=color)


def draw_circle(canvas: tk.Canvas, size: int, thickness: int) -> None:
    center = size
    canvas.config(width=size * 2, height=size * 2)
    color = canvas.crosshair_color  # type: ignore[attr-defined]
    pad = thickness
    canvas.create_oval(pad, pad, size * 2 - pad, size * 2 - pad, outline=color, width=thickness)


def run_overlay(config: dict) -> None:
    if sys.platform != "win32":
        raise SystemExit("This overlay currently supports Windows only.")

    size = int(config.get("size", 24))
    style = config.get("style", "cross")
    color = config.get("color", "#00ff00")
    thickness = int(config.get("thickness", 2))
    gap = int(config.get("gap", 6))
    dot = bool(config.get("dot", True))
    opacity = float(config.get("opacity", 0.9))
    follow_mouse = bool(config.get("follow_mouse", True))
    poll_ms = max(1, min(int(config.get("poll_ms", 8)), 16))

    root = tk.Tk()
    root.title("my-crosshair")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "magenta")
    root.attributes("-alpha", opacity)
    root.configure(bg="magenta")

    canvas = tk.Canvas(root, bg="magenta", highlightthickness=0, bd=0)
    canvas.crosshair_color = color  # type: ignore[attr-defined]
    canvas.pack()

    if style == "dot":
        draw_dot(canvas, size, thickness)
    elif style == "circle":
        draw_circle(canvas, size, thickness)
    else:
        draw_cross(canvas, size, gap, thickness, dot)

    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    if w <= 1 or h <= 1:
        w = h = size * 2

    if follow_mouse:
        last_x, last_y = place_at_cursor(root, w, h)
        last_pos = [last_x, last_y]
    else:
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        move_to_cursor(root, w, h, sw // 2, sh // 2)
        root.update()
        last_pos = [-1, -1]

    ensure_click_through(root)

    if not register_quit_hotkey():
        print("Warning: could not register Ctrl+Shift+X quit hotkey.", file=sys.stderr)

    root.protocol("WM_DELETE_WINDOW", root.quit)
    enable_ctrl_c(root)

    print("Crosshair running. Quit: Ctrl+Shift+X  |  Ctrl+C (in this terminal)", flush=True)
    tick(root, w, h, last_pos, follow_mouse, poll_ms)

    try:
        root.mainloop()
    finally:
        unregister_quit_hotkey()


def main() -> None:
    run_overlay(load_config())


if __name__ == "__main__":
    main()
