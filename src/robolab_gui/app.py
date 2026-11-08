"""Service assembler and application entry point."""

import sys
import logging
from typing import Optional

from robolab_gui.domain.deck import DeckManager
from robolab_gui.hardware.session import HardwareSession
from robolab_gui.configuration.machine_profiles import MachineProfileService
from robolab_gui.protocols.catalog import ProtocolCatalog
from robolab_gui.execution.engine import ExecutionEngine
from robolab_gui.reporting.session_logs import SessionLogService


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
    """Launch the complete RoboLab Master GUI application."""
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
