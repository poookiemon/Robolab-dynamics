# Contributing to RoboLab Dynamics

Thank you for contributing to RoboLab! Please follow these guidelines:

## Code Standards
- Adhere to PEP 8 style conventions.
- Package code lives exclusively in `src/robolab_gui/`. Never put loose scripts in the root directory.
- `__init__.py` files must NEVER initiate hardware connections or bind to external DLLs on import.
- Pure business logic, geometry transforms, and protocol models must remain testable using `SimulatedHardware`.

## Pull Request Guidelines
1. Create a feature branch from `main`.
2. Ensure all unit and regression tests pass:
   ```bash
   pytest
   ```
3. Update `CHANGELOG.md` with relevant details.
4. Submit PR for review.
