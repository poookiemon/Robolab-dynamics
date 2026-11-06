# Installation Guide

## Requirements
- Python 3.9, 3.10, 3.11, or 3.12
- macOS, Linux, or Windows (Windows required for physical Biohit USB hardware connection)

## Development Setup

```bash
git clone https://github.com/poookiemon/Robolab-dynamics.git
cd Robolab-dynamics
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[analysis,hardware,test]"
```
