import tkinter as tk
from tkinter import ttk
from PIL import ImageTk, Image
import json
import sys

from src.contractiondb import contractionDb
from src.contractiondb.regex import parse_args
from matplotlib import pyplot as plt

args=parse_args()

print(f"config is {args.config}")

loginData=json.load(open(args.config))
db = ContractionDB(**loginData)



window = tk.Tk()
window.geometry=('600x400')
window.title('contractionDb')

table=ttk.Treeview(window)
table.pack()

window.mainloop()


