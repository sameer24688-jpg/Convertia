"""
Combined entry point for the single-file Convertia executable.

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
    """Ensure the repo root is importable when running unfrozen."""
    if getattr(sys, "frozen", False):
        return
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def run() -> None:
    _bootstrap_path()

    try:
        if len(sys.argv) > 1:
            import win_console

            win_console.ensure_console()
            from sdf_csv_converter.main import main as cli_main

            from startup_errors import close_pyinstaller_splash

            close_pyinstaller_splash()
            cli_main()
            return

        # GUI: import heavy modules before hiding the console so failures are
        # not silent on double-click. The PyInstaller splash stays up during
        # this import on frozen builds.
        from sdf_csv_converter.gui import main as gui_main

        gui_main()
    except Exception as exc:
        from startup_errors import report_startup_failure

        report_startup_failure(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    run()
