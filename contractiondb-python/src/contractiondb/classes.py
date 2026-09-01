import datetime
from typing import NamedTuple, Optional

import numpy as np

class Well(NamedTuple):
    id: int
    idPlate: int
    name: str
    plate: str

class Compound(NamedTuple):
    name: str
    description: Optional[str]
    cas: Optional[str]
    salt: Optional[str]
    formula: Optional[str]
    smiles: Optional[str]
    smiles_clean: Optional[str]
    id: int = 0
    mw: Optional[float] = 0

class Measurement(NamedTuple):
    id: int
    idPlate: int
    name: str
    plate: str

class Experiment(NamedTuple):
    id: int
    idPerson: int
    name: str
    plate: str
    #def __init__(self):
    #    self.well = []








    