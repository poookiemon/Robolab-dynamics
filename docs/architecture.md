# System Architecture

RoboLab Dynamics is structured according to pyOpenSci standards using an isolated layered architecture:

```
[ UI Layer (Tkinter / Qt) ]
            │
[ Execution Layer (Engine, RunState, TipTracker, LiquidTracker, Timer) ]
            │
[ Protocol & Planning Layer (Catalog, Validation, Planner, Builders) ]
            │
[ Configuration Layer (Paths, StationIdentity, MachineProfiles, Calibration) ]
            │
[ Domain & Geometry Layer (Deck, Slots, Labware, Coordinates, NozzleLayout) ]
            │
[ Hardware Abstraction Layer (HardwareInterface -> BiohitHardware / SimulatedHardware) ]
```

## Guiding Principles
1. **Decoupled Engine**: The core pipetting sequence engine runs independently of Tkinter or Qt.
2. **Zero Connection on Import**: Loading the package never communicates with USB/COM ports or initializes .NET DLLs.
3. **Multi-Station Isolation**: Station profiles and heights are kept completely segregated so Machine 1, 2, and 3 never overwrite each other.
