import numpy as np

def running_max(data: np.ndarray, size: int)->np.ndarray:                        
        win = int((size-1)/2)        
        ret = np.empty(len(data))
        ret[:]=np.nan
        #
        for i in range(win, len(data)-win):
              ret[i] = np.nanmax(data[i-win:i+win])            
        #
        ret[:win ] = np.nanmax(data[:size ])
        ret[-win:] = np.nanmax(data[-size:])        
        return ret


def running_min(data: np.ndarray, size: int)->np.ndarray:                        
        win = int((size-1)/2)
        ret = np.empty(len(data))
        ret[:]=np.nan
        #
        for i in range(win, len(data)-win):
           ret[i]  = np.nanmin(data[i-win:i+win])            
        ret[:win ] = np.nanmin(data[:size ])
        ret[-win:] = np.nanmin(data[-size:])        
        return ret

def running_avg(data: np.ndarray, size: int)->np.ndarray:
        win = int((size-1)/2)
        ret = np.empty(len(data))
        ret[:]=np.nan
        csum = np.nancumsum(data)
        ret[:win]  = np.nanmean(data[:size ])
        ret[-win:] = np.nanmean(data[-size:])
        ret[win+1:-win] = (csum[size:]-csum[:-size])/size
        return ret