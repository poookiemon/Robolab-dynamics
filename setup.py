from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="robolab-dynamics",
    version="1.0.0",
    description="Biohit Automated Pipettor GUI & LIMS Controller",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Robolab Dynamics Team",
    url="https://github.com/poookiemon/Robolab-dynamics",
    packages=["robolab_gui"],
    package_dir={"robolab_gui": "Biohit-Automated-Pipettor-GUI"},
    package_data={
        "robolab_gui": [
            "*.json",
            "labware/*.json",
            "protocols/*.json",
            "assets/*",
        ]
    },
    include_package_data=True,
    install_requires=[
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "seaborn",
        "plotly",
        "ttkbootstrap",
        "watchdog",
        "Pillow",
    ],
    extras_require={
        "full": [
            "PyQt6",
            "PyQt6-WebEngine",
            "pyvista",
            "pyvistaqt",
            "pythonnet",
        ]
    },
    entry_points={
        "console_scripts": [
            "robolab-gui=robolab_gui.lims_master_gui:launch",
            "biohit-gui=robolab_gui.lims_master_gui:launch",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
)
