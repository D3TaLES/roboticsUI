import json
import os
import itertools
from pathlib import Path

shift_values = {
    "x": 0.303,
    "y": 0.200,
    "z": 0.099,
    "thetaX": 0,
    "thetaY": 0,
    "thetaZ": 0
}

old_snapshots = Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "snapshots" / "old"
new_snapshots = Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "snapshots" / "new"
os.makedirs(new_snapshots, exist_ok=True)

for snapshot in os.listdir(old_snapshots):
    with open(old_snapshots / str(snapshot), 'r') as fn:
        master_data = json.load(fn)

    for item, value in shift_values.items():
        master_data["poses"]["pose"][0]["reachPose"]["targetPose"][item] = value

    # Generate VialHome files
    with open(new_snapshots / str(snapshot), "w+") as fn:
        json.dump(master_data, fn, indent=2)

    print("Updated snapshot ", snapshot)

print("Successfully updated snapshots in folder 'old'. New snapshots are in folder 'new'.")



