# RoboLab Dynamics (robolab-gui)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![pyOpenSci](https://img.shields.io/badge/pyOpenSci-Compliant-brightgreen.svg)](https://www.pyopensci.org/)

Modular automated liquid handling, protocol execution, and data analysis platform for Biohit/Sartorius liquid handlers.

---

## Key Features

- **Multi-Machine Architecture**: Independent station calibrations and profiles (`Machine 1: 8×1000 µL`, `Machine 2: 1-10 µL`, `Machine 3: 300 µL`).
- **Kinematics Engine**: Symmetrical 8-channel centering ($Y=84.52\text{ mm}$) and partial-tip pickups (A-E 5 tips) with zero rack divider wall collisions.
- **Tim's Z-Verification Tool**: Assisted visual jog workflow taking a tip from Slot 4 to verify and edit target Z depths per slot with direct profile persistence.
- **Interactive Error Recovery**: User-directed clearance unjam targeting operator-selected slots/wells with step retry logic.
- **Active Session Tip Memory**: Virtual tip remapping (`A1..H1 -> A2..H2 ...`) across runs without modifying protocol JSON files.
- **Weighted Dynamic Time Estimation**: Live countdown timer in `HHh MMm SSs` format with speed factor scaling and pause compensation.
- **Automated Reporting**: Formatted HTML dashboards and CSV audit logs generated alongside real-time streaming session logs.
- **Glove-Friendly Touch UI**: High-contrast cleanroom mode designed for biosafety cabinet touchscreens.

---

## Installation

### From Source (Development Mode)

```bash
git clone https://github.com/poookiemon/Robolab-dynamics.git
cd Robolab-dynamics
pip install -e .
```

### With Optional Dependencies

```bash
# With analysis and plotting libraries (pandas, seaborn, scipy)
pip install -e ".[analysis]"

# With full hardware drivers on Windows
pip install -e ".[hardware]"

# With test dependencies
pip install -e ".[test]"
```

---

## Running RoboLab GUI

### Modern CLI Entry Point:
```bash
robolab-gui
```

### Module Execution:
```bash
python -m robolab_gui
```

### Compatibility Launcher:
```bash
python main.py
```

To run the legacy monolithic GUI:
```bash
python main.py --legacy
```

---

## Package Architecture (pyOpenSci Standards)

```text
Robolab-dynamics/
├── pyproject.toml              # Single source of packaging metadata (PEP 621)
├── README.md                   # System documentation and usage guide
├── LICENSE                     # MIT Open Source License
├── main.py                     # Transitional compatibility launcher
│
├── src/
│   └── robolab_gui/            # Core importable package
│       ├── domain/             # Machine profiles, deck layout, labware definitions
│       ├── geometry/           # Coordinate transforms, nozzle layout, safe clearances
│       ├── hardware/           # Driver interfaces, Biohit wrapper, simulated hardware
│       ├── configuration/      # Paths, station identity, machine profiles, calibration
│       ├── protocols/          # Protocol models, catalog, validation, planning, builders
│       ├── execution/          # Engine, run state, tip memory, meniscus tracking, recovery
│       ├── reporting/          # Session logs, audit trails, HTML dashboards, CSV export
│       ├── integrations/       # FOC48 reader pipeline, ContractionDB client
│       ├── analysis/           # Signal processing, dose response curves, quality control
│       ├── ui/                 # Tkinter and PyQt6 user interfaces
│       └── resources/          # Bundled machine profiles, labware, and protocol templates
│
├── tests/                      # Unit, integration, and regression test suites
├── docs/                       # Architecture, hardware setup, and calibration guides
├── tools/                      # Maintenance and calibration export tools
└── archive/                    # Excluded legacy scripts and superseded protocols
```

---

## License

RoboLab Dynamics is open source software licensed under the [MIT License](LICENSE).
