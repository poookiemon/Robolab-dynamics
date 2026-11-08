"""Headless protocol execution engine shared by Tkinter, Qt, and CLI interfaces."""

import time
import logging
import threading
from typing import Optional, List, Callable

from robolab_gui.domain.deck import DeckManager
from robolab_gui.hardware.session import HardwareSession
from robolab_gui.protocols.models import Protocol, ProtocolStep
from robolab_gui.protocols.planning import ProtocolPlanner
from robolab_gui.execution.run_state import RunState, RunStatus
from robolab_gui.execution.tip_state import TipStateTracker
from robolab_gui.execution.liquid_state import LiquidStateTracker
from robolab_gui.execution.recovery import RecoveryManager, RecoveryDecision, RecoveryAction
from robolab_gui.execution.timing import ExecutionTimer
from robolab_gui.execution.events import (
    ExecutionEvent,
    StepStartedEvent,
    StepCompletedEvent,
    RunStatusChangedEvent,
)
from robolab_gui.geometry.nozzle_layout import NozzleLayout
from robolab_gui.reporting.session_logs import SessionLogService

logger = logging.getLogger("RoboLab.ExecutionEngine")


class ExecutionEngine:
    """Core protocol runner orchestrating hardware, deck, timing, and recovery."""

    def __init__(
        self,
        session: HardwareSession,
        deck_manager: DeckManager,
        session_logger: Optional[SessionLogService] = None,
        recovery_manager: Optional[RecoveryManager] = None,
    ):
        self.session = session
        self.deck_manager = deck_manager
        self.session_logger = session_logger or SessionLogService()
        self.recovery_manager = recovery_manager or RecoveryManager()

        self.tip_tracker = TipStateTracker()
        self.liquid_tracker = LiquidStateTracker()
        self.run_state = RunState()

        self._abort_flag = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Unpaused initially

        self._event_listeners: List[Callable[[ExecutionEvent], None]] = []

    def add_event_listener(self, listener: Callable[[ExecutionEvent], None]) -> None:
        self._event_listeners.append(listener)

    def _emit(self, event: ExecutionEvent) -> None:
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error("Error in event listener: %s", e)

    def pause(self) -> None:
        if self._pause_event.is_set():
            self._pause_event.clear()
            self.run_state.status = RunStatus.PAUSED
            self._emit(RunStatusChangedEvent(time.time(), "Run paused", RunStatus.RUNNING, RunStatus.PAUSED))

    def resume(self) -> None:
        if not self._pause_event.is_set():
            self._pause_event.set()
            self.run_state.status = RunStatus.RUNNING
            self._emit(RunStatusChangedEvent(time.time(), "Run resumed", RunStatus.PAUSED, RunStatus.RUNNING))

    def abort(self, reason: RunStatus = RunStatus.ABORTED_USER) -> None:
        self.run_state.status = reason
        self._abort_flag.set()
        self._pause_event.set()
        self._emit(RunStatusChangedEvent(time.time(), f"Run aborted: {reason}", RunStatus.RUNNING, reason))

    def execute_protocol(self, protocol: Protocol) -> RunStatus:
        """Execute a full protocol sequence."""
        self._abort_flag.clear()
        self._pause_event.set()
        self.run_state.status = RunStatus.RUNNING
        self.run_state.total_steps = len(protocol.steps)
        self.run_state.current_step_index = 0

        baselines = ProtocolPlanner.estimate_step_durations(protocol.steps)
        timer = ExecutionTimer(baselines)
        timer.start()

        self.session_logger.start_session(protocol.name, self.run_state.total_steps)

        idx = 0
        while idx < len(protocol.steps):
            self._pause_event.wait()
            if self._abort_flag.is_set():
                break

            step = protocol.steps[idx]
            self.run_state.current_step_index = idx

            # Virtual Tip Remapping
            act = step.action.lower()
            if "pick" in act and "tip" in act:
                if not step.slot or step.slot.upper() in ("AUTO", "DEFAULT", "NONE", ""):
                    step.slot = "Slot_4"
                is_8ch = step.eight_ch_symmetric or (str(step.mounted_channels).count("-") > 0)
                remapped_well = self.tip_tracker.resolve_next_tip(step.slot, is_8ch_pickup=is_8ch, requested_well=step.well)
                if not remapped_well:
                    self.abort(RunStatus.AUTO_ABORTED_EMPTY_TIPS)
                    break
                step.well = remapped_well

            t_step_start = time.time()
            self._emit(StepStartedEvent(
                timestamp=t_step_start,
                message=f"Starting step {idx + 1}/{len(protocol.steps)}: {step.action}",
                step_index=idx,
                total_steps=len(protocol.steps),
                action=step.action,
                slot=step.slot,
                well=step.well,
            ))

            try:
                self._execute_single_step(step)
                duration = time.time() - t_step_start
                timer.update_speed_factor(idx + 1)
                self.run_state.active_elapsed_seconds = timer.get_active_elapsed()
                self.run_state.estimated_remaining_seconds = timer.get_remaining_seconds(idx + 1)
                self.run_state.speed_factor = timer.live_speed_factor

                self._emit(StepCompletedEvent(
                    timestamp=time.time(),
                    message=f"Completed step {idx + 1}",
                    step_index=idx,
                    duration_seconds=duration,
                ))
                idx += 1

            except Exception as ex:
                logger.error("Exception during step %d: %s", idx + 1, ex)
                recovery = self.recovery_manager.handle_error(ex, idx)

                if recovery.decision == RecoveryDecision.RETRY:
                    logger.info("Retrying step %d...", idx + 1)
                    continue  # Keep idx unchanged, retry step
                elif recovery.decision == RecoveryDecision.CLEAR_UNJAM:
                    self._execute_clearance(recovery.clear_slot, recovery.clear_well)
                    continue
                elif recovery.decision == RecoveryDecision.SKIP:
                    logger.info("Skipping step %d...", idx + 1)
                    idx += 1
                else:
                    self.abort(RunStatus.AUTO_ABORTED_ERROR)
                    break

        final_status = self.run_state.status if self._abort_flag.is_set() else RunStatus.COMPLETED
        self.run_state.status = final_status
        self.session_logger.finish_session(final_status.value)
        return final_status

    def _execute_single_step(self, step: ProtocolStep) -> None:
        """Dispatch step to hardware motions."""
        hw = self.session.hardware
        act = step.action.lower()

        # Coordinate resolution
        cx, cy = self.deck_manager.calculate_xy(step.slot, step.well)
        if step.eight_ch_symmetric or (str(step.mounted_channels).count("-") > 0):
            cy = NozzleLayout.get_carriage_y_for_manifold(cy, step.mounted_channels, True, True, step.tip_offset_rows, step.slot)

        # Move safe Z first
        hw.move_abs(z=0.0)
        hw.move_abs(x=cx, y=cy)

        # Action handling
        if "pick" in act and "tip" in act:
            target_z = self.deck_manager.calculate_z("Pick Up Tip", step.slot, step.well)
            hw.pickup_tip(target_z)
        elif "discard" in act or "drop" in act:
            target_z = self.deck_manager.calculate_z("Discard Tip", step.slot, step.well)
            hw.move_abs(z=target_z)
            hw.eject_tip()
            hw.move_abs(z=0.0)
        elif "aspirate" in act:
            target_z = self.deck_manager.calculate_z("Aspirate Media", step.slot, step.well, step.volume)
            hw.move_abs(z=target_z)
            hw.aspirate(step.volume)
            hw.move_abs(z=0.0)
            self.liquid_tracker.aspirate(step.slot, step.well, step.volume)
        elif "dispense" in act:
            target_z = self.deck_manager.calculate_z("Dispense Media", step.slot, step.well, step.volume)
            hw.move_abs(z=target_z)
            hw.dispense(step.volume)
            if step.mix_cycles > 0 and step.mix_volume_ul > 0:
                for _ in range(step.mix_cycles):
                    hw.aspirate(step.mix_volume_ul)
                    hw.dispense(step.mix_volume_ul)
            hw.move_abs(z=0.0)
            self.liquid_tracker.dispense(step.slot, step.well, step.volume)

    def _execute_clearance(self, slot: str, well: str) -> None:
        hw = self.session.hardware
        cx, cy = self.deck_manager.calculate_xy(slot, well)
        hw.move_abs(z=0.0)
        hw.move_abs(x=cx, y=cy)
        hw.move_abs(z=75.0)
        hw.eject_tip()
        hw.move_abs(z=0.0)
