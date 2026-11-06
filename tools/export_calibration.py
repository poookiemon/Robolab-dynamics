"""Maintenance tool to inspect and export active machine profile calibrations."""

import sys
from robolab_gui.configuration.machine_profiles import MachineProfileService


def main():
    service = MachineProfileService()
    active = service.active_profile
    print(f"Active Station ID: {active.id}")
    print(f"Station Name: {active.display_name}")
    print(f"Head Configuration: {active.head.description}")
    print("\nCalibrated Heights:")
    for k, v in active.calibrated_heights.items():
        print(f"  {k:28s} : {v:.2f} mm")


if __name__ == "__main__":
    main()
