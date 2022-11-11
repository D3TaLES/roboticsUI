import json
import os
import itertools
from pathlib import Path

key_ys = {
    "A": 0.090,
    "B": -0.01,
    "C": -0.105,
}
key_xs = {
    "01": 0,
    "02": 0.595,
    "03": 0.632,
    "04": 0.665,
}
key_zs = {
    "01": 0,
    "02": 0.074,
    "03": 0.120,
    "04": 0.166,
}

snapshot_home = os.path.join(Path(
    "C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "d3tales_fw" / "Robotics" / "workflows" / "snapshots")

with open("VialHome_master.json", 'r') as fn:
    master_data = json.load(fn)

for column, row in itertools.product(key_ys, key_xs):
    if not key_zs.get(row):
        continue
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["x"] = key_xs.get(row)
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["z"] = key_zs.get(row)
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["y"] = key_ys.get(column)

    # Generate VialHome files
    out_name = "VialHome_{}_{}.json".format(column, row)
    with open(os.path.join(snapshot_home, out_name), "w+") as fn:
        json.dump(master_data, fn, indent=2)

    # Generate VialHomeAbv files
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["z"] = key_zs.get(row) + 0.1
    out_name_abv = "VialHome_{}_{}_Abv.json".format(column, row)
    with open(os.path.join(snapshot_home, out_name_abv), "w+") as fn:
        json.dump(master_data, fn, indent=2)


