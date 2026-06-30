"""
Console helpers for the combined single-file executable.

The exe is built as a **windowed** app (``console=False``) so double-clicking
does not flash a blank terminal. On the **CLI** path (arguments present)
``ensure_console()`` attaches to the parent console or allocates one so stdout,
stderr, and redirection (``> file``, ``2> log``) still work.

``hide_console_window()`` remains available for legacy console-subsystem builds.
because the CLI help and summary contain Unicode (e.g. ``\u2192``) that would
raise ``UnicodeEncodeError`` on legacy cp1252 consoles.

On non-Windows platforms ``ensure_console()`` only reconfigures streams to UTF-8.
"""
import sys

_ATTACH_PARENT_PROCESS = -1  # (DWORD)-1
_CP_UTF8 = 65001
_SW_HIDE = 0


def hide_console_window() -> None:
    """Hide the console window on the GUI launch path (frozen exe only).

    Uses ``ShowWindow(SW_HIDE)`` rather than ``FreeConsole()`` so tkinter is
    not disrupted. A brief console flash may still appear on cold start before
    this runs.
    """
    if not getattr(sys, "frozen", False):
        return  # keep the dev terminal visible when running unfrozen
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, _SW_HIDE)
    except Exception:
        pass


def ensure_console() -> None:
    """Make sure stdout/stderr/stdin are usable (and UTF-8) for CLI output.

    Attaches to the parent console if the exe was launched from a terminal;
    otherwise allocates a new console window. Safe to call multiple times and
    safe to call when running unfrozen.
    """
    if not sys.platform.startswith("win"):
        _reconfigure_utf8()
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # Attach to the launching terminal's console; if that fails (no parent
        # console, e.g. launched from Explorer with args) allocate a new one.
        attached = bool(kernel32.AttachConsole(_ATTACH_PARENT_PROCESS))
        if not attached:
            attached = bool(kernel32.AllocConsole())
        if attached:
            _rebind_standard_streams()
        # Force the console code page to UTF-8 so arrows/box chars render and do
        # not raise UnicodeEncodeError. Harmless if it fails.
        try:
            kernel32.SetConsoleOutputCP(_CP_UTF8)
            kernel32.SetConsoleCP(_CP_UTF8)
        except Exception:
            pass
    except Exception:
        pass

    _reconfigure_utf8()


def _rebind_standard_streams() -> None:
    """Point sys.stdout/stderr/stdin at the now-attached console device."""
    try:
        sys.stdout = open("CONOUT$", "w", buffering=1, encoding="utf-8",
                          errors="replace")
    except OSError:
        pass
    try:
        sys.stderr = open("CONOUT$", "w", buffering=1, encoding="utf-8",
                          errors="replace")
    except OSError:
        pass
    try:
        sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
    except OSError:
        pass


def _reconfigure_utf8() -> None:
    """Best-effort switch of the existing std streams to UTF-8 (errors=replace).

    Covers the already-attached case (e.g. running unfrozen in a terminal) where
    we cannot re-open the console device but can still fix the stream encoding.
    """
    for name in ("stdout", "stderr", "stdin"):
        stream = getattr(sys, name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
