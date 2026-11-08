"""Launch the complete RoboLab Dynamics GUI Application."""

import sys
import os

repo_root = os.path.dirname(os.path.abspath(__file__))
legacy_dir = os.path.join(repo_root, "Biohit-Automated-Pipettor-GUI")
src_dir = os.path.join(repo_root, "src")

for p in (legacy_dir, src_dir, repo_root):
    if p not in sys.path:
        sys.path.insert(0, p)

os.chdir(legacy_dir)
import lims_master_gui


def main():
    lims_master_gui.launch()


if __name__ == "__main__":
    main()
