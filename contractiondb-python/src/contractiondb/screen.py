from .classes import Compound, Experiment

class Screen:
    id: int
    name: str
    nExperiment: int = 0
    nCompound: int=0
    def __init__(self):
        self.experiment: []
        self.compound: []

    def addCompound(self, compound: Compound):
        self.compound.append(compound)

    def addExperiment(self, experiment: Experiment):
        self.experiment.append(experiment)