import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

start = code.find("def draw_deck(self):")
end = code.find("def _deck_jog(self):", start)

old_body = code[start:end]

new_body = """def draw_deck(self):
        self.scene.clear()
        
        bed_width = 400
        bed_height = 300
        scale = 2.0
        
        self.scene.setSceneRect(0, 0, bed_width * scale, bed_height * scale)
        
        from PyQt6.QtGui import QPen, QBrush, QColor
        from PyQt6.QtCore import Qt, QRectF
        
        # Grid lines
        for x in range(0, int(bed_width) + 10, 10):
            vx = (bed_width - x) * scale
            color = "#cccccc" if x % 50 == 0 else "#ebebeb"
            self.scene.addLine(vx, 0, vx, bed_height * scale, QPen(QColor(color)))
            if x % 50 == 0:
                t = self.scene.addText(f"{x}mm")
                t.setPos(vx - 20, 10)
                t.setDefaultTextColor(QColor("#888888"))
                
        for y in range(0, int(bed_height) + 10, 10):
            vy = y * scale
            color = "#cccccc" if y % 50 == 0 else "#ebebeb"
            self.scene.addLine(0, vy, bed_width * scale, vy, QPen(QColor(color)))
            if y % 50 == 0:
                t = self.scene.addText(f"{y}mm")
                t.setPos(bed_width * scale - 45, vy - 10)
                t.setDefaultTextColor(QColor("#888888"))
                
        # Origin
        ox = bed_width * scale
        self.scene.addEllipse(ox - 15, 2, 13, 13, QPen(Qt.GlobalColor.black), QBrush(Qt.GlobalColor.red))
        t = self.scene.addText("(0,0)")
        t.setPos(ox - 45, 15)
        t.setDefaultTextColor(Qt.GlobalColor.red)
        
        # Draw slots
        for name in self.placed_slots:
            s = self.lims.deck_slots[name]
            visual_x_right = (bed_width - s.x_abs) * scale
            visual_x_left = (bed_width - (s.x_abs + s.width_mm)) * scale
            y0 = s.y_abs * scale
            y1 = (s.y_abs + s.height_mm) * scale
            
            fill = "#e9ecef"
            if name in self.lims.deck_labware:
                fill = "#f8f9fa" 
            
            rect = QRectF(visual_x_left, y0, visual_x_right - visual_x_left, y1 - y0)
            self.scene.addRect(rect, QPen(QColor("#6c757d"), 2), QBrush(QColor(fill)))
            
            t = self.scene.addText(name)
            t.setPos(visual_x_left + 5, y0 + 5)
            
            if name in self.lims.deck_labware:
                lab = self.lims.deck_labware[name]
                for w_name, w_info in lab.wells.items():
                    wx = (bed_width - (s.x_abs + w_info['x'])) * scale
                    wy = (s.y_abs + w_info['y']) * scale
                    self.scene.addEllipse(wx - 2, wy - 2, 4, 4, QPen(Qt.GlobalColor.gray), QBrush(Qt.GlobalColor.white))
                    
        # Draw pipettor (blue dot)
        jx, jy = 0.0, 0.0
        try:
            jx = float(self.deck_x.text())
            jy = float(self.deck_y.text())
        except ValueError:
            pass
            
        vx = (bed_width - jx) * scale
        vy = jy * scale
        self.scene.addEllipse(vx - 7, vy - 7, 14, 14, QPen(Qt.GlobalColor.black), QBrush(Qt.GlobalColor.blue))
        
    """

if start != -1:
    code = code.replace(old_body, new_body)
    with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
        f.write(code)
    print("PATCH 2 SUCCESSFUL")
else:
    print("FAILED TO MATCH PATCH 2")
