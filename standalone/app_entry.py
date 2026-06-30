"""
Combined entry point for the single-file sdf_csv_converter executable.

Behavior:
- Launched with no arguments (e.g. double-clicked): opens the GUI.
- Launched with arguments (e.g. from a terminal): runs the CLI, attaching to the
  parent console first so output is visible.

This script does not modify the existing ``sdf_csv_converter`` package; it only
imports it. When run unfrozen it adds the repository root (the parent of this
``standalone`` folder) to ``sys.path`` so ``import sdf_csv_converter`` resolves.
"""
import os
import sys


def _bootstrap_path() -> None:
    """Ensure the repo root is importable when running unfrozen.

    When frozen by PyInstaller the package is bundled, so sys.path is already
    set up and this is harmless.
    """
    if getattr(sys, "frozen", False):
        return
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _close_splash() -> None:
    """Close the PyInstaller onefile splash screen if present (frozen only)."""
    try:
        import pyi_splash  # type: ignore

        pyi_splash.close()
    except Exception:
        pass


def run() -> None:
    _bootstrap_path()

    if len(sys.argv) > 1:
        import win_console

        win_console.ensure_console()
        # Import the (heavy) converter stack while the splash is still up.
        from sdf_csv_converter.main import main as cli_main

        _close_splash()
        cli_main()
    else:
        # Hide the auto-allocated console before heavy imports (console-subsystem
        # exe only) so double-click does not leave a terminal window open.
        import win_console

        win_console.hide_console_window()
        from sdf_csv_converter.gui import main as gui_main

        _close_splash()
        gui_main()


if __name__ == "__main__":
    run()
