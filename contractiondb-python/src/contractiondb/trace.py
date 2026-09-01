    

import numpy as np
import datetime

from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes   import Axes

from .peak import Peak
from .data_utils import running_min, running_max, running_avg

class Trace:
    id:      int    =0
    name:    str
    plate:   str
    well:    str
    timestamp:       datetime.datetime
    time:            np.ndarray= np.array([])
    twitch_force:    np.ndarray= np.array([])
    twitch_distance: np.ndarray= np.array([])
    raw_distance:    np.ndarray= np.array([])
    raw_value:       np.ndarray= np.array([])
    baseline:        np.ndarray = np.array([])
    run_avg:         np.ndarray = np.array([])
    run_min:         np.ndarray = np.array([])
    run_nei:         np.ndarray = np.array([])
    run_max:         np.ndarray = np.array([])
    run_noise:       np.ndarray = np.array([])
    peaks:             [Peak] = []
    position:             int = 0
    time_resolution_ms: float = 20.0
    min_px:             float = 60.0
    max_px:             float = 120.0
    peak_thresh:        float = 0.6
    noise_abs:          float = 0.2
    noise_thresh:        float = 3
    nei_len:              int = 21
    run_min_len:           int = 501
    run_max_len:           int = 201
    run_nei_len:           int = 31
    run_noi_len:           int = 31
    run_avg_len:           int = 3
    run_avg_slow_len:      int = 21
    run_base_len:          int = 201  # approx 7*run nei len

    def __init__(self,data):        
        for key, value in data.items():
            setattr(self, key, value)



    def filter_min_max(self):
        self.raw_distance[self.raw_distance < self.min_px]=np.nan
        self.raw_distance[self.raw_distance > self.max_px]=np.nan
        
    def N(self)->int:
        return len(self.raw_distance)

    def find_peaks(self)-> list[Peak]:
        #        
        self.run_avg    = running_avg(self.raw_distance, self.run_avg_len)
        #
        self.run_min    = running_min(self.run_avg, self.run_min_len)
        self.run_max    = running_max(self.run_avg, self.run_max_len)
        self.baseline   = self.running_base(self.run_base_len)
        #peak (freq) filter
        self.run_nei    = running_min(self.run_avg, self.run_nei_len)        
        # analyse noise, ignoring peaks
        self.run_noi    = self.running_noise(self.run_noi_len)
        
        #
        dT = (self.run_max-self.run_min) * self.peak_thresh
        dN = self.run_noi * self.noise_thresh

        dA = np.ones(len(self.run_max)) * self.noise_abs
        
        dCut = np.maximum(dT, dN)
        dCut = np.maximum(dCut, dA)

        self.run_thresh = self.run_max - dCut
        
        bMin = (self.run_avg == self.run_nei) * (self.run_avg < self.run_thresh)
        #
        peak_pos= np.where(bMin)[0];
        #
        #
        print(f"found {len(peak_pos)} peaks of trace {self.id}")
        #
        self.peaks.clear()

        win=int((self.run_nei_len-1)/2)
        #
        for i in range(1, len(peak_pos)):
            idx       =peak_pos[i]
            p         =Peak()
            p.trace_id=self.id
            p.frame   =idx
            p.base    =round(self.baseline[idx],3)
            p.dist    =self.run_avg[idx]
            p.height  =round(p.base - p.dist,3)
            p.time    =round(self.time[idx],3)
            p.d20     = p.base - p.height*0.2
            p.d80     = p.base - p.height*0.8
            p.data    = self.run_avg[idx-win:idx+win]
            if i>0:
              p.rr=(idx-peak_pos[i-1])*self.time_resolution_ms            
            p.analyze() 
            self.peaks.append(p)
            
        return self.peaks



    def plot(self, fig: Figure = None, axs: Axes=None) ->Figure:
        #
        if fig is None:
            fig = plt.figure()
            axs = fig.subplots()

        for l in axs.lines :
            l.remove()

        axs.plot(self.time, self.raw_distance, "sc")
        axs.plot(self.time, self.run_avg, "-k")
        axs.plot(self.time, self.run_min, ":g")
        axs.plot(self.time, self.baseline, "--r")
        axs.plot(self.time, self.run_thresh, "-.y")
        axs.plot(self.time, self.run_nei, "-.m")
        x,y=self.peak_positions()        
        #plt.plot(x, y, "^k")
        axs.plot(x, y, "^k")
        #
        axs.set_title(f"Plate {self.plate}, Well {self.well}\nMeasurement {self.name} {self.id}")
        axs.set_xlabel("Time / s")
        axs.set_ylabel("Raw distance / pixel")
        plt.show()
        return fig
        
    
    def peak_positions(self)-> (np.ndarray, np.ndarray):
        x = np.zeros(len(self.peaks))
        y = np.zeros(len(self.peaks))
        for i in range(0,len(self.peaks)):
            idx = self.peaks[i].frame
            x[i] = self.time[idx]
            y[i] = self.run_avg[idx]
        return x,y
    
    

    def base(self)->float:
        return np.nanmean(self.running_base(self.run_base_len))

    def min(self)->float:
        return np.nanmin(self.raw_distance)

    def max(self)->float:
        return np.nanmax(self.raw_distance)

    def avg(self)->float:
        return float(np.nanmean(self.raw_distance))

    def std(self)->float:
        return float(np.nanstd(self.raw_distance))

    def running_min(self, size: int)->np.ndarray:
        return running_min(self.raw_distance, size)

    def running_max(self, size)->np.ndarray:                        
        return running_max(self.raw_distance, size)

    def running_avg(self, size)->np.ndarray:
        return running_avg(self.raw_distance, size)

    def running_base(self, size)->np.ndarray:
        data = self.running_avg(self.run_avg_slow_len)        
        return running_max(data, size)
    
    def running_noise(self, size)->np.ndarray:
        data   =  self.raw_distance-self.baseline
        data[data <0]=np.nan
        return running_avg(data, size)        