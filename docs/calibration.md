# Calibration & Tim's Z-Verification Workflow

## Tim's Slot-by-Slot Tip Check
1. The robot picks up a single verification tip from Slot 4.
2. The carriage moves to the user-selected slot and well at nominal Z.
3. The operator visually inspects the tip clearance above well brim or bottom.
4. Using the fine-jog controls (+/-0.1mm, +/-0.5mm, +/-2mm, +/-10mm), the operator aligns the exact height and clicks **[ Save to Active Profile ]**.
5. The calibrated value is saved directly to the active machine's `heights.json`.
