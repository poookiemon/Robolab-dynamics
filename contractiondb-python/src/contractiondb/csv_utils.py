import datetime
import os
import re
import warnings
from collections import defaultdict
from typing import Dict, Sequence, List, Tuple, Optional
import numpy as np
from .trace import Trace
from .regex import PLATE_REGEX, MEA_REGEX, EXP_REGEX, DEVICE_REGEX



def filename_to_experimentname(fname: str)->str:
    filename=os.path.basename(fname)
    filepath=os.path.dirname(fname)
    path = os.path.normpath(filepath)
    dirs=path.split(os.sep)
    expName=dirs[-1]
    if re.fullmatch(EXP_REGEX, expName):
      plate = expName[:9]
    else:
      errstr=f"No experiment name matching {EXP_REGEX} found in {fname}. Check Folder naming"
      raise ValueError(errstr)
    return plate

def filename_to_measurementname(fname: str)->str:
    filename=os.path.basename(fname)
    (fBase, fExt) = os.path.splitext(filename)
    if re.fullmatch(MEA_REGEX, fBase):
      meaName = fBase[:9]
    else:
      errstr='No valid Measurement name matching {reg} found in {name}. Check Folder naming'.format(reg=PLATE_REGEX, name=fname)
      raise ValueError(errstr)

    return meaName

def filename_to_devicename(fname: str)->str:
    p = re.compile(DEVICE_REGEX)
    res = p.search(fname)
    device="root"
    if res :
        device = res.group(1)
    return device


def create_csvs(traces: Sequence[Trace], out_directory: str = "."):
    plates = {t.plate for t in traces}

    # tables[plate][name] is list of all measurements of that plate and name
    tables: Dict[str, Dict[str, List[Trace]]] = {}
    for plate in plates:
        tables[plate] = defaultdict(list)

    for t in traces:
        tables[t.plate][t.name].append(t)

    for plate in plates:
        os.makedirs(os.path.join(out_directory, plate), exist_ok=True)
        for name, data in tables[plate].items():
            create_single_csv(data, os.path.join(out_directory, plate, name) + ".csv")


def create_single_csv(traces: Sequence[Trace], out_filename: str) -> None:
    wells = [c + d for c in "ABCDEFGH" for d in "123456"]
    if not all(t.plate == traces[0].plate for t in traces):
        raise ValueError(f"Expected data of a single plate, got {set(t.plate for t in traces)}")
    if not all(t.name == traces[0].name for t in traces):
        raise ValueError(f"Expected data of a measurement, got {set(t.name for t in traces)}")

    # find time data
    for t in traces:
        if t.time is not None:
            time = t.time
            break
    else:
        raise ValueError("No time data found in any of the measurements")
    distance_data = {t.well: t.raw_distance for t in traces}

    # create full data array
    data = np.full((time.size, 49), -1, dtype=float)
    data[:, 0] = time
    for i, well in enumerate(wells, start=1):
        if distance_data.get(well) is not None:
            data[:, i] = distance_data[well]
        else:
            data[:, i] = np.full(time.shape, -1)
            warnings.warn(f"No data found for well {well}, filling with -1 (while creating {out_filename})")

    # save to csv file
    np.savetxt(out_filename, data, delimiter=",", fmt="%1.2f")


def read_traces_from_csv(
        csv_filename: str,
        plate: Optional[str] = None,
        name: Optional[str] = None,
        timestamp: Optional[datetime.datetime] = None
) -> Tuple[Trace]:

    if not os.path.isfile(csv_filename):
        raise FileNotFoundError(f"No such file: {csv_filename}")

    if plate is None:
        parent_dir = os.path.split(os.path.split(os.path.abspath(csv_filename))[0])[-1]
        if re.fullmatch(PLATE_REGEX, parent_dir):
            plate = parent_dir[:9]
        else:
            raise ValueError(
                "No plate name found. Either specify it explicitly, or make sure the file is in the correct directory"
            )

    if name is None:
        name = os.path.splitext(os.path.split(csv_filename)[-1])[0]

    if timestamp is None and re.fullmatch(PLATE_REGEX, name):
        timestamp_from_filename = datetime.datetime.strptime(name[:8], '%Y%m%d')
        timestamp_from_file_creation = datetime.datetime.fromtimestamp(os.path.getctime(csv_filename))
        if timestamp_from_file_creation.date() != timestamp_from_filename.date():
            timestamp = timestamp_from_filename  # only contains the date, not time
        else:
            timestamp = timestamp_from_file_creation  # only correct if file was not moved since creation day

    wells = [c + d for c in "ABCDEFGH" for d in "123456"]
    
    data = np.loadtxt(csv_filename, delimiter=",", dtype=float)
    
    time = data[:, 0]
    time -= time[0]

    traces = []
    # 'id', 'idEvent', 'name', 'plate', 'well', 'position', 'timestamp', 'time', 'twitch_force', 'twitch_distance', 'raw_distance', 'raw_value', and 'baseline'
    for i, well in enumerate(wells, start=1):
        t=Trace({'id':-1, 'name': name, 'plate': plate, 'well': well, 'position':i, 'timestamp':timestamp, 'time':time})
        t.raw_distance=data[:, i]
        traces.append(t)
            
        

    return tuple(traces)
