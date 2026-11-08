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
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    legacy_dir = os.path.join(repo_root, "Biohit-Automated-Pipettor-GUI")
    if not os.path.isdir(legacy_dir):
        cand_cwd = os.path.join(os.getcwd(), "Biohit-Automated-Pipettor-GUI")
        if os.path.isdir(cand_cwd):
            legacy_dir = cand_cwd
        else:
            user_cand = os.path.join(os.path.expanduser("~"), "PycharmProjects", "Robolab-dynamics", "Biohit-Automated-Pipettor-GUI")
            if os.path.isdir(user_cand):
                legacy_dir = user_cand

    if os.path.isdir(legacy_dir):
        if legacy_dir not in sys.path:
            sys.path.insert(0, legacy_dir)
        os.chdir(legacy_dir)
        import lims_master_gui
        lims_master_gui.launch()
        return

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
