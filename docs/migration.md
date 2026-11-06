# Migration Guide

## From Monolithic GUI to robolab-gui v3.0

- **CLI Access**: Run `robolab-gui` or `python -m robolab_gui`.
- **Existing Scripts**: Old scripts calling `python main.py` run seamlessly.
- **Legacy Fallback**: If needed, `python main.py --legacy` launches the legacy monolithic interface.
- **Protocols**: All existing protocols in `protocols/` remain 100% compatible.
