import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from gapi import (
    SetTrajectory,
    CreateModeledMarker,
    GetEvents,
    getTimeLineMeasure,
)
import tkinter as tk
from tkinter import ttk, messagebox
import json


class SimModlOutput:
    def __init__(self):
        """
        Model Format
        Markers={
                MarkerName:
                {
                    "X": [],
                    "Y": [],
                    "Z": [],
                    "Exists": []
                }
                }
        model={


            Groupname1={
                ModelOutputName1={
                    Name=["ComponentName1", "ComponentName2", ...]
                    QuantityTypes=["QuantityType1", "QuantityType2", ...]
                    ComponentName1=Any
                    ComponentName2=Any
                    ...
                }
                ModelOutputName2={
                    Name=["ComponentName1", "ComponentName2", ...]
                    QuantityTypes=["QuantityType1", "QuantityType2", ...]
                    ComponentName1=Any
                    ComponentName2=Any
                    ...
                }
            }

        }
        """
        self.model = {}
        self.modelOutputs = set()
        self.Markers = {}
        self.leftPlate = "0"
        self.rightPlate = "0"

    def CreateModelOutput(
        self, modelOutputName, groupName, componentNames, QuantityTypes
    ):
        if groupName not in self.model:
            self.model[groupName] = {}
        if modelOutputName not in self.model[groupName]:
            self.modelOutputs.add(modelOutputName)
            self.model[groupName][modelOutputName] = {}
            self.model[groupName][modelOutputName]["Name"] = componentNames
            self.model[groupName][modelOutputName]["QuantityTypes"] = QuantityTypes
            for componentName in componentNames:
                self.model[groupName][modelOutputName][componentName] = None

    def getContents(self):
        return list(self.modelOutputs)

    def CreateModeledMarker(self, name):
        if name not in self.Markers:
            self.Markers[name] = {}
            CreateModeledMarker(name)
        else:
            print(f"Marker '{name}' already exists.")

    def SetModelOutput(self, modelOutputName, components, e,start,end,offset=0):
        if modelOutputName in self.Markers:
            self.Markers[modelOutputName]["X"] = components[0]
            self.Markers[modelOutputName]["Y"] = components[1]
            self.Markers[modelOutputName]["Z"] = components[2]
            self.Markers[modelOutputName]["Exists"] = e
            SetTrajectory(
                modelOutputName, components[0], components[1], components[2], e,start,end,offset
            )
            return
        for key, val in self.model.items():
            if modelOutputName in val:
                for componentName, value in zip(
                    val[modelOutputName]["Name"], components
                ):
                    val[modelOutputName][componentName] = value
                return

    def GetModelOutput(self, ModelName):
        arr = []
        for i in self.model.keys():
            if ModelName in self.model[i]:
                for componentName in self.model[i][ModelName]["Name"]:
                    arr.append(self.model[i][ModelName][componentName])

                return arr, [True] * len(arr)

    def printItem(self, name):
        if name in self.Markers:
            print(f"Marker: {name}")
            return
        for key, val in self.model.items():
            if name in val:
                print(f"Group: {key}, Model Output: {name}")
                for componentName, value in val[name].items():
                    print(f"  {componentName}: {value}")
                return
        print(f"Item '{name}' not found in model.")

    def saveAsJson(self, filename):
        with open(Path(__file__).parent / filename, "w") as f:
            json.dump(self.model, f, indent=4)


class ForcePlateGUI:
    def __init__(self, payload):
        self.payload = payload
        self.root = tk.Tk()
        self.root.title("Force Plate Selector")
        self.root.state('zoomed')

        # Configure styles for a cleaner look
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass # Fallback to default if clam is unavailable
            
        # Define custom styles
        style.configure("TFrame", background="#f5f5f5")
        style.configure("TLabel", background="#f5f5f5", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        
        # Card styles for force plate widgets
        style.configure("Card.TLabelframe", background="#ffffff")
        style.configure("Card.TLabelframe.Label", background="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Card.TCheckbutton", background="#ffffff", font=("Segoe UI", 10))

        self.root.configure(bg="#f5f5f5")

        # Variables to track selected left and right force plates
        self.left_var = tk.StringVar(value="0")
        self.right_var = tk.StringVar(value="0")

        self.create_widgets()

    def calculate_max_min(self, data_list):
        """Calculate max and min values from a list of data"""
        return np.nanmax(data_list), np.nanmin(data_list)

    def create_widgets(self):
        # Main container with padding
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header Section
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(header_frame, text="Force Plate Selection", style="Title.TLabel").pack(anchor="w")
        
        instructions = (
            "1. Open Data Info Window in QTM (Right Click > Display Force Data).\n"
            "2. Compare Max/Min values of Force (X,Y) with the plots below.\n"
            "3. Select the corresponding checkbox (Left/Right) if values match.\n"
            "Note: Only one Left and one Right plate can be selected."
        )
        ttk.Label(header_frame, text=instructions, justify="left").pack(anchor="w", pady=(5,0))

        # Scrollable Area Setup
        canvas_frame = ttk.Frame(main_container)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Create window in canvas and bind width to canvas width for responsiveness
        frame_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=canvas.winfo_reqwidth())
        # Make the inner frame expand when canvas expands
        def _configure_canvas(event):
            canvas.itemconfig(frame_id, width=event.width)
        canvas.bind("<Configure>", _configure_canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel for better UX
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Create widgets for each force plate ID
        for plate_id in self.payload:
            self.create_plate_widget(self.scrollable_frame, plate_id)

        # Ensure the scrollable frame columns expand to fill canvas
        self.scrollable_frame.columnconfigure(0, weight=1)

        # Footer / Action Area
        footer_frame = ttk.Frame(main_container)
        footer_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(
            footer_frame, text="Confirm Selection", command=self.show_results, width=25
        ).pack(side=tk.RIGHT)

        self.result_label = ttk.Label(footer_frame, text="", font=("Segoe UI", 10, "italic"))
        self.result_label.pack(side=tk.LEFT)

    def update_offset(self, plate_id, value_str):
        """Update offset data in payload"""
        try:
            values = value_str.split(",")
            if len(values) == 3:
                offset = [float(val) for val in values]
                if "Offset" not in self.payload[plate_id]:
                    self.payload[plate_id]["Offset"] = {}
                self.payload[plate_id]["Offset"] = {"X": offset[0], "Y": offset[1], "Z": offset[2]}
                print(f"Updated offset for {plate_id}: {offset}")
            else:
                messagebox.showerror("Invalid Format", "Offset must be in format: X,Y,Z")
        except ValueError:
            messagebox.showerror("Invalid Values", "Please enter valid numeric values")

    def update_origin(self, plate_id, value_str):
        """Update origin data in payload"""
        try:
            values = value_str.split(",")
            if len(values) == 3:
                origin = [float(val) for val in values]
                self.payload[plate_id]["Origin"] = origin
                print(f"Updated origin for {plate_id}: {origin}")
            else:
                messagebox.showerror("Invalid Format", "Origin must be in format: X,Y,Z")
        except ValueError:
            messagebox.showerror("Invalid Values", "Please enter valid numeric values")

    def update_world_center(self, plate_id, value_str):
        """Update world center data in payload"""
        try:
            values = value_str.split(",")
            if len(values) == 3:
                world_center = [float(val) for val in values]
                self.payload[plate_id]["WorldCenter"] = world_center
                print(f"Updated world center for {plate_id}: {world_center}")
            else:
                messagebox.showerror("Invalid Format", "World Center must be in format: X,Y,Z")
        except ValueError:
            messagebox.showerror("Invalid Values", "Please enter valid numeric values")

    def create_CenterMod(self, parent, plate_id):
        # Configuration Section inside the card
        config_frame = ttk.Frame(parent, style="Card.TFrame")
        config_frame.pack(fill=tk.X, pady=(10, 5))
        
        # Grid Layout for Inputs
        ttk.Label(config_frame, text="Parameter", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(config_frame, text="X", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=1, padx=2)
        ttk.Label(config_frame, text="Y", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=3, padx=2)
        ttk.Label(config_frame, text="Z", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=5, padx=2)

        def create_input_row(row, label, data_key, update_cb):
            ttk.Label(config_frame, text=label, background="#ffffff").grid(row=row, column=0, sticky="w", padx=5, pady=2)
            
            data = self.payload[plate_id][data_key]
            if isinstance(data, dict):
                vals = [data['X'], data['Y'], data['Z']]
            else:
                vals = data

            entries = []
            for i, val in enumerate(vals):
                e = ttk.Entry(config_frame, width=12, justify="center")
                e.insert(0, f"{val:.6f}")
                e.grid(row=row, column=1 + i*2, padx=2)
                entries.append(e)
                
                if i < 2:
                    ttk.Label(config_frame, text=",", background="#ffffff").grid(row=row, column=2 + i*2)

            def on_change(event=None):
                combined = f"{entries[0].get()},{entries[1].get()},{entries[2].get()}"
                update_cb(plate_id, combined)

            for e in entries:
                e.bind("<FocusOut>", on_change)
                e.bind("<Return>", on_change)

        # Ensure Offset exists
        if "Offset" not in self.payload[plate_id]:
            self.payload[plate_id]["Offset"] = {"X": 0.0, "Y": 0.0, "Z": 0.0}

        create_input_row(1, "Origin", "Origin", self.update_origin)
        create_input_row(2, "World Center", "WorldCenter", self.update_world_center)
        create_input_row(3, "Offset", "Offset", self.update_offset)

    def create_plate_widget(self, parent, plate_id):
        """Create widget for individual force plate"""
        # Card Container
        card = ttk.LabelFrame(parent, text=f" Force Plate ID: {plate_id} ", style="Card.TLabelframe", padding=15)
        # Using pack with fill=BOTH and expand=True so the cards take full width
        card.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)

        # Selection Area
        select_frame = ttk.Frame(card, style="Card.TFrame")
        select_frame.pack(fill=tk.X, pady=(0, 10))

        left_cb = ttk.Checkbutton(
            select_frame,
            text="Left Force Plate",
            style="Card.TCheckbutton",
            command=lambda: self.on_left_selected(plate_id),
        )
        left_cb.pack(side=tk.LEFT, padx=(0, 20))

        right_cb = ttk.Checkbutton(
            select_frame,
            text="Right Force Plate",
            style="Card.TCheckbutton",
            command=lambda: self.on_right_selected(plate_id),
        )
        right_cb.pack(side=tk.LEFT)

        setattr(self, f"left_cb_{plate_id}", left_cb)
        setattr(self, f"right_cb_{plate_id}", right_cb)

        # Configuration Inputs
        self.create_CenterMod(card, plate_id)

        # Data Statistics Area
        ttk.Separator(card, orient='horizontal').pack(fill='x', pady=10)
        
        stats_frame = ttk.Frame(card, style="Card.TFrame")
        stats_frame.pack(fill=tk.X)

        # Headers
        headers = ["Metric", "X (Max/Min)", "Y (Max/Min)", "Z (Max/Min)"]
        for i, h in enumerate(headers):
            align = "w" if i == 0 else "e"
            ttk.Label(stats_frame, text=h, font=("Segoe UI", 8, "bold"), background="#ffffff").grid(row=0, column=i, sticky=align, padx=5, pady=5)

        # Data Rows
        row = 1
        for data_type in ["Force", "Moment", "Center_of_Pressure"]:
            ttk.Label(stats_frame, text=data_type.replace("_", " "), background="#ffffff").grid(row=row, column=0, sticky="w", padx=5, pady=2)

            for col, axis in enumerate(["X", "Y", "Z"]):
                data = self.payload[plate_id][data_type][axis]
                max_val, min_val = self.calculate_max_min(data)
                
                # Adjust scale for Moment
                scale = 1000.0 if data_type == 'Moment' else 1.0
                val_str = f"{max_val/scale:.2f} / {min_val/scale:.2f}"
                
                
                ttk.Label(stats_frame, text=val_str, font=("Consolas", 9), background="#ffffff").grid(row=row, column=col+1, padx=5, sticky="e")
            row += 1
            
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        stats_frame.columnconfigure(3, weight=1)

    def on_left_selected(self, plate_id):
        """Handle left force plate selection"""
        left_cb = getattr(self, f"left_cb_{plate_id}")
        right_cb = getattr(self, f"right_cb_{plate_id}")
        if right_cb.instate(["selected"]):
            # If right is selected, do not allow left selection
            right_cb.state(["!selected"])
            self.right_var.set("0")

        if left_cb.instate(["selected"]):
            # Uncheck all other left checkboxes
            for other_id in self.payload:
                if other_id != plate_id:
                    other_cb = getattr(self, f"left_cb_{other_id}")
                    other_cb.state(["!selected"])

            self.left_var.set(str(plate_id))
        else:
            self.left_var.set("0")

    def on_right_selected(self, plate_id):
        """Handle right force plate selection"""
        right_cb = getattr(self, f"right_cb_{plate_id}")
        left_cb = getattr(self, f"left_cb_{plate_id}")
        if left_cb.instate(["selected"]):
            # If left is selected, do not allow right selection
            left_cb.state(["!selected"])
            self.left_var.set("0")

        if right_cb.instate(["selected"]):
            # Uncheck all other right checkboxes
            for other_id in self.payload:
                if other_id != plate_id:
                    other_cb = getattr(self, f"right_cb_{other_id}")
                    other_cb.state(["!selected"])

            self.right_var.set(str(plate_id))
        else:
            self.right_var.set("0")

    def show_results(self):
        """Display selected force plate IDs"""
        left_id = self.left_var.get()
        right_id = self.right_var.get()

        # Store results
        self.result_left = left_id
        self.result_right = right_id

        # Create popup message
        message = f"Selected Force Plates:\n\nLeft Force Plate: {left_id}\nRight Force Plate: {right_id}"

        # Show message box
        messagebox.showinfo("Force Plate Selection", message)

        # Close the application
        self.root.quit()
        self.root.destroy()

        return left_id, right_id

    def get_selected_plates(self):
        """Return the selected force plate IDs"""
        return self.left_var.get(), self.right_var.get()

    def run(self):
        """Start the GUI"""
        self.root.mainloop()
        return self.get_selected_plates()

def normalize_zeroes(payload,key):
    payload[key]["X"][np.isclose(payload[key]["X"], 0.0)] = 0.0
    payload[key]["Y"][np.isclose(payload[key]["Y"], 0.0)] = 0.0
    payload[key]["Z"][np.isclose(payload[key]["Z"], 0.0)] = 0.0

def ProcessForceplateData(reader):
    n = len(reader["data"]["platform"])
    payload = {}
    for id in range(n):
        center = np.mean(reader["data"]["platform"][id]["corners"], axis=1)
        payload[f"FP{id}"] = {
            "Force": {
                "X": reader["data"]["platform"][id]["force"][0],
                "Y": reader["data"]["platform"][id]["force"][1],
                "Z": reader["data"]["platform"][id]["force"][2],
            },
            "Moment": {
                "X": reader["data"]["platform"][id]["moment"][0],
                "Y": reader["data"]["platform"][id]["moment"][1],
                "Z": reader["data"]["platform"][id]["moment"][2],
            },
            "Center_of_Pressure": {
                "X": np.array(reader["data"]["platform"][id]["center_of_pressure"][1]),
                "Y": -np.array(reader["data"]["platform"][id]["center_of_pressure"][0]),
                "Z": -np.array(reader["data"]["platform"][id]["center_of_pressure"][2]),
            },
            "Exists": [],
            "Frequency": reader["parameters"]["ANALOG"]["RATE"]["value"][0],
            "Origin": reader["data"]["platform"][id]["origin"],
            "WorldCenter": center,

            "Offset": {"X": np.round(center[0]), "Y": np.round(center[1]), "Z": np.round(center[2])/2}  # Initialize offset with default zeros
        }
        normalize_zeroes(payload[f"FP{id}"], "Force")
        normalize_zeroes(payload[f"FP{id}"], "Moment")
        normalize_zeroes(payload[f"FP{id}"], "Center_of_Pressure")
       
        #pd.DataFrame(payload[f"FP{id}"]["Center_of_Pressure"]).to_csv(f"COP_Shriner_FP{id}.csv", index=False)
            
        #print(np.array(tmp[str(qid)]["Center_of_Pressure"]["X"][:1819][::-1][:500]))
        # for tmp_key in tmp:
        #     # Compare force and moment values to find matching force plate
        #     # print(math.sqrt(payload[tmp_key]["Moment"]["X"][526]**2+
        #     #                 payload[tmp_key]["Moment"]["Y"][526]**2+
        #     #                 payload[tmp_key]["Moment"]["Z"][526]**2))

        #     #print COP of both FP and tmp at frame 526

        #     # print(f"FP{id} Center of Pressure at frame 526: {payload[f'FP{id}']['Center_of_Pressure']['X'][526]}, {payload[f'FP{id}']['Center_of_Pressure']['Y'][526]}, {payload[f'FP{id}']['Center_of_Pressure']['Z'][526]}")
        #     # print(f"tmp {tmp_key} Center of Pressure at frame 526: {tmp[tmp_key]['Center_of_Pressure']['X'][526]}, {tmp[tmp_key]['Center_of_Pressure']['Y'][526]}, {tmp[tmp_key]['Center_of_Pressure']['Z'][526]}")

        #     mn=min(len(payload[f"FP{id}"]["Force"]["X"]), len(tmp[tmp_key]["Force"]["X"]))
        #     force_match = (
        #         np.allclose(payload[f"FP{id}"]["Force"]["X"][:mn], tmp[tmp_key]["Force"]["X"][:mn], rtol=1e-5, atol=1e-8) and
        #         np.allclose(payload[f"FP{id}"]["Force"]["Y"][:mn], tmp[tmp_key]["Force"]["Y"][:mn], rtol=1e-5, atol=1e-8) and
        #         np.allclose(payload[f"FP{id}"]["Force"]["Z"][:mn], tmp[tmp_key]["Force"]["Z"][:mn], rtol=1e-5, atol=1e-8)
        #     )

        #     moment_match = (
        #         np.allclose(payload[f"FP{id}"]["Moment"]["X"][:mn]/1000, tmp[tmp_key]["Moment"]["X"][:mn], rtol=1e-5, atol=1e-8) and
        #         np.allclose(payload[f"FP{id}"]["Moment"]["Y"][:mn]/1000, tmp[tmp_key]["Moment"]["Y"][:mn], rtol=1e-5, atol=1e-8) and
        #         np.allclose(payload[f"FP{id}"]["Moment"]["Z"][:mn]/1000, tmp[tmp_key]["Moment"]["Z"][:mn], rtol=1e-5, atol=1e-8)
        #     )

        #     if force_match and moment_match:
        #         # Copy center of pressure, exists, and frequency from matching tmp data
        #         payload[f"FP{id}"]["Center_of_Pressure"] = {
        #             "X": np.array(tmp[tmp_key]["Center_of_Pressure"]["X"]),
        #             "Y": np.array(tmp[tmp_key]["Center_of_Pressure"]["Y"]),
        #             "Z": np.array(tmp[tmp_key]["Center_of_Pressure"]["Z"])
        #         }
        #         payload[f"FP{id}"]["Exists"] = tmp[tmp_key]["Exists"]
        #         payload[f"FP{id}"]["Frequency"] = tmp[tmp_key]["Frequency"]
        #         break

    print(payload.keys())
    return payload


# Example usage
def main():
    # Sample payload data
    payload = {
        "1": {
            "Force": {
                "X": [10.5, 15.2, 8.9, 12.1],
                "Y": [5.3, 7.8, 4.2, 6.9],
                "Z": [25.1, 30.4, 22.7, 28.3],
            },
            "Moment": {
                "X": [2.1, 3.5, 1.8, 2.9],
                "Y": [1.7, 2.3, 1.2, 2.0],
                "Z": [4.2, 5.1, 3.8, 4.7],
            },
            "Center_of_Pressure": {
                "X": [0.15, 0.22, 0.08, 0.18],
                "Y": [0.12, 0.19, 0.06, 0.14],
                "Z": [0.0, 0.0, 0.0, 0.0],
            },
            "Exists": [True, True, True, True],
            "Origin": [0.0, 0.0, 0.0],
            "WorldCenter": [0.0, 0.0, 0.0],
        },
        "2": {
            "Force": {
                "X": [8.3, 11.7, 6.9, 9.5],
                "Y": [4.1, 6.2, 3.5, 5.1],
                "Z": [20.8, 26.3, 18.9, 23.7],
            },
            "Moment": {
                "X": [1.9, 2.8, 1.4, 2.3],
                "Y": [1.5, 2.1, 1.0, 1.8],
                "Z": [3.7, 4.5, 3.2, 4.1],
            },
            "Center_of_Pressure": {
                "X": [0.13, 0.20, 0.07, 0.16],
                "Y": [0.10, 0.17, 0.05, 0.12],
                "Z": [0.0, 0.0, 0.0, 0.0],
            },
            "Exists": [True, True, True, True],
            "Origin": [0.0, 0.0, 0.0],
            "WorldCenter": [0.0, 0.0, 0.0],
        },
        "3": {
            "Force": {
                "X": [8.3, 11.7, 6.9, 9.5],
                "Y": [4.1, 6.2, 3.5, 5.1],
                "Z": [20.8, 26.3, 18.9, 23.7],
            },
            "Moment": {
                "X": [1.9, 2.8, 1.4, 2.3],
                "Y": [1.5, 2.1, 1.0, 1.8],
                "Z": [3.7, 4.5, 3.2, 4.1],
            },
            "Center_of_Pressure": {
                "X": [0.13, 0.20, 0.07, 0.16],
                "Y": [0.10, 0.17, 0.05, 0.12],
                "Z": [0.0, 0.0, 0.0, 0.0],
            },
            "Exists": [True, True, True, True],
            "Origin": [0.0, 0.0, 0.0],
            "WorldCenter": [0.0, 0.0, 0.0],
        },
    }

    # Create and run the GUI
    app = ForcePlateGUI(payload)
    left_id, right_id = app.run()

    print(f"Final selection - Left: {left_id}, Right: {right_id}")
    return left_id, right_id


def GetTrajectoryAtFrame(fields, model: SimModlOutput, markerName, Frame):
    if markerName in fields["Points"]:
        return (
            fields[markerName]["X"][Frame],
            fields[markerName]["Y"][Frame],
            fields[markerName]["Z"][Frame],
            fields[markerName]["Exists"][Frame],
        )
    if markerName in model.Markers:
        return (
            model.Markers[markerName]["X"][Frame],
            model.Markers[markerName]["Y"][Frame],
            model.Markers[markerName]["Z"][Frame],
            model.Markers[markerName]["Exists"][Frame],
        )


if __name__ == "__main__":
    # print(GetEvents("RSTRIKE"))
    print(getTimeLineMeasure())
    #main()
