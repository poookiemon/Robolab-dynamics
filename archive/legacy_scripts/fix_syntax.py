import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# Find everything between "def calc_dilution(self):" and "except Exception as e:"
start_idx = code.find('    def calc_dilution(self):')
end_idx = code.find('        except Exception as e:', start_idx)

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
"""

final_code = code[:start_idx] + new_calc + code[end_idx:]

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(final_code)
print("Syntax fixed!")
