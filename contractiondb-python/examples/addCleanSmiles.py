#from contractiondb import ContractionDB, get_credentials
#from types import NoneType
import json
#import numpy as np
import sys
from mysql.connector import fabric
#import seaborn as sns

import pandas as pd
#import numpy as np
#import matplotlib.pyplot as plt 
from rdkit import Chem
from rdkit import DataStructs
from rdkit.ML.Cluster import Butina
from rdkit.Chem import Draw
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Draw import SimilarityMaps

#np.set_printoptions(threshold=sys.maxsize)


sys.path.append("E:\Labhub\Repos\meyerti\contractiondb-python")


from src.contractiondb import ContractionDB
from src.contractiondb.csv_utils import read_measurements_from_csv

config_filename = "c:\Labhub\Import\contractiondb2_gwdg.json"
loginData=json.load(open(config_filename))
db = ContractionDB(**loginData)

cmpds = db.get_compounds()

for c1 in cmpds:
    if c1.smiles is None:
        continue
    n1  =c1.name.decode(encoding="utf-8")
    smiles=c1.smiles.decode(encoding="utf-8")
    s1= smiles.split(".")[0]
    print(f"id {c1.id} name {n1} smiles {s1}")    
    if len(s1)<4:
        continue
    try:
        fp1 = Chem.RDKFingerprint(Chem.MolFromSmiles(s1))
    except:
        print(f"skip {n1} {s1}")
        continue

    for c2 in cmpds:
       if c1.id>c2.id:
           continue
       if c2.smiles is None:
           continue
       n2  =c2.name.decode(encoding="utf-8")
       smiles=c2.smiles.decode(encoding="utf-8")
       s2= smiles.split(".")[0]            
       
       if len(s2)<4:
           continue
       print(f"{n2} smiles {s2}")
       try:
           fp2 = Chem.RDKFingerprint(Chem.MolFromSmiles(s2))
       except:
           print(f"skip {n2}")
           continue
       sim=DataStructs.TanimotoSimilarity(fp1,fp2)
       print(f"id {c1.id} {c2.id} tanimoto {sim}")       
       sql_str=f"Insert into compound_similarity (idCompound, idReference, value) VALUE({c1.id}, {c2.id}, {sim}) ON DUPLICATE KEY UPDATE value={sim}"
       print(sql_str)
       db.execute_sql(sql_str)