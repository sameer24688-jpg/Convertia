"""
Startup failure reporting for the frozen Convertia executable.

Writes ``convertia_error.log`` beside the .exe and shows a Windows message box so
GUI launches do not fail silently when the console has been hidden.
"""
from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime


def _exe_directory() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def error_log_path() -> str:
    return os.path.join(_exe_directory(), "convertia_error.log")


def close_pyinstaller_splash() -> None:
    """Close the PyInstaller onefile splash screen if present."""
    try:
        import pyi_splash  # type: ignore

        pyi_splash.close()
    except Exception:
        pass


def _show_message_box(title: str, message: str) -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
            None,
            message,
            title,
            0x10,  # MB_ICONERROR
        )
    except Exception:
        pass


def report_startup_failure(exc: BaseException) -> None:
    """Log a startup traceback and alert the user."""
    close_pyinstaller_splash()

    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    log_path = error_log_path()
    header = (
        f"Convertia startup failure\n"
        f"Time: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Executable: {getattr(sys, 'executable', '')}\n"
        f"Frozen: {getattr(sys, 'frozen', False)}\n"
        f"{'-' * 60}\n"
    )
    try:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(header)
            fh.write(tb)
            fh.write("\n")
    except OSError:
        log_path = "(could not write log file)"

    summary = str(exc).strip() or exc.__class__.__name__
    if len(summary) > 240:
        summary = summary[:237] + "..."

    _show_message_box(
        "Convertia could not start",
        (
            f"{summary}\n\n"
            f"Details were saved to:\n{log_path}\n\n"
            "Try running from Command Prompt:\n"
            "  Convertia.exe --version\n\n"
            "If Windows blocked the file, right-click the .exe, choose "
            "Properties, and check Unblock if shown."
        ),
    )

    # Best-effort console output when a terminal is attached.
    try:
        print(header, file=sys.stderr)
        print(tb, file=sys.stderr)
    except Exception:
        pass
