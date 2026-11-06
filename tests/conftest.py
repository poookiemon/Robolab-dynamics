"""Shared test fixtures for RoboLab test suites."""

import pytest
import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from robolab_gui.domain.deck import DeckManager
from robolab_gui.hardware.simulated import SimulatedHardware
from robolab_gui.hardware.session import HardwareSession
from robolab_gui.configuration.machine_profiles import MachineProfileService
from robolab_gui.protocols.catalog import ProtocolCatalog
from robolab_gui.execution.engine import ExecutionEngine


@pytest.fixture
def simulated_hardware():
    hw = SimulatedHardware()
    hw.connect("test_port")
    return hw


@pytest.fixture
def hardware_session(simulated_hardware):
    session = HardwareSession(simulated_hardware)
    session.connect(use_simulation=True)
    return session


@pytest.fixture
def deck_manager():
    return DeckManager()


@pytest.fixture
def profile_service(tmp_path):
    return MachineProfileService(profiles_dir=tmp_path / "profiles")


@pytest.fixture
def execution_engine(hardware_session, deck_manager):
    return ExecutionEngine(session=hardware_session, deck_manager=deck_manager)
