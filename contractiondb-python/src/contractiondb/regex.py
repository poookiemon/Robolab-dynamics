import argparse
import sys
import re
import glob


DATE_REGEX = "[0-9]{4}-[0-9]{2}-[0-9]{2}"

PLATE_REGEX = "[0-9]{8}[a-z](_[a-zA-Z0-9 _]*)?"

MEA_REGEX = "[0-9]{8}[a-z](_[a-zA-Z0-9 _]*)?"

CSV_REGEX = "[0-9]{8}[a-z](_[a-zA-Z0-9 _-]*)?.csv"

XML_REGEX = "[0-9]{8}[a-z](_[a-zA-Z0-9]*)?.xml"

EXP_REGEX = "[0-9]{8}[a-z](_[a-zA-Z0-9 _-]*)?"

DEVICE_REGEX = "HZPHW-([a-zA-Z0-9]*)?"

SUFFIX_REGEX = "_[a-zA-Z0-9 _]*"

WELL_REGEX = "[A-H][1-6]"

CAS_REGEX = "[0-9]{2,7}-[0-9]{2}-[0-9]{1}"



def parse_args()->argparse.Namespace :
    parser = argparse.ArgumentParser(description='Parse config file path',   epilog='Hope it helps')
    parser.add_argument('-c', '--config', help='Path to config file', default=r"c:\Labhub\Import\contractiondb.json")
    parser.add_argument('-p ', '--path',   help='Path to Root Dir',    default=r"c:\labhub\FOC48_DATA")
    parser.add_argument('-o', '--override', help='Force Upload of known Measurements', default=False)
    parser.add_argument('-e', '--expName', help='Experiment Name', default=None)
    parser.add_argument('-m', '--meaName', help='Measurement Name', default=None)
    parser.add_argument('-w', '--wellName', help='Well Name', default=None)
    parser.add_argument('-f', '--files',   nargs="+", help="File List")

    # Argumente aus der Commandozeile lesen

    args=parser.parse_args(sys.argv[1:])

    if args.files and len(args.files)==1:
        print(f"analyse file {args.files[0]}")
        if re.search(r'\*', args.files[0]):
            print(f"expand filenames: {args.files[0]}")
            args.files = glob.glob(args.files[0])
            print(f"wildcard expanded to {len(args.files)} files")

    return args

