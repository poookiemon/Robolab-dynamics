"""Unit tests for port scanning with actual names and initialization gating."""

import os
import sys
import unittest

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
legacy_dir = os.path.join(repo_root, "Biohit-Automated-Pipettor-GUI")
src_dir = os.path.join(repo_root, "src")
for p in (legacy_dir, src_dir, repo_root):
    if p not in sys.path:
        sys.path.insert(0, p)

from working import BiohitInterface


class TestPortScanningAndInitialization(unittest.TestCase):
    """Verify ports are accurately listed with actual names and initialization cannot happen without port selection."""

    def setUp(self):
        self.hw = BiohitInterface()

    def test_scan_ports_returns_descriptive_names(self):
        """Verify scan_ports accurately returns descriptive items rather than just 'MOCK_PORT'."""
        ports = self.hw.scan_ports()
        self.assertIsInstance(ports, list)
        self.assertGreater(len(ports), 0, "Should at least find simulation or native bridge or detected ports")
        for p in ports:
            # Each entry should have a readable format or separator
            self.assertIsInstance(p, str)
            self.assertNotIn("MOCK_PORT", p, "Old MOCK_PORT string should be replaced with descriptive name")

    def test_extract_clean_port(self):
        """Verify clean port ID extraction from descriptive name."""
        self.assertEqual(BiohitInterface.extract_clean_port("COM3 — USB Serial Port (COM3)"), "COM3")
        self.assertEqual(BiohitInterface.extract_clean_port("COM4 - FTDI FT232R"), "COM4")
        self.assertEqual(BiohitInterface.extract_clean_port("/dev/ttyUSB0 — Serial Device"), "/dev/ttyUSB0")
        self.assertEqual(BiohitInterface.extract_clean_port("SIMULATION — Virtual Robot (Offline Test)"), "SIMULATION")

    def test_connect_fails_when_no_port_selected(self):
        """Verify connect returns False when port is empty or unselected placeholder."""
        for invalid_port in ["", "   ", "Select Hardware Port...", "Select Port...", "(No Serial Ports Detected)"]:
            ok, msg = self.hw.connect(invalid_port)
            self.assertFalse(ok, f"connect('{invalid_port}') should return False!")
            self.assertIn("No hardware port selected", msg)
            self.assertFalse(self.hw.is_initialized)

    def test_initialize_blocked_if_no_port_connected(self):
        """Verify initialize cannot happen unless a port is selected and connected."""
        # Clean state, no port connected
        self.hw.active_port = None
        self.hw.is_initialized = False

        ok, msg = self.hw.initialize()
        self.assertFalse(ok, "Initialize should return False if no port was selected!")
        self.assertFalse(self.hw.is_initialized, "Hardware must NOT be marked initialized!")
        self.assertIn("No hardware port", msg)

    def test_successful_connect_and_initialize_with_selected_port(self):
        """Verify that when a valid port is selected, connect and initialize succeed."""
        selected_port = "COM3 — USB Serial Port (COM3)"
        ok, msg = self.hw.connect(selected_port)
        self.assertTrue(ok, f"Connect should succeed for valid port: {msg}")
        self.assertEqual(self.hw.active_port, "COM3")

        ok2, msg2 = self.hw.initialize()
        self.assertTrue(ok2, f"Initialize should succeed once port is connected: {msg2}")
        self.assertTrue(self.hw.is_initialized, "Hardware should now be marked initialized!")


class TestGUIPortGating(unittest.TestCase):
    """Verify GUI initialization cannot proceed unless a port is selected."""

    def test_gui_hw_init_blocks_without_port(self):
        """Simulate GUI hw_init when operator clicks Connect & Initialize without picking a port."""
        import tkinter as tk
        from tkinter import messagebox
        from unittest.mock import patch
        import lims_master_gui

        root = tk.Tk()
        root.withdraw()
        app = lims_master_gui.LIMSMasterApp(root)

        try:
            # 1. Port dropdown starts as 'Select Hardware Port...'
            app.port_var.set("Select Hardware Port...")

            with patch.object(messagebox, "showwarning") as mock_warn:
                app.hw_init()
                mock_warn.assert_called_once()
                self.assertIn("Hardware Port Required", mock_warn.call_args[0][0])
                self.assertFalse(app.lims.hw.is_initialized, "Hardware must NOT be initialized!")

            # 2. Pipettor Head init on Tab 1 must also block if hardware not initialized
            with patch.object(messagebox, "showwarning") as mock_warn2:
                app.action_initialize_pipettor()
                mock_warn2.assert_called_once()
                self.assertIn("Hardware Port Required", mock_warn2.call_args[0][0])
                self.assertFalse(app.is_head_initialized, "Pipette head must NOT be initialized!")

            # 3. Select a valid port and initialize
            app.port_var.set("COM3 — USB Serial Port (COM3)")
            with patch.object(messagebox, "showinfo") as mock_info:
                app.hw_init()
                self.assertTrue(app.lims.hw.is_initialized, "Hardware should now be initialized!")
                self.assertIn("ONLINE", app.lbl_hw_stat.cget("text"))

            # 4. Now that hardware is initialized, pipettor head initialization should succeed
            with patch.object(messagebox, "showinfo") as mock_info2:
                app.action_initialize_pipettor()
                self.assertTrue(app.is_head_initialized, "Pipette head should now be initialized!")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
