import os
import sys
import re
import time
import subprocess
import json

sys.path.append("C:\Labhub\Repos\contractiondb-python")
from src.contractiondb import ContractionDB

PLATE_REGEX = "[0-9]{8}[a-z](_[a-zA-Z0-9 _]*)?"

#sys.path.append("C:\Labhub\Repos\contractiondb-python")
#from contractiondb.regex import PLATE_REGEX





firstFile = int(1)
path = "S:\MOLP\PHA_LabHub\Labhub\devices\HZPHW-FOC4809"
exe  =   'C:\\Labhub\\import\\analyzeMeasurement_20231130.exe '


cred = 'C:\\labhub\\import\\smartlab_db_gwdg.json'
#cred = 'C:\\labhub\\import\\contractiondb.json'

for arg in sys.argv:
    print(arg)
    if arg.isdigit():
        firstFile=int(arg)
    elif os.path.isdir(arg):
        path=arg

print('start with file number ' + str(firstFile) )
print('start in directory: ' + path )


fname = 'S:\\MOLP\\PHA_LabHub\\Labhub\\devices\\HZPHW-FOC4807\\2022\\20220407c\\20220430b_stim800.xml'

time.sleep(5)

db = ContractionDB(**json.load(open(cred)))

idExp=0

i=1
for root,d_names,f_names in os.walk(path):   
   print(root)
   if not "FOC48" in root:
       continue
   dirs=root.rsplit('\\')
   if len(dirs)<2:
          continue
   sExp = dirs[-1]
   if not re.fullmatch(PLATE_REGEX, sExp):
        continue
   if "x" in sExp:
       continue
   idExp=db.get_id_experiment(sExp) 
   for f in f_names:
      f_root, f_ext  = os.path.splitext(f)
      if len(f_root.rsplit('.')) != 1:
          continue
      if f_ext!='.xml':
         continue
      #
      fname=os.path.join(root, f)
      if (' ' in fname):
         print('whitespace in: ' + fname, ' skip')
         continue
      #
      i=i+1      
      if i<firstFile:
          continue
      csv=fname=os.path.join(root, f_root+'.csv')
      #S:\\MOLP\\PHA_LabHub\\Labhub\\devices\\HZPHW-FOC4802\\2020\\20201010e_tib\\20201023a.csv
      if not os.path.isfile(csv) or os.path.getsize(csv) < 100:
           print('Data File  ' + csv + ' too small,  skip')
           continue
      
      #
      idMea=db.get_id_measurement(idExp, f_root)
      if idMea>0:
           print('Measurement ' + f_root + ' already in DB with no ' + str(idMea), ' skip')
           continue
      
      print(str(i) + ' execute ' + exe + ' -batch -o -nofile -db '+ cred + ' ' + fname) 
      subprocess.run([exe, '-batch','-o','-nofile','-db', cred, fname])
        



