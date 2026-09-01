
#from contractiondb import ContractionDB, get_credentials
import json
import numpy as np
import sys
import csv
import re


sys.path.append("E:\Labhub\Repos\meyerti\contractiondb-python")


from src.contractiondb import ContractionDB
from src.contractiondb.csv_utils import read_measurements_from_csv
from src.contractiondb import CAS_REGEX
from src.contractiondb.classes import Compound

config_filename = "c:\Labhub\Import\contractiondb2_gwdg.json"
loginData=json.load(open(config_filename))
db = ContractionDB(**loginData)

{
  "host": "maxscale.mysql.gwdg.de",
  "port": 3307,
  "database": "contractiondb2",
  "user": "labhub",
  "password": "Q50i59Izs"
}



file_path = r'E:\Documents\People\chanut_emma\autoOrgan_stage1_all_drugs.CSV'

with open(file_path, 'r', newline='') as file:
    reader = csv.reader(file, delimiter=';',lineterminator='\r')
    for i,row in enumerate(reader):
     #Ignore controls
     if row[3] == 'Control' or row[7] == 'Synonyms' or len(row[7]) < 3:
         continue

     cmpd=Compound;
     match = re.search(r'\((.*?)\)$', row[7])
     if match:
            print(f"Salt is {match.group(1)}")
            cmpd.salt =   match.group(1)
            cmpd.name = re.sub(r'\(.*?\)', '', row[7])
     else:
            cmpd.name=row[7]
        
     id=db.add_compound(cmpd)

     print(f"{i} {cmpd.name} CAS is {row[9]} with lenght {len(row[9])}")

     if re.fullmatch(CAS_REGEX, row[9]):
         db.update_compound_cas(   id, row[9])

     db.update_compound_mw(    id, row[10])     
     db.update_compound_smiles(id, row[15])



        
        
            



#we first need to get all well Ids associated with the experiment


db.close()

