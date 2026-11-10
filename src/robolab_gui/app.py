"""Service assembler and application entry point."""

import os
import sys
import subprocess
import logging
from typing import Optional, List

from robolab_gui import __version__
from robolab_gui.domain.deck import DeckManager
from robolab_gui.hardware.session import HardwareSession
from robolab_gui.configuration.machine_profiles import MachineProfileService
from robolab_gui.protocols.catalog import ProtocolCatalog
from robolab_gui.execution.engine import ExecutionEngine
from robolab_gui.reporting.session_logs import SessionLogService

REPO_GIT_URL = "https://github.com/poookiemon/Robolab-dynamics.git"
_WRAPPER_NAMES = ("robolab", "robolab-gui", "biohit-gui", "robolab-dynamics", "biohit", "robolab-update")


def _cleanup_old_windows_wrappers() -> None:
    """Remove any leftover .exe.old wrapper files from a previous self-update on Windows."""
    if os.name != "nt":
        return
    dirs = {
        os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else "",
        os.path.join(sys.prefix, "Scripts"),
        os.path.dirname(sys.executable),
    }
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for name in _WRAPPER_NAMES:
            old_path = os.path.join(d, f"{name}.exe.old")
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass


def run_self_update(args: Optional[List[str]] = None) -> int:
    """Update robolab-gui directly from GitHub via pip."""
    args = list(args or [])
    include_deps = False
    branch = "main"

    for arg in args:
        if arg in ("--deps", "--full", "-f"):
            include_deps = True
        elif not arg.startswith("-"):
            branch = arg

    target_spec = f"git+{REPO_GIT_URL}@{branch}"
    print(f"🔄 Updating RoboLab (current: v{__version__}) from branch '{branch}'...")

    renamed_wrappers = []
    if os.name == "nt":
        dirs = {
            os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else "",
            os.path.join(sys.prefix, "Scripts"),
            os.path.dirname(sys.executable),
        }
        for d in dirs:
            if not d or not os.path.isdir(d):
                continue
            for name in _WRAPPER_NAMES:
                exe_path = os.path.join(d, f"{name}.exe")
                old_path = os.path.join(d, f"{name}.exe.old")
                if os.path.exists(exe_path):
                    try:
                        if os.path.exists(old_path):
                            os.remove(old_path)
                        os.rename(exe_path, old_path)
                        renamed_wrappers.append((exe_path, old_path))
                    except OSError:
                        pass

    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir"]
    if not include_deps:
        cmd.append("--no-deps")
    cmd.append(target_spec)

    try:
        res = subprocess.run(cmd)
        if res.returncode != 0 and not include_deps:
            print("⚠️ Fast update encountered an issue; retrying with full dependency check...")
            cmd_full = [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", target_spec]
            res = subprocess.run(cmd_full)

        if res.returncode == 0:
            # Verify new version in subprocess
            ver_cmd = [
                sys.executable, "-c",
                "from importlib.metadata import version; print(version('robolab-gui'))"
            ]
            ver_res = subprocess.run(ver_cmd, capture_output=True, text=True)
            new_ver = ver_res.stdout.strip() if ver_res.returncode == 0 else "latest"
            print(f"\n✅ RoboLab successfully updated to v{new_ver}! Run 'robolab' to launch.")
            return 0
        else:
            for exe_path, old_path in renamed_wrappers:
                if not os.path.exists(exe_path) and os.path.exists(old_path):
                    try:
                        os.rename(old_path, exe_path)
                    except OSError:
                        pass
            print(f"\n❌ Update failed with exit code {res.returncode}.")
            return res.returncode
    except Exception as exc:
        for exe_path, old_path in renamed_wrappers:
            if not os.path.exists(exe_path) and os.path.exists(old_path):
                try:
                    os.rename(old_path, exe_path)
                except OSError:
                    pass
        print(f"\n❌ Update error: {exc}")
        return 1


def update_cli() -> None:
    """Dedicated entry point for 'robolab-update'."""
    _cleanup_old_windows_wrappers()
    sys.exit(run_self_update(sys.argv[1:]))


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def create_application_context():
    """Instantiate and wire domain, hardware, configuration, and execution services."""
    profile_service = MachineProfileService()
    deck_manager = DeckManager()
    session = HardwareSession()
    session.connect(use_simulation=True)  # Safe default until operator clicks connect
    catalog = ProtocolCatalog()
    active_id = getattr(profile_service.active_profile, "id", "machine_2_1_10ul")
    session_logger = SessionLogService(machine_id=active_id)
    engine = ExecutionEngine(
        session=session,
        deck_manager=deck_manager,
        session_logger=session_logger,
    )

    return {
        "profile_service": profile_service,
        "deck_manager": deck_manager,
        "session": session,
        "catalog": catalog,
        "engine": engine,
        "session_logger": session_logger,
    }


def main(ui_framework: str = "master"):
    """Launch the complete RoboLab Master GUI application (or handle CLI subcommands)."""
    _cleanup_old_windows_wrappers()

    if len(sys.argv) > 1:
        subcmd = sys.argv[1].strip().lower()
        if subcmd in ("update", "upgrade", "--update", "-u"):
            sys.exit(run_self_update(sys.argv[2:]))
        if subcmd in ("version", "--version", "-v"):
            print(f"robolab-gui {__version__}")
            return

    if ui_framework.lower() == "modular":
        setup_logging()
        ctx = create_application_context()
        from robolab_gui.ui.tkinter.main_window import MainWindow
        app = MainWindow(
            deck_manager=ctx["deck_manager"],
            session=ctx["session"],
            profile_service=ctx["profile_service"],
            catalog=ctx["catalog"],
            engine=ctx["engine"],
        )
        app.mainloop()
        return

    import os
    # 1. If running directly inside a git clone / developer workspace, use the local directory
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dev_legacy_dir = os.path.join(repo_root, "Biohit-Automated-Pipettor-GUI")
    if os.path.isdir(os.path.join(repo_root, ".git")) and os.path.isdir(dev_legacy_dir):
        if dev_legacy_dir not in sys.path:
            sys.path.insert(0, dev_legacy_dir)
        os.chdir(dev_legacy_dir)
        try:
            import lims_master_gui
            lims_master_gui.launch()
            return
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("RoboLab Boot Error", f"Fatal error during application startup:\n\n{e}\n\n{traceback.format_exc()}")
                root.destroy()
            except Exception:
                pass
            raise

    # 2. For pip installations, run the packaged robolab_legacy module from site-packages
    try:
        import robolab_legacy.lims_master_gui as legacy_gui
        pkg_legacy_dir = os.path.dirname(legacy_gui.__file__)
        if pkg_legacy_dir not in sys.path:
            sys.path.insert(0, pkg_legacy_dir)
        os.chdir(pkg_legacy_dir)
        legacy_gui.launch()
        return
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("RoboLab Boot Error", f"Failed to start RoboLab GUI:\n\n{e}\n\n{traceback.format_exc()}")
            root.destroy()
        except Exception:
            pass
        raise

    # Graceful fallback to modular MainWindow if standalone legacy directory is absent
    setup_logging()
    ctx = create_application_context()
    from robolab_gui.ui.tkinter.main_window import MainWindow
    app = MainWindow(
        deck_manager=ctx["deck_manager"],
        session=ctx["session"],
        profile_service=ctx["profile_service"],
        catalog=ctx["catalog"],
        engine=ctx["engine"],
    )
    app.mainloop()


if __name__ == "__main__":
    main()
