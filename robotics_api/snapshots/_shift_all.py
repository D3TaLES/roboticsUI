import json
import os
import itertools
from pathlib import Path

shift_values = {
    "x": -0.006,
    "y": -0.001,
    "z": 0,
    "thetaX": 0,
    "thetaY": 0,
    "thetaZ": 0
}

old_snapshots = Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "snapshots" / "snaps_20240828"
new_snapshots = Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "snapshots" / "snaps_20240917"
os.makedirs(new_snapshots, exist_ok=True)

for snapshot in os.listdir(old_snapshots):
    with open(old_snapshots / str(snapshot), 'r') as fn:
        master_data = json.load(fn)
        if master_data.get("poses"):
            for item, value in shift_values.items():
                master_data["poses"]["pose"][0]["reachPose"]["targetPose"][item] += value
            print("Updated snapshot ", snapshot)
        else:
            print(f"Snapshot '{snapshot}' not adjusted because it does not contain 'poses'.")

        # Generate VialHome files
        with open(new_snapshots / str(snapshot), "w+") as fn:
            json.dump(master_data, fn, indent=2)

print("Successfully updated snapshots in folder 'snaps_20240813_orig'. New snapshots are in folder 'old'.")
