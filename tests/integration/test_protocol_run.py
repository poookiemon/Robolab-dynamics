"""Integration test executing a full multi-step protocol on simulated hardware."""

from robolab_gui.protocols.models import Protocol, ProtocolStep
from robolab_gui.execution.engine import ExecutionEngine
from robolab_gui.execution.run_state import RunStatus
from robolab_gui.hardware.session import HardwareSession
from robolab_gui.hardware.simulated import SimulatedHardware
from robolab_gui.domain.deck import DeckManager
from robolab_gui.reporting.session_logs import SessionLogService


def test_full_protocol_run_lifecycle(tmp_path):
    hw = SimulatedHardware()
    hw.connect()
    session = HardwareSession(hw)
    session.connect(use_simulation=True)
    session.initialize_head("machine_2_1_10ul")

    deck = DeckManager()
    session_logs = SessionLogService(logs_dir=tmp_path / "logs")
    engine = ExecutionEngine(session=session, deck_manager=deck, session_logger=session_logs)

    protocol = Protocol(
        name="Integration Test Protocol",
        steps=[
            ProtocolStep(action="Pick Up Tip", slot="Slot_4", well="A1"),
            ProtocolStep(action="Aspirate Media", slot="Slot_3", well="A1", volume=7.5),
            ProtocolStep(action="Dispense Media", slot="Slot_5", well="A1", volume=7.5),
            ProtocolStep(action="Discard Tip", slot="Slot_2", well="A1"),
        ]
    )

    status = engine.execute_protocol(protocol)
    assert status == RunStatus.COMPLETED
    assert engine.run_state.current_step_index == 3
    assert engine.tip_tracker.get_consumed_count("Slot_4") == 1

    # Verify log output was created and renamed
    logs = list((tmp_path / "logs").glob("*_COMPLETED.log"))
    assert len(logs) == 1
