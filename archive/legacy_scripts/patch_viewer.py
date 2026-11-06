with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

old_block = """                # Save to the timestamped folder
                image_name = file_name.replace(".stats.xml", "_heatmap.png")
                save_path = os.path.join(save_dir, image_name)
                plt.savefig(save_path, bbox_inches='tight', dpi=150)
                
                plt.show()
            except Exception as e:"""

new_block = """                # Save to the timestamped folder
                image_name = file_name.replace(".stats.xml", "_heatmap.png")
                save_path = os.path.join(save_dir, image_name)
                plt.savefig(save_path, bbox_inches='tight', dpi=150)
                
                # Close the plot silently instead of popping up a blocking window
                plt.close()
            except Exception as e:"""

# We also need to add the folder-opening logic at the very end
old_end = """        messagebox.showinfo("Success", f"Analysis complete! Saved all heatmaps to:\\n{save_dir}")"""

new_end = """        
        # Auto-open the folder on Mac (or Windows) so they can use native Image Viewer
        import subprocess, sys
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", save_dir])
            elif sys.platform == "win32":
                os.startfile(save_dir)
        except Exception:
            pass
            
        messagebox.showinfo("Success", f"Analysis complete! Saved all heatmaps to:\\n{save_dir}")"""


if old_block in code and old_end in code:
    code = code.replace(old_block, new_block)
    code = code.replace(old_end, new_end)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO FIND TARGET BLOCKS")

