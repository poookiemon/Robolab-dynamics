import numpy as np
from typing import Tuple, Optional, Union, Sequence, List


class Peak:
    trace_id:       int=0
    frame:          int=0
    base:         float=0.0
    height:       float=0.0
    width:          int=0
    rr:           float=0.0
    v_contract:   float=0.0
    v_relax:      float=0.0
    t1:           float=0.0
    t2:           float=0.0
    t3:           float=0.0
    t4:           float=0.0
    d20:          float=0.0  
    d80:          float=0.0 
    height_fit:   float=0.0
    raw:          float=0.0      #after smoothing
    raw_dist:     float=0.0      #raw value
    time:         float=0.0
    dist: Optional[np.ndarray] = np.array([])

    def __init__(self, data = {'frame_index':0} )  :        
        for key, value in data.items():
            setattr(self, key, value)

    def analyze(self):
        self.t1=0.0

    def plot(self):
        xx=[self.time[0], self.time[-1]]
        plt.plot(self.time, self.dist, "sc")
        plt.plot(xx, [self.d20,self.d20], ":g")
        plt.plot(xx, [self.d80,self.d80], "--r")
        plt.plot([0,0] , [self.base, self.base-self.height], "-.y")
        #        
        plt.plot(0, self.base-self.height, "^k")
        #
        plt.title(f"Plate {self.plate}, Well {self.well}\nMeasurement {self.name} {self.id}")
        plt.xlabel("Time / s")
        plt.ylabel("Raw distance / pixel")
        plt.show()