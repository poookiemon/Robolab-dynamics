from .classes import Compound, Experiment
from   mysql.connector import MySQLConnection

class Solution:
    id: int
    name: str
    description: str
    compound: [Compound]
    __db: MySQLConnection

    def __init__(self, db):


    def get(self, solvents: [Solution], solutes: [Compound]) -> Solution:



    def new(self, solvents: [Solution], solutes: [Compound]) -> Solution:
        self=Solution();

        self.compound.append(compound)

        return self

