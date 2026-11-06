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
    session_logger = SessionLogService()
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


def main(ui_framework: str = "tkinter"):
    """Launch the RoboLab GUI application."""
    setup_logging()
    ctx = create_application_context()

    if ui_framework.lower() == "qt":
        try:
            from robolab_gui.ui.qt.main_window import QtMainWindow
            from PyQt6.QtWidgets import QApplication
            app = QApplication(sys.argv)
            win = QtMainWindow(ctx)
            win.show()
            sys.exit(app.exec())
        except ImportError:
            logging.warning("PyQt6 not available. Falling back to Tkinter UI.")

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
