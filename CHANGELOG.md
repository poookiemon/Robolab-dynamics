# Changelog

All notable changes to the RoboLab platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-11-06

### Added
- pyOpenSci compliant modular `src/robolab_gui/` package architecture.
- Multi-machine profile management (`machine_1_8x1000`, `machine_2_1_10ul`, `machine_3_300ul`) in `config/machine_profiles/`.
- Local `.machine_id` workstation identification hierarchy.
- Tim's Slot-by-Slot Tip Z-Verification Tool with assisted visual jogging and direct profile persistence.
- Interactive error recovery modal with user-directed clearance targeting.
- Active session tip memory (virtual tip remapping `A1..H1 -> A2..H2 ...`) across protocol executions.
- Weighted dynamic execution countdown timer in `HHh MMm SSs` with speed factor scaling and pause compensation.
- Automated HTML run dashboards and CSV audit logs generated alongside session logs in `logs/`.
- Glove-friendly cleanroom high-contrast touch UI mode.
- Symmetrical 8-channel centering ($Y=84.52\text{ mm}$) eliminating rack divider wall collisions during multi-tip pickups.

### Changed
- Transitioned root packaging metadata to PEP 517/518/621 standard `pyproject.toml`.
- Replaced monolithic coupling with headless `ExecutionEngine` decoupled from GUI.
- Archived over 50 legacy root patch scripts into `archive/legacy_scripts/`.
- Organized active protocols into titled machine subfolders (`Machine 1 - 8x1000 uL`, `Machine 2 - 1-10 uL`, `Machine 3 - 300 uL`, `Diagnostics and Tests`).
