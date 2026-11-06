# Machine Profiles & Multi-Station Setup

RoboLab supports 3 physical liquid handler workstations with independent calibrations:

| Station Profile ID | Head Configuration | Active Workstation | Calibrated Heights File |
|---|---|---|---|
| `machine_1_8x1000` | 8-Channel 1000 µL | Workstation 1 | `config/machine_profiles/machine_1_8x1000/heights.json` |
| `machine_2_1_10ul` | Single 1-10 µL | Workstation 2 | `config/machine_profiles/machine_2_1_10ul/heights.json` |
| `machine_3_300ul` | Single 300 µL | Workstation 3 | `config/machine_profiles/machine_3_300ul/heights.json` |

## Local Station Identity (.machine_id)
Each PC stores its station identifier in `.machine_id` (git-ignored). This prevents cross-overwrites when pulling git updates.
