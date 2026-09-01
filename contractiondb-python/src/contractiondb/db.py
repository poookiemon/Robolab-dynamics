import datetime
import re
import itertools
import numpy as np
from typing import Tuple, Optional, Union, Sequence, List
import mysql.connector
from   mysql.connector import MySQLConnection
from   mysql.connector.locales.eng import client_error
import xml.etree.ElementTree as ET

#import MySQLdb

#import local classes
from .csv_utils import read_traces_from_csv, filename_to_experimentname, filename_to_measurementname, filename_to_devicename
from .classes import Experiment, Well, Compound
from .trace import Trace
from .peak import Peak
from .screen import Screen
from .regex import DATE_REGEX, PLATE_REGEX, WELL_REGEX, SUFFIX_REGEX, CAS_REGEX, EXP_REGEX, MEA_REGEX

print(f"name of package {__name__}")


class ContractionDB:
   
    MySQLConnection
    db_time_factor: int=1000
    db_time_factor: int=1000
    db_dist_factor: int=100

    def __init__(self, *, host: str, port: Optional[int] = None, database: str, user: str, password: str, auth_plugin: Optional[str]='mysql_native_password'):
        """Wrapper for a MySQL Connector to the ContractionDB"""        
        kwargs= {
            "host": host,
            "database": database,
            "user": user,
            "password": password,
            "auth_plugin": auth_plugin,
            "autocommit": True
        }
        
        if port is not None:
            kwargs["port"] = port

        self.__file__ = __file__
        
        #in MySQL8 the default changed from native_password to ssh
        #this is to restore the old defualt behaviour
        #if auth_plugin is not None:
         #   kwargs["auth_plugin"] = auth_plugin
            
        self.__db = mysql.connector.connect(**kwargs)

    def get_cursor(self):
        """Run the given SQL query, return the results, column names, and last row id"""
        return self.__db.cursor()

    def execute_sql(self, query: str) -> Tuple[Tuple, str, int]:
        """Run the given SQL query, return the results, column names, and last row id"""
        return self.__execute_sql(query)
    
    def __execute(self, query: str) -> Tuple[Tuple, str, int]:
        return self.__execute_sql(query)

    def __execute_sql(self, query: str) -> Tuple[Tuple, str, int]:
        """Run the given SQL query, return the results, column names, and last row id"""
        #print(query)
        cursor = self.__db.cursor()
        try:
            cursor.execute(query)
            #print(query)
            return tuple(cursor), cursor.column_names, cursor.lastrowid
        except:
            print(f"failed to execute {query}")
        finally:
            cursor.close()

    def __execute_proc(self, proc: str, ain: Tuple, aout: Tuple ) -> Tuple:
        """Run the given SQL query, return the results, column names, and last row id"""

        #Connector/Python 1.2.1 and up permits parameter types to be specified. To do
        # this, specify a parameter as a two-item tuple consisting of the parameter 
        # value and type. Suppose that a procedure sp1() has this definition: 
        #args = ('ham', 'eggs', (0, 'CHAR'))
        #result_args = cursor.callproc('sp1', args)
        #print(result_args[2])
        # ret=cursor.callproc('measurementData', ('20230101x', '20230101d',0,0))
        # ret=cursor.callproc('measurementData', (('20230101x'),('20230101d'),(0,'int'),(0,'int')))
        #flatten args
        #args=[]
        #args.extend(ain)
        #args.extend(aout)        
        args = tuple(itertools.chain.from_iterable((ain, aout)))
        cursor = self.__db.cursor()
        try:
            ret = cursor.callproc(proc, args)
        finally:
            cursor.close()
        return ret[len(ain):]

    def execute_proc(self, proc: str, argin: Tuple, argout: Tuple ) -> Tuple:
        return self.__execute_proc(proc, argin, argout)
    

    def __insert_row(self, table: str, columns: Sequence[str], values: Sequence) -> int:
        """Insert the given values, returning the row id"""
        converted_values: List[str] = []
        
        for value in values:
            if isinstance(value, int) or isinstance(value, np.int64):
                value = str(value)
            if isinstance(value, float):
                value = str(value)
            #
            if isinstance(value, datetime.datetime):
                value = repr(value.strftime('%Y-%m-%d %H:%M:%S'))
            elif isinstance(value, str):
                value = repr(value)
            elif isinstance(value, bytes):
                value = "0x" + value.hex()
            elif value is None:
                value = "NULL"
            else:
                print(f"value {value} type {type(value)}")
                raise ValueError(f"No conversion implemented for inserting value of type {type(value)}")

            converted_values.append(value)

        sql_str=f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({", " . join(converted_values)} )'
        #print(sql_str)
        #row_id=0
        row_id = self.__execute_sql(sql_str)[2]
        self.__db.commit()
        return row_id

    def __insert_update_row(self, table: str, columns: Sequence[str], values: Sequence, update: Sequence[str]) -> int:
        """Insert the given values, returning the row id"""
        my_dict = dict(zip(columns, values))
        update_keys:      List[str] = []

        for key in my_dict.keys():
            val=my_dict[key]
            if isinstance(val, float) and np.isnan(val):
                #print(f"replace nan with NULL")
                my_dict[key] = "NULL"
            elif isinstance(val, int) or isinstance(val, np.int64) or isinstance(val, float):
                my_dict[key] = str(val)
            elif isinstance(val, datetime.datetime):
                my_dict[key] = repr(val.strftime('%Y-%m-%d %H:%M:%S'))
            elif isinstance(val, str):
                my_dict[key] = repr(val)
            elif isinstance(val, bytes):
                my_dict[key] = "0x" + val.hex()
            elif val is None:
                my_dict[key] = "NULL"
            else:
                print(f"value {val} type {type(val)}")
                raise ValueError(f"No conversion implemented for inserting value of type {type(val)}")

            if key in update:
                # key=new.key does not work in mariaDB
                update_keys.append(f"{key} = {my_dict[key]}")

        sql_str = f"""INSERT INTO {table}      ({", ".join(my_dict.keys())} ) VALUES ({", ".join(my_dict.values())}) 
                       on duplicate key update {", ".join(update_keys)} """

        #print(sql_str)
        # row_id=0
        row_id = self.__execute_sql(sql_str)[2]
        self.__db.commit()
        return row_id

    @staticmethod
    def __parse_binary(buffer: Optional[bytes], factor: float = 1, dtype: np.dtype = np.uint16) -> Optional[np.ndarray]:
        """
        Parse a MySQL MEDIUMBLOB value as the given data type, then convert to float and multipy by the given factor
        """
        if buffer is None:
            return None

        return np.frombuffer(buffer, dtype).astype(float) * factor

    @staticmethod
    def __array_to_bytes(array: np.ndarray, factor: float = 1, dtype: np.dtype = np.uint16) -> bytes:
        """Multiply by the given factor, round to integers, convert to given data type, then to bytes"""
        return (array * factor).round(decimals=0).astype(dtype).tobytes()

    @staticmethod
    def __parse_date(date: Union[str, datetime.date]) -> datetime.date:
        """Parse the given value as a `datetime.date`. Strings are parsed according to ISO 8601 (YYYY-MM-DD)."""
        if isinstance(date, str):
            if not re.fullmatch(DATE_REGEX, date):
                raise ValueError(f"Expected a date like 'YYYY-MM-DD', got {date!r}")
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        if not isinstance(date, (datetime.date, str)):
            raise ValueError(f"Expected a string or datetime.date, got {date!r}")
        return date

        

    def get_peaks_of_trace(self, trace: Union[int, Trace]) -> Tuple[Peak]:
        """
        Get all peaks of a measurement.
        If measurement is an int, the `idEvent` field from the `forces` table is assumed (`Measurement.id`).
        """
        if not isinstance(trace, (Trace, int)):
            raise ValueError(f"Expected an integer or Trace, got {trace!r}")
        if isinstance(trace, Trace):
            trace = trace.id

        results, _, _ = self.__execute_sql(f"""
            SELECT 
                idEvent AS trace_id,
                frame AS frame,
                base,
                height,
                width,
                RR,
                vContract,
                vRelax,
                t1,
                t2,
                t3,
                t4,
                height_fit
            FROM peak
            WHERE idEvent = {trace}
        """)

        return tuple(Peak(*result) for result in results)


    def get_screens(self) -> Tuple[Screen]:

        query_str = f"""
        SELECT s.idScreen as id, s.name, count(distinct idCompound) as nCompound, count(distinct idEvent) as nExperiment
        FROM screen s left join screen_compound  using(idScreen) left join screen_event using(idScreen)"""
        rows, cols, _ = self.__execute_sql(query_str)
        return tuple(self.__result_to_screen(row, cols) for row in rows)

    def get_experiments(
            self,
            *,
            plate: Optional[str] = None,
            start_date: Optional[Union[str, datetime.date]] = None,
            end_date: Optional[Union[str, datetime.date]] = None,
    ) -> Tuple[Experiment]:
        """Get all measurements matching the criteria."""
        filters = []
        if plate is not None:
            if not isinstance(plate, str) or not re.fullmatch(PLATE_REGEX, plate):
                raise ValueError(
                    f"Expected a plate ID like '20200101a' or '20200101a_comment', got {plate!r}"
                )
            filters.append(f"experiment.name LIKE '{plate}%'")
        
        if start_date is not None:
            start_date = ContractionDB.__parse_date(start_date)
            filters.append(f"plateMeasurementEvent.date >= '{start_date.isoformat()}'")

        if end_date is not None:
            end_date = ContractionDB.__parse_date(end_date)
            filters.append(f"plateMeasurementEvent.date <= '{end_date.isoformat()}'")        

        filter_str = "WHERE " + " AND ".join(filters) if filters else ""

        query_str = f"""
          SELECT x.idEvent as id, x.name AS name, x.idPerson as idPerson, l.name as plate          
          FROM experiment x join event e using (idEvent) join labware l using (idLabware)
          {filter_str } 
          """

        rows, cols, _ = self.__execute_sql(query_str)

        return tuple( self.__result_to_experiment(row, cols) for row in rows)


    def get_peak_summary(self, experiment_name: str, well: str):
    
        """
        Return average peak heights grouped by event, for a given experiment and well.
        """
    
        query_str = """
            SELECT x.name AS experiment,
            m.name AS measurement,
            l.name,
            e.date,
            ROUND(AVG(peak.height), 2) AS avg_peak_height
            FROM peak
            JOIN forces USING(idEvent)
            JOIN event e USING(idEvent)
            JOIN labware l USING(idLabware)
            JOIN measurement m ON e.idParent = m.idEvent
            JOIN event em ON m.idEvent = em.idEvent
            JOIN experiment x ON em.idParent = x.idEvent
            WHERE l.name = %s
            AND x.name = %s
            GROUP BY e.idEvent        
            """
        params = (well, experiment_name)
        rows, cols, _ = self.__execute_sql(query, params)
        return [dict(zip(cols, row)) for row in rows]


    
    def get_trace_ids(
            self,
            exp: Optional[str] = None,
            mea: Optional[str] = None,
            well: Optional[str] = None,
            start_date: Optional[Union[str, datetime.date]] = None,
            end_date: Optional[Union[str, datetime.date]] = None,
            measurement_suffix: Optional[str] = None,
    ) -> Tuple[Trace]:
        """Get all measurements matching the criteria."""
        filters = []
        if exp is not None and exp.lower() != 'all' :
            if not isinstance(exp, str) or not re.fullmatch(PLATE_REGEX, exp):
                raise ValueError(
                    f"Expected a mea ID like '20200101a' or '20200101a_comment', got {exp!r}"
                )
            filters.append(f"e.name LIKE '{exp}%'")

        if mea is not None and mea.lower() != 'all':
                if not isinstance(mea, str) or not re.fullmatch(MEA_REGEX, mea):
                    raise ValueError(
                        f"Expected a mea ID like '20200101a' or '20200101a_comment', got {mea!r}"
                    )
                filters.append(f"m.name LIKE '{mea}%'")

        if well is not None and well.lower() != 'all':
            if not isinstance(well, str) or not re.fullmatch(WELL_REGEX, well):
                raise ValueError(f"Expected a well ID from 'A1' to 'H6', got {well!r}")
            filters.append(f"l.name = '{well}'")

        if start_date is not None:
            start_date = ContractionDB.__parse_date(start_date)
            filters.append(f"m.date >= '{start_date.isoformat()}'")

        if end_date is not None:
            end_date = ContractionDB.__parse_date(end_date)
            filters.append(f"m.date <= '{end_date.isoformat()}'")

        if measurement_suffix is not None:
            if not isinstance(measurement_suffix, str) or not re.fullmatch(SUFFIX_REGEX, measurement_suffix):
                raise ValueError(f"Expected a suffix like '_stim0', not {measurement_suffix!r}")
            filters.append(f"me.name LIKE '%{measurement_suffix}'")

        filter_str = "WHERE " + " AND ".join(filters) if filters else ""

        query_str = (f"""
            SELECT
                w.idEvent as id,
                m.name AS name,
                e.name AS plate,
                l.name AS well,
                l.pos AS position,
                m.date AS timestamp,
                me.resolutionTime AS time_resolution_ms
            FROM forces f
            INNER JOIN event   w using(idEvent)
            INNER JOIN labware l using(idLabware)
            INNER JOIN event   m ON w.idParent = m.idEvent
            INNER JOIN measurement me ON m.idEvent = me.idEvent
            INNER JOIN event   e ON m.idParent = e.idEvent
            {filter_str}
            ORDER BY m.date
        """)
        #print(query_str)
        rows, cols, _ = self.__execute_sql(query_str)
        return tuple( self.__result_to_trace(row, cols) for row in rows)

    def get_traces(
            self,
            *,
            exp:        Optional[str] = None,
            mea:        Optional[str] = None,
            well:       Optional[str] = None,
            start_date: Optional[Union[str, datetime.date]] = None,
            end_date:   Optional[Union[str, datetime.date]] = None,
            measurement_suffix: Optional[str] = None,
    ) -> Tuple[Trace]:

        """Get all measurements matching the criteria."""
        filters = []
        if exp is not None:
            if not isinstance(exp, str) or not re.fullmatch(EXP_REGEX, exp):
                raise ValueError(
                    f"Expected a plate ID like '20200101a' or '20200101a_comment', got {plate!r}"
                )
            filters.append(f"e.name LIKE '{exp}%'")

        if mea is not None:
            if not isinstance(mea, str) or not re.fullmatch(MEA_REGEX, mea):
                raise ValueError(f"Expected a mea ID, got {well!r}")
            filters.append(f"m.name = '{mea}'")

        if well is not None:
            if not isinstance(well, str) or not re.fullmatch(WELL_REGEX, well):
                raise ValueError(f"Expected a well ID from 'A1' to 'H6', got {well!r}")
            filters.append(f"l.name = '{well}'")

        if start_date is not None:
            start_date = ContractionDB.__parse_date(start_date)
            filters.append(f"plateMeasurementEvent.date >= '{start_date.isoformat()}'")

        if end_date is not None:
            end_date = ContractionDB.__parse_date(end_date)
            filters.append(f"plateMeasurementEvent.date <= '{end_date.isoformat()}'")

        if measurement_suffix is not None:
            if not isinstance(measurement_suffix, str) or not re.fullmatch(SUFFIX_REGEX, measurement_suffix):
                raise ValueError(f"Expected a suffix like '_stim0', not {measurement_suffix!r}")
            filters.append(f"measurement.name LIKE '%{measurement_suffix}'")

        
        filter_str = "WHERE " + " AND ".join(filters) if filters else ""

        query_str=f"""
            SELECT
                w.idEvent as id,
                m.name AS name,
                e.name AS plate,
                l.name AS well,
                l.pos  AS position,
                m.date AS timestamp,                
                me.resolutionTime AS time_resolution_ms,
                f.twitchForce     AS twitch_force,
                f.twitchDistance  AS twitch_distance,
                f.rawDistance     AS raw_distance,
                f.rawValue        AS raw_value,
                f.baseLine        AS baseline
            FROM forces f
            INNER JOIN event   w using(idEvent)
            INNER JOIN labware l using(idLabware)
            INNER JOIN event   m ON w.idParent = m.idEvent
            INNER JOIN measurement me ON m.idEvent = me.idEvent
            INNER JOIN event   e ON m.idParent = e.idEvent            
            {filter_str}
            ORDER BY m.date
            """
        print(query_str)
        rows, cols, _ = self.__execute_sql(query_str)
        return tuple( self.__result_to_trace(row, cols) for row in rows)

    def get_compounds(
            self,
            *,
            name:     Optional[str] = None,
            cas:      Optional[str] = None,
            smiles:   Optional[str] = None,
            mw:       Optional[float] = None,
            mw_min:   Optional[float] = None,
            mw_max:   Optional[float] = None
    ) -> Tuple[Compound]:

        """Get all measurements matching the criteria."""
        filters = []
        if name is not None:
            filters.append(f"name LIKE '{name}%'")
        if cas is not None:
            if not isinstance(cas, str) or not re.fullmatch(CAS_REGEX, cas):
                raise ValueError(
                    f"Expected a cas ID like '500-64-7', got {cas!r}"
                )
            filters.append(f"cas LIKE '{cas}%'")
        if smiles is not None:
            filters.append(f"smiles = '{smiles}'")

        if mw is not None:
            filters.append(f"mw = {mw}")

        if mw_min is not None:
            filters.append(f"mw > {mw}")

        if mw_max is not None:
            filters.append(f"mw < {mw}")
        
        filter_str = "WHERE " + " AND ".join(filters) if filters else ""

        query_str=f"""
            SELECT
                idCompound as id,
                name,
                cas,
                mw,
                smiles,
                description,
                salt,
                formula,
                smiles_clean
            FROM compound
            {filter_str}
            ORDER BY name
            """
        #print(query_str)
        rows, cols, _ = self.__execute_sql(query_str)
        return tuple( self.__result_to_compound(row, cols) for row in rows)

    def __result_to_compound(self, row: Tuple, cols: Tuple) -> Compound:
        cmp_dict = {col: val for (col, val) in zip(cols, row)}
        return Compound(**cmp_dict)

    def get_trace(self, idMea: int, sWell: str) -> Trace:
        sql_str="""SELECT idEvent as id, measurement.time AS time, forces.rawDistance AS raw_distance"""
        row, cols, _ = self.__execute_sql(sql_str)
        return __result_to_trace(row, cols)

    def add_trace(self, t: Trace) -> None:
        sql_str = f"""SELECT m.time, f.rawDistance from forces f join event e using(idEvent) 
                      join measurement m on e.idParent=m.idEvent where f.idEvent={t.id}"""

        ret        = self.__execute_sql(sql_str)
        time, dist = self.__execute_sql(sql_str)[0][0][:]
        t.raw_distance = ContractionDB.__parse_binary(dist, 1/self.db_dist_factor)
        t.time         = ContractionDB.__parse_binary(time, 1/self.db_time_factor)


    def __result_to_trace(self, row: Tuple, cols: Tuple) -> Trace:
        dict = {col: val for (col, val) in zip(cols, row)}
        # parse binaries
        for key in dict.keys():
            if isinstance(dict[key], bytearray):
                dict[key] = dict[key].decode("utf-8")

        #if isinstance(dict["plate"], bytes):
        #    dict["plate"] = dict["plate"].decode("utf-8")
        #if isinstance(dict["well"], bytes):
        #    dict["well"] = dict["well"].decode("utf-8")
        
        if "twitch_force" in dict:
            dict["twitch_force"] = ContractionDB.__parse_binary(dict["twitch_force"], 0.01)
        if "twitch_distance" in dict:
            dict["twitch_distance"] = ContractionDB.__parse_binary(dict["twitch_distance"], 0.01)
        if "raw_distance" in dict:
            print("convert raw distance")
            dict["raw_distance"] = ContractionDB.__parse_binary(dict["raw_distance"], 0.01)
        if "raw_value" in dict:
            dict["raw_value"] = ContractionDB.__parse_binary(dict["raw_value"], 0.01)
        if "baseline" in dict:
            dict["baseline"] = ContractionDB.__parse_binary(dict["baseline"], 0.01)
        # add time                
        
        if "time" in dict :
            #use explicit timestamp from camera
            dict["time"] = ContractionDB.__parse_binary(dict["time"], 0.001, np.dtype("uint32"))
        elif "raw_distance" in dict and dict["raw_distance"] is not None:
            #generate timestamp
            n_values = len(dict["raw_distance"])
            time_resolution_ms = dict.pop("time_resolution_ms")
            #
            dict["time"] = np.arange(n_values) * time_resolution_ms / self.db_time_factor
        else:
            dict["time"]= np.array([])

        return Trace(dict)


    def __result_to_experiment(self, row: Tuple, cols: Tuple) -> Experiment:
        exp_dict = {col: val for (col, val) in zip(cols, row)}        
        return Experiment(**exp_dict)

    def __result_to_screen(self, row: Tuple, cols: Tuple) -> Experiment:
        exp_dict = {col: val for (col, val) in zip(cols, row)}
        return Experiment(**exp_dict)


    def __result_to_well(self, row: Tuple, cols: Tuple) -> Well:
        well_dict = {col: value for (col, value) in zip(cols, row)}
        return Well(**well_dict)

    
    def __upload_new_plate(self, plate: str, timestamp: datetime.datetime) -> int:
        """Create new experiment and event, return the event id, do not use"""
        raise('do not use')
        # get necessary data
        plate_labware_id = self.__execute_sql("SELECT idLabware FROM labware WHERE name = '20180315a'")[0][0][0]
        experiment_event_type = self.__execute_sql("""
            SELECT idEventType FROM eventtype WHERE name = 'experiment'
        """)[0][0][0]
        labhub_person_id = self.__execute_sql("SELECT idPerson FROM person WHERE name = 'labhub'")[0][0][0]

        # create event and experiment
        experiment_event_id = self.__insert_row(
            "event",
            ["idParent", "idEventType", "idLabware", "date"],
            [1, experiment_event_type, plate_labware_id, timestamp]
        )
        self.__insert_row(
            "experiment",
            ["idEvent", "idPerson", "name"],
            [experiment_event_id, labhub_person_id, plate]
        )
        return experiment_event_id


    
    def register_experiment(self, exp: str, plate: str) ->int:
        """Create new experiment and event, return the event id"""
        sql_string=f'SELECT registerExperiment(\'{exp}\',\'{plate}\')'        
        id = self.__execute_sql(sql_string)[0][0][0]
        if id==0:
           errstr='Could not create Experiment Id from {str}'.format(str=exp)
           raise ValueError(errstr)  
        return id


    def register_ehm_experiment(self, exp: str) ->int:
        """Create new experiment and event, return the event id"""
        sql_string=f'SELECT registerEhmExperiment(\'{str}\')'        
        id = self.__execute_sql(sql_string)[0][0][0]
        if id==0:
           errstr='Could not create Experiment Id from {str}'.format(str=exp)
           raise ValueError(errstr)  
        return id
    
    def get_id_wells(self, id: int) -> Tuple[Well]:
        """Retrieve Tuple of wellIds for a plateID"""
        sql_str=(f"""
               SELECT well.idLabware as id, plate.idLabware as idPlate, plate.name as plate, well.name as name
	           FROM labware well join labware plate on (well.idParent=plate.idLabware)  WHERE plate.idLabware = {id} order by well.row, well.col
               """)        
        #print(sql_str)
        rows, cols, _ = self.__execute_sql(sql_str)        
        return tuple( self.__result_to_well(rows, cols) for row in rows)
        #return self.__execute_proc('idWells', (id,) ,())
    

    def get_id_plate(self, exp: str) ->int:
        """Retrieve idExperiment. Returns 0 if not existing"""
        sql_query=f'SELECT getIdLabware(\'{exp}\')'
        #print(sql_query)
        _id = self.__execute_sql(sql_query)[0][0][0]
        return _id
    
    def plate_has_wells(self, id: int) ->bool:
        """Retrieve idExperiment. Returns 0 if not existing"""
        sql_string='SELECT hasWells({num})'.format(num=id)        
        nWell = self.__execute_sql(sql_string)[0][0][0]
        return nWell>0

    def plate_add_wells(self, id: int) ->int:
        """Retrieve idExperiment. Returns 0 if not existing"""
        sql_string='SELECT addWells({num})'.format(num=id)        
        nWell = self.__execute_sql(sql_string)[0][0][0]
        return nWell

    def get_id_experiment(self, exp: str) ->int:
        """Retrieve idExperiment. Returns 0 if not existing"""
        #sql_string=f'SELECT getIdExperiment("{exp}")'        
        #return self.__execute_sql(sql_string)[0][0][0]
        return self.__execute_proc('experimentData', (exp,), (0,0))[0]    

    def get_id_labware(self, exp: str) ->int:
        """Retrieve idExperiment. Returns 0 if not existing"""
        #sql_string=f'SELECT getIdExperiment("{exp}")'        
        #return self.__execute_sql(sql_string)[0][0][0]
        return self.__execute_proc('experimentData', (exp,), (0,0))[1]

    def get_id_measurement(self, exp: str, mea: str) ->int:
        """Retrieve idExperiment. Returns 0 if not existing"""
        #sql_string=f'SELECT getIdMeasurement("{exp}", "{mea}")'        
        #return self.__execute_sql(sql_string)[0][0][0]      
        return self.__execute_proc('measurementData', (exp,mea), (0,0))[0]
    
    def get_id_eventtype(self, event: str) -> int:
        """ call procedure """
        #important: Tuples with one element must have a comma!
        return self.__execute_proc('idEventType', (event,), (0,))[0]
    
    def add_measurement(self, exp: str, mea: str) ->int:
        """Create new experiment and event, return the event id"""
        id=self.__execute_proc('addMeasurement', (exp, mea),(0,))[0]
        self.__db.commit()
        return id
    
    def add_ehm_experiment(self, exp: str) ->int:
        id=self.__execute_proc('addEhmExperiment', (exp,),(0,))[0]
        self.__db.commit()
        return id
    
    def get_id_device(self, devName: str) ->int:
        """Retrieve idForces if exists"""        
        return self.__execute_proc('idDevice', (devName,),(0,))[0]

    def get_id_trace(self, idMea: int, well: str) ->int:
        """Retrieve idForces if exists"""        
        return self.__execute_proc('idForces', (idMea, well),(0,))[0]

    def get_id_traces(self, id_mea: int) -> Tuple[Trace]:
        """Retrieve idForces if exists"""
        sql_string = f"SELECT idEvent as id, name from event where idParent={id_mea}"
        rows, cols, _ = self.__execute_sql(sql_string)
        return tuple(self.__result_to_trace(row, cols) for row in rows)

    def add_forces(self, idMea: int, well: str) ->int:
        """Create new experiment and event, return the event id"""
        id=self.__execute_proc('addForces', (idMea, well),(0,))[0]
        if id==0:
           errstr='Could not add forces from idMea {num} well {str}'.format(num=idMea, str=well)
           raise ValueError(errstr)
        return id
    
    def get_id_compound(self, name: str) -> int:
        """   test  """
        ##sql_string='SELECT idCompound("{str}")'.format(str=name)
        sql_string=f"SELECT idCompound('{name}')"
        id = self.__execute_sql(sql_string)[0][0][0]        
        return id
    
    def update_compound_mw(self, id: int, mw: float):
        """   test  """
        ##sql_string='SELECT idCompound("{str}")'.format(str=name)
        sql_string=f"UPDATE compound set mw={mw} where idCompound={id}"
        self.__execute_sql(sql_string)
    
    def update_compound_cas(self, id: int, cas: str):
        """   test  """
        ##sql_string='SELECT idCompound("{str}")'.format(str=name)
        if not re.fullmatch(CAS_REGEX, cas):
            raise ValueError(f"update_compound_cas: Expected a date like {CAS_REGEX} 'DDDD-DD-DDD', got {cas!r}")
        sql_string=f"UPDATE compound set cas='{cas}' where idCompound={id}"
        self.__execute_sql(sql_string)
    
        
    def update_compound_smiles(self, id: int, smiles: str):
        """   test  """
        ##sql_string='SELECT idCompound("{str}")'.format(str=name)
        sql_string=f"UPDATE compound set smiles='{smiles}' where idCompound={id}"
        self.__execute_sql(sql_string)
        
    def update_event(self, id: int, col: str, val: int):
        """   test  """
        ##sql_string='SELECT idCompound("{str}")'.format(str=name)
        sql_string=f"UPDATE event set {col}={val} where idEvent={id}"
        #print(sql_string) 
        self.__execute_sql(sql_string)

    def update_measurement(self, _id: int, col: str, val: int):
        """   test  """
        ##sql_string='SELECT idCompound("{str}")'.format(str=name)
        sql_string=f"UPDATE measurement set {col}={val} where idEvent={_id}"
        #print(sql_string) 
        self.__execute_sql(sql_string)

    def update(self, table: str, col: str, value: any, ref_col: str, _id: int):
        """   test  """
        ##sql_string='SELECT idCompound("{str}")'.format(str=name)
        #sql = "UPDATE measurement set time=%s where idEvent=%s"
        #sql =f"UPDATE {table} set {col}='%' where {ref_col}=%"
        #
        sql = f"UPDATE {table} set {col}=%s where {ref_col}=%s"
        #
        if isinstance(value, str):
            #
            1
            #sql =f"UPDATE {table} set {col}=%s where {ref_col}=%s"
            #
        elif isinstance(value, float) or isinstance(value, int):
            #
            1
            #sql =f"UPDATE {table} set {col}=%s where {ref_col}=%s"
            #
        elif isinstance(value, float) or isinstance(value, datetime.date):
            value = value.strftime("%Y-%m-%d %H:%M:%S")
            sql = f"UPDATE {table} set {col} = %s where {ref_col} = %s "
        else:
            print(f"value {value} type {type(value)}")
            raise ValueError(f"No conversion implemented for inserting value of type {type(value)}")
        #
        #print(f"{sql} -> {value} - {_id}")
        cursor = self.__db.cursor(sql)
        cursor.execute(sql, (value,_id))
        cursor.close()
        #print(sql_string)
        #self.__execute_sql(sql_string)

    def add_compound(self, cmpd: Compound) -> int:
        """   test  """
        print(f"adding {cmpd.name}")
        id = self.get_id_compound(cmpd.name)
        if (id >0):
            print(f"compound {cmpd.name} exists with id {id}")
        else :
            sql_string=f"SELECT addCompound('{cmpd.name}')"
            print(sql_string)
            id = self.__execute_sql(sql_string)[0][0][0]

        
        return id

    def update_time(self, id: int, array: np.ndarray)->int:
        """ update """
        values = self.__array_to_bytes(array, self.db_time_factor)
        #clean_str=MySQLdb.escape_string(values)
        sql = "UPDATE measurement set time=%s where idEvent=%s"
        cursor = self.__db.cursor()
        cursor.execute(sql,(values, id))
        cursor.close()
        return self.__db.commit()

    def update_raw_distance(self, id: int, array: np.ndarray)->int:
        """ update """
        #print(f"update_raw_distance id {id}")
        values = self.__array_to_bytes(array, self.db_dist_factor)
        #clean_str=MySQLdb.escape_string(values)
        #sql_string=f"UPDATE forces set rawDistance={clean_str} where idEvent={id}"        
        sql = "UPDATE forces set rawDistance=%s where idEvent=%s"
        cursor = self.__db.cursor()
        cursor.execute(sql,(values, id))
        cursor.close()
        #sql_string='UPDATE forces set rawDistance={val} where idEvent={id}'.format(val=values, id=idEvent)
        #print(sql_string)
        #self.__execute_sql(sql_string)
        return self.__db.commit()

    def commit(self)->int:
        return self.__db.commit()

    def upload_measurement_from_xml(self, fname: str, bForce: bool = True) -> int:
        expName = filename_to_experimentname(fname)
        meaName = filename_to_measurementname(fname)
        #
        # Datum in ein datetime-Objekt konvertieren
        meaDate = datetime.datetime.strptime(meaName[0:8], '%Y%m%d').date()

        # print(f"upload measurement {expName}, {meaName} from {devName}")
        # we first need to get all well Ids associated with the experiment
        #
        id_exp = self.get_id_experiment(expName)
        if id_exp == 0:
            id_exp = self.add_ehm_experiment(expName)
        # get LabwareId
        id_mea = self.get_id_measurement(expName, meaName)
        #
        if id_mea == 0:
            id_mea = self.add_measurement(expName, meaName)
        #

        tree = ET.parse(fname)
        root = tree.getroot()

        for elem in root:
                print(elem.tag, elem.attrib, elem.text)

        # upload forces
        if elem.Date and elem.Time:
            meaDate=datetime.datetime.strptime(f"{elem.Date} elem.Time", '%Y%m%d %H:%M:%S').date()
            self.update('event', 'date', meaDate, 'idEvent', id_mea)
        if elem.pixel_per_mm:
            self.update('measurement', 'resolutionSpace', float(elem.pixel_per_mm), 'idEvent', int(id_mea))


        #
        return id_mea





    def upload_measurement_from_csv(self, fname: str, bForce: bool=True) -> int:
        # the FOC_OUTFILE contains the path to xml file, if it is passed auto-convert to csv
        if re.search(r'.xml$', fname):
            fname = re.sub(r'\.xml$', '.csv', fname)

        expName =filename_to_experimentname(fname)
        meaName =filename_to_measurementname(fname)
        devName =filename_to_devicename(fname)
        #
        # Datum in ein datetime-Objekt konvertieren
        meaDate = datetime.datetime.strptime(meaName[0:8], '%Y%m%d').date()
        #print(f"upload measurement {expName}, {meaName} from {devName}")
        #we first need to get all well Ids associated with the experiment
        #
        id_exp  =self.get_id_experiment(expName)
        if id_exp==0:
            id_exp = self.add_ehm_experiment(expName)
        # get LabwareId
        id_mea =self.get_id_measurement(expName, meaName)
        #
        if id_mea ==0:
            id_mea = self.add_measurement(expName, meaName)
        #
        print(f"uploading traces: idMea {id_mea} idExp {id_exp}")
        traces = read_traces_from_csv(fname, expName, meaName)
        time=traces[0].time
        time_resolution_ms = round( (time[-1]-time[0])*1000/(len(time)-1),1)
        # upload forces
        self.update('event', 'date', meaDate,  'idEvent', id_mea)
        self.update('measurement', 'resolutionTime',  float(time_resolution_ms), 'idEvent', int(id_mea))
        self.update_time(id_mea, time)
        self.update('measurement','filename', fname, 'idEvent', id_mea)
        self.commit();
        #
        return id_mea

    
    def upload_traces_from_csv(self, fname: str, b_force: bool=True) -> int:
        # the FOC_OUTFILE contains the path to xml file, if it is passed auto-convert to csv
        if re.search(r'.xml$', fname):
            fname = re.sub(r'\.xml$', '.csv', fname)
        #
        expName =filename_to_experimentname(fname)
        meaName =filename_to_measurementname(fname)
        devName =filename_to_devicename(fname)
        #
        #print(f"upload measurement {expName}, {meaName} from {devName} force >{bForce}<")
        #we first need to get all well Ids associated with the experiment        
        #
        id_exp  =self.get_id_experiment(expName)
        #print(f"idExp of {expName} is {id_exp}")
        if id_exp==0:
            id_exp = self.add_ehm_experiment(expName)
        # get LabwareId
        id_mea =self.get_id_measurement(expName, meaName)
        #print(f"idMea of {meaName} is {id_mea}")
        traces = self.get_trace_ids(expName, meaName, 'all')

        #
        if id_mea==0:
            id_mea = self.add_measurement(expName, meaName)
            print(f"idMea of {meaName} is {id_mea}")
        elif b_force==False and len(traces)==48:
            print(f"Skip measurement {meaName}, already known. Force for overwrite")
        else:        #        
            #
            id_dev  =self.get_id_device(devName.lower())
            #print(f"idDevice of {devName} is {id_dev}")
            if id_dev>1:
                self.update_event(id_mea, 'idDevice', id_dev)
            #
            id_plate =self.get_id_plate(expName)
            #print(f"idPlate of {expName} is {id_plate}")
            if self.plate_has_wells(id_plate)==0:
                self.plate_add_wells(id_plate)
            #
            # wells = self.get_id_wells(id_plate)
            traces = read_traces_from_csv(fname, expName, meaName)
            time=traces[0].time
            time_resolution_ms = round( (time[-1]-time[0])*1000/(len(time)-1),1)
            print(f"timeResolution of {fname} {meaName} is {time_resolution_ms}")
            # upload forces
            self.update_measurement(id_mea, 'resolutionTime',  time_resolution_ms)
            self.update_time(id_mea, time)

            for t in traces:
               id_force=self.get_id_trace(id_mea, t.well)

               if id_force==0:
                   id_force = self.add_forces(id_mea, t.well)

               #print(f"idForce is >{id_force}<, update")
               try:
                   self.update_raw_distance(id_force, t.raw_distance)
               except:
                   print(f"failed to update raw_distance of {t.well} ifForce {id_force}")
                   for f in t.raw_distance:
                       print(f)

        #
        return id_mea

    def remove_peaks_from_trace(self, t: Trace):
        sql_string = f"DELETE from peak where idEvent = {t.id}"
        #print(sql_string)
        self.__execute_sql(sql_string)

    def add_peaks_to_trace(self, t: Trace):
        print(f"upload {len(t.peaks)} peaks for trace {t.id}")
        if len(t.peaks)>0:
            for p in t.peaks:
                self.__insert_row('peak',
                ['idEvent',        'frame','time', 'height','base', 'rr'],
                [int(p.trace_id), int(p.frame), float(p.time), float(p.height), p.base, float(p.rr/1000)]  )
            self.calcForceStats(t)

    def add_stats_to_trace(self, t: Trace):
        self.__insert_update_row('analysis', ['idEvent', 'name', 'value'], [int(t.id), 'base', t.base()], ['value'])
        self.__insert_update_row('analysis',['idEvent', 'name', 'value'],[int(t.id), 'avg', t.avg()], ['value'])
        self.__insert_update_row('analysis',['idEvent', 'name', 'value'],[int(t.id), 'std', t.std()], ['value'])
        self.__insert_update_row('analysis',['idEvent', 'name', 'value'],[int(t.id), 'min', t.min()], ['value'])
        self.__insert_update_row('analysis',['idEvent', 'name', 'value'],[int(t.id), 'max', t.max()], ['value'])


    def calcForceStats(self, t: Trace):
        return self.__execute_proc('calcForceStats', (t.id,), (0,))[0]

    def close(self) ->int :
        self.__db.close()
        return 1
    

    def __del__(self):
        try:
            self.__db.close()
        except AttributeError:
            pass
