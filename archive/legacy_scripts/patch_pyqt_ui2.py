import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# 1. Rewrite Dilution Calculator Output
new_calc = """    def calc_dilution(self):
        try:
            stock_mM = float(self.ent_stock.text())
            stock_um = stock_mM * 1000
            target_um = float(self.ent_target.text())
            well_vol = float(self.ent_vol_dil.text())
            
            dilution_factor = stock_um / target_um
            transfer_vol = well_vol / (dilution_factor - 1)
            dmso_pct = (transfer_vol / (well_vol + transfer_vol)) * 100
            
            res = "=== DILUTION INSTRUCTIONS ===\\n\\n"
            
            if transfer_vol < 50:
                res += "⚠️ TRANSFER VOLUME TOO SMALL! (Needs Intermediate Stock)\\n\\n"
                res += "STEP 1: Make a 10x Dilution (Working Stock)\\n"
                res += "        Mix 10 uL of your Drug Stock with 90 uL of pure Media.\\n"
                res += "        (This creates a new Working Stock at 1/10th concentration).\\n\\n"
                
                new_stock_um = stock_um / 10
                new_df = new_stock_um / target_um
                new_transfer = well_vol / (new_df - 1)
                new_dmso = (new_transfer / (well_vol + new_transfer)) * 100
                
                res += "STEP 2: Pipette into EHM Well\\n"
                res += f"        Transfer {new_transfer:.1f} uL of the Working Stock into the {well_vol} uL EHM well.\\n\\n"
                res += f"        -> Final DMSO % in well: {new_dmso/10:.3f}% (Safe!)\\n"
            else:
                res += "✅ DIRECT PIPETTING (No intermediate stock needed)\\n\\n"
                res += "STEP 1: Pipette into EHM Well\\n"
                res += f"        Transfer {transfer_vol:.1f} uL of the Drug Stock directly into the {well_vol} uL EHM well.\\n\\n"
                res += f"        -> Final DMSO % in well: {dmso_pct:.3f}%\\n"
                if dmso_pct > 1.0:
                    res += "\\n🚨 WARNING: DMSO limit exceeded (>1%)! Tissue toxicity risk.\\n"
                
            self.res_text.setPlainText(res)
        except Exception as e:"""

code = re.sub(r'    def calc_dilution\(self\):.*?except Exception as e:', new_calc, code, flags=re.DOTALL)

# 2. Add Homing/Jogging to Deck Tab
# We will just insert standard X/Y/Z lineedits or a "Home All" button in the Deck Tab.
new_deck = """        btn_assign = QPushButton("Assign Labware")
        btn_assign.clicked.connect(self.assign_lw)
        l_layout.addWidget(btn_assign)
        
        l_layout.addSpacing(20)
        l_layout.addWidget(QLabel("--- QUICK JOG ---"))
        btn_home = QPushButton("Home XYZ")
        btn_home.clicked.connect(lambda: self.lims.hw.home_all())
        l_layout.addWidget(btn_home)
        
        self.deck_x = QLineEdit("0")
        self.deck_y = QLineEdit("0")
        self.deck_z = QLineEdit("0")
        btn_go = QPushButton("Go To Coordinates")
        btn_go.clicked.connect(self._deck_jog)
        l_layout.addWidget(QLabel("X:"))
        l_layout.addWidget(self.deck_x)
        l_layout.addWidget(QLabel("Y:"))
        l_layout.addWidget(self.deck_y)
        l_layout.addWidget(QLabel("Z:"))
        l_layout.addWidget(self.deck_z)
        l_layout.addWidget(btn_go)
"""

code = code.replace(
    '        btn_assign = QPushButton("Assign Labware")\n        btn_assign.clicked.connect(self.assign_lw)\n        l_layout.addWidget(btn_assign)',
    new_deck
)

add_jog_method = """    def _deck_jog(self):
        try:
            x = float(self.deck_x.text())
            y = float(self.deck_y.text())
            z = float(self.deck_z.text())
            self.lims.hw.move_to(x, y, z)
            # update PV needle
            mat = np.eye(4)
            mat[0,3] = x
            mat[1,3] = y
            mat[2,3] = z
            if hasattr(self, 'pv_pipette_actor') and self.pv_pipette_actor:
                self.pv_pipette_actor.user_matrix = mat
        except: pass
"""
code = code.replace("    def assign_lw(self):", add_jog_method + "\n    def assign_lw(self):")


with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Patch 2 Applied")
