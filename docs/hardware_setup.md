# Hardware Setup Guide

## InstrumentLib Driver & Connection
On Windows workstations controlling physical liquid handlers:
1. Ensure the Biohit/Sartorius USB cable is plugged into the workstation.
2. Install `pythonnet` to bridge to the .NET InstrumentLib assembly:
   ```bash
   pip install pythonnet
   ```
3. The robot powers on with axes homed. RoboLab enforces an uninitialized interlock state until the operator initializes the head from the UI.
