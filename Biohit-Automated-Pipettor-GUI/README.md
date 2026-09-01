## Biohit-Automated-Pipettor-GUI

**Note: Ensure the biohit_pipettor package is available in your environment to connect to the hardware.**

## The 5 Core Files
* **lims_master_gui.py:** The main app window. Use this to move the robot, map the deck, and run automated protocols.
* **working.py:** The background rules and math. It handles the robot's limits and safely routes the coordinate geometry.
* **deck_gui.py:** A quick setup tool to calibrate exactly where your well plates sit on the machine bed.
* **assay.py:** A standalone script to run a hardcoded Calcium gradient test (0.2mM to 4.0mM) without needing the UI.
* **gui.py:** The data analyzer. After the FOC48 takes a measurement, use this to open your *peak_forces.csv files and calculate the Hill equation for your calcium curve.


## Core Dependencies
These 5 specific libraries are required to be installed:

* **`numpy` & `scipy`:** Required by `gui.py`.
* **`matplotlib`:** Required by `gui.py`.
* **`ttkbootstrap`:** Required by `lims_master_gui.py`.
* **`biohit_pipettor`:** Required by `working.py`.


## Safety Interlocks & Key Features
* **Volume Slicing:** If a protocol asks for 600µL, the software automatically splits it into three safe 200µL trips to prevent flooding the manifold.
* **Absolute Mapping:** Uses hardcoded physical coordinates for specific plates (like EHM grids) instead of guessing, preventing hardware crashes.
* **Z-Axis Clearance:** Forces the robot to pull up to a safe height between moves to avoid cross-contamination.
* **On-the-Fly Protocol Adjustment:** You can safely pause the protocol at any time and monitor the visual progress bar (this acts as a hard pause, not a live parameter editor).

## Future Roadmap
This system is stable and handles the core workflows, but it is not dynamic. 

If this is to be advanced, below are the features that can be built next:

* **Embed the Calcium Curve in the LIMS:** A separate pop-up window for the Dose-Response graph should be architected to render directly inside Tab 5 of `lims_master_gui.py` for a seamless protocol.
* **Automated PDF Reporting:** Expand the data analyzer to automatically export the metrics and into a formatted PDF or Excel report for easy lab sharing.
* **Expand the Labware Library:** The current JSON blueprints only cover the plates currently in use (e.g., EHM grids, standard 96-well). Use `deck_gui.py` to build and map profiles for different labware or custom reagent troughs.
* **Mid-Run Error Recovery:** If a physical error occurs (like a dropped tip), the protocol usually requires a hard restart. Building a "Resume from Step X" feature into `lims_master_gui.py` would save a lot of time.
* **Live Parameter Editing:** Upgrade the pause feature. Currently, you can pause the run and monitor the progress bar, but you cannot actively tweak pipetting speeds or aspiration volumes mid-run without stopping and editing the workflow JSON.
* **Dynamic UI:** Possible Integration of Robotic hand with the biopipettor and other required machine's for a much seemeless protocol. This may help maintain a more sterile environment.
