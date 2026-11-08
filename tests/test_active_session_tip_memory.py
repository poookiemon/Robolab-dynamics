"""Unit and integration tests for Active Session Tip Memory across all machines."""

import os
import sys
import unittest

# Add paths
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
legacy_dir = os.path.join(repo_root, "Biohit-Automated-Pipettor-GUI")
src_dir = os.path.join(repo_root, "src")
for p in (legacy_dir, src_dir, repo_root):
    if p not in sys.path:
        sys.path.insert(0, p)

from robolab_gui.execution.tip_state import TipStateTracker


class TestModularTipStateTracker(unittest.TestCase):
    """Test TipStateTracker in src/robolab_gui/execution/tip_state.py."""

    def setUp(self):
        self.tracker = TipStateTracker()

    def test_8ch_full_rack_advancing(self):
        """Machine 1: 8x1000 uL full 8-channel rack."""
        # First pick: requested A1
        t1 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well="A1")
        self.assertEqual(t1, "A1")
        # All 8 sockets of col 1 should be consumed
        for r in "ABCDEFGH":
            self.assertTrue(self.tracker.is_consumed("Slot_4", f"{r}1"))

        # User stopped, removed tips, restarted run requesting A1 without resetting tip rack
        t2 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well="A1")
        self.assertEqual(t2, "A2", "Should advance to Column 2 (A2) because Column 1 was consumed!")

        # Next run without reset should advance to Column 3
        t3 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well="A1")
        self.assertEqual(t3, "A3")

    def test_8ch_machine_2_five_tip_advancing(self):
        """Machine 2: 1-10 uL 5-tip parallel pickup (Rows A-E)."""
        step_5tip = "A-E"
        # First pick: requested A1 with 5 tips
        t1 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well="A1", mounted_channels=step_5tip)
        self.assertEqual(t1, "A1")
        for r in "ABCDE":
            self.assertTrue(self.tracker.is_consumed("Slot_4", f"{r}1"))

        # Next pick requesting A1: Column 1 is no longer fresh for A-E -> must advance to Column 2!
        t2 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well="A1", mounted_channels=step_5tip)
        self.assertEqual(t2, "A2")

    def test_single_channel_tip_advancing(self):
        """Single-channel: A1 -> B1 -> C1..."""
        t1 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=False, requested_well="A1")
        self.assertEqual(t1, "A1")
        self.assertTrue(self.tracker.is_consumed("Slot_4", "A1"))

        # Next pick requesting A1: A1 is consumed -> advances to B1
        t2 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=False, requested_well="A1")
        self.assertEqual(t2, "B1")

    def test_unspecified_auto_pickup(self):
        """User does not specify where to get tip from (AUTO/None)."""
        t1 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well=None)
        self.assertEqual(t1, "A1")

        t2 = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well="AUTO")
        self.assertEqual(t2, "A2")

    def test_reset_tip_rack(self):
        """Resetting tip rack clears consumed tips and restarts from Column 1 / A1."""
        self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well="A1")
        self.tracker.reset_slot("Slot_4")
        self.assertEqual(self.tracker.get_consumed_count("Slot_4"), 0)
        t_fresh = self.tracker.resolve_next_tip("Slot_4", is_8ch_pickup=True, requested_well="A1")
        self.assertEqual(t_fresh, "A1")


class TestLegacyLIMSTipMemory(unittest.TestCase):
    """Test tip memory methods in Biohit-Automated-Pipettor-GUI/lims_master_gui.py."""

    def setUp(self):
        import lims_master_gui
        self.app_cls = lims_master_gui.LIMSMasterApp

        # Create a lightweight dummy app instance with tip tracking structures
        class DummyApp:
            def __init__(self):
                self.session_tip_tracker = {}

            def _get_tip_tracker(self, slot_name):
                if slot_name not in self.session_tip_tracker:
                    self.session_tip_tracker[slot_name] = {"cursor": 0, "consumed": set()}
                return self.session_tip_tracker[slot_name]

            def _ordered_tip_wells(self, slot_name):
                return list(lims_master_gui.TIP_ORDER_96)

            _expand_8ch_tip_sockets = staticmethod(lims_master_gui.LIMSMasterApp._expand_8ch_tip_sockets)
            resolve_8ch_session_tip_col = lims_master_gui.LIMSMasterApp.resolve_8ch_session_tip_col
            resolve_session_tip = lims_master_gui.LIMSMasterApp.resolve_session_tip
            mark_tip_consumed = lims_master_gui.LIMSMasterApp.mark_tip_consumed
            _sync_tip_cursor = lims_master_gui.LIMSMasterApp._sync_tip_cursor
            _refresh_tip_memory_badge = lambda self, s="Slot_4": None
            _schedule_deck_redraw = lambda self: None

        self.app = DummyApp()

    def test_8ch_user_abort_and_restart_memory(self):
        """Simulate user's exact reported bug:
        1. 8x1000 run starts, picks Column 1 (A1).
        2. User stops, removes tips, unchecks tip-on-pipette.
        3. Protocol starts again requesting A1 without tip reset.
        4. MUST advance to Column 2 (A2), not Column 1!
        """
        step = {"mounted_channels": "A-H"}
        slot = "Slot_4"

        # Step 1 pickup: Col 1 requested
        col, remapped = self.app.resolve_8ch_session_tip_col(slot, "A1", step)
        self.assertEqual(col, 1)
        self.assertFalse(remapped, "Column 1 is fresh so not remapped")

        # Seated: mark sockets consumed
        for sock in self.app._expand_8ch_tip_sockets(step, f"A{col}"):
            self.app.mark_tip_consumed(slot, sock)

        # User stops protocol, takes off tips, restarts run -> Step 1 requested well is still 'A1'
        col2, remapped2 = self.app.resolve_8ch_session_tip_col(slot, "A1", step)
        self.assertEqual(col2, 2, "MUST advance to Column 2 because Column 1 was consumed!")
        self.assertTrue(remapped2, "Was remapped from consumed Col 1")

        # Pick Col 2 and mark consumed
        for sock in self.app._expand_8ch_tip_sockets(step, f"A{col2}"):
            self.app.mark_tip_consumed(slot, sock)

        # Run again -> advances to Column 3
        col3, remapped3 = self.app.resolve_8ch_session_tip_col(slot, "A1", step)
        self.assertEqual(col3, 3)

    def test_machine_2_five_tip_memory(self):
        """Machine 2 (1-10 uL) 5-tip parallel assay (Rows A-E):
        Rows A-E consumed in Col 1 -> next pick advances to Col 2.
        """
        step = {"mounted_channels": "A-E"}
        slot = "Slot_4"

        col, remapped = self.app.resolve_8ch_session_tip_col(slot, "A1", step)
        self.assertEqual(col, 1)

        # Mark rows A-E consumed
        for sock in self.app._expand_8ch_tip_sockets(step, f"A{col}"):
            self.app.mark_tip_consumed(slot, sock)

        # Col 1 is no longer fresh for A-E -> must advance to Col 2
        col2, remapped2 = self.app.resolve_8ch_session_tip_col(slot, "A1", step)
        self.assertEqual(col2, 2)

    def test_single_channel_tip_memory(self):
        """Machine 3 (300 uL) and single-channel runs:
        A1 consumed -> next pick advances to B1.
        """
        slot = "Slot_4"

        w1, rem1 = self.app.resolve_session_tip(slot, "A1")
        self.assertEqual(w1, "A1")
        self.assertFalse(rem1)
        self.app.mark_tip_consumed(slot, w1)

        # Restart run requesting A1
        w2, rem2 = self.app.resolve_session_tip(slot, "A1")
        self.assertEqual(w2, "B1")
        self.assertTrue(rem2)


if __name__ == "__main__":
    unittest.main()
