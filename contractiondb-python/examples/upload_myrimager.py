

def main():
    #from contractiondb import ContractionDB, get_credentials
    import json
    import os
    import sys
    import winreg
    import re

    from ..src.contractiondb import ContractionDB
    from ..src.contractiondb import parse_args


    args = parse_args()
    print(f"config is {args.config}")

    file_list=[]

    if args.files:
        file_list=args.files
    else:
        # Öffnen Sie den Registry-Ordner
        reg_key = "FOC_OUTFILE"
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        # Lesen Sie die Umgebungsvariable
        fname, type = winreg.QueryValueEx(hkey, reg_key)
        #   Drucken Sie den Wert der Umgebungsvariable
        # the FOC_OUTFILE contains the path to xml file, if it is passed auto-convert to csv

        if os.path.isfile(fname):
            file_list.append(fname)
        else:
            print(f"Env {reg_key} does not contain a valid filename >{fname}<")


    try:
        loginData = json.load(open(args.config))
        db = ContractionDB(**loginData)
    except:
        raise Exception(f"Failed to connect to DB, check Config File >{args.config}<")

    for fname in file_list:

        if re.search(r".xml$", fname):
            fname = re.sub(r"\.xml$", ".csv", fname)
            print(f"fname became {fname}")

        if os.path.isfile(fname):
            print(f"loading  {fname}")
            try:
                id_mea=db.upload_traces_from_csv(fname)
            except:
                raise Exception(f"Second Argument does not contain a valid CSV File, {fname}")

            try:
                traces = db.get_id_traces(id_mea)
                #print(f"found {len(traces)} traces")
            except:
                raise Exception(f"coudl not load traces from DB")

            for t in traces:
                db.add_trace(t)
                t.filter_min_max()
                t.find_peaks()
                #print(f"found {len(t.peaks)} peaks in trace {t.id}")
                db.add_stats_to_trace(t)
                db.remove_peaks_from_trace(t)
                db.add_peaks_to_trace(t)
        else:
            print(f"no file >{fname}< found")

    db.commit()
    db.close()
    print("DONE")

if __name__ == "__main__":
    # Nur beim direkten Ausführen ausführen
    import sys
    main()
    exit()