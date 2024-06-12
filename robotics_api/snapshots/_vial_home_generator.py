import json
import os
import itertools
from pathlib import Path

key_ys = {
    "S": 0.303,
    "A": 0.200,
    "B": 0.099,
    "C": -0.001,
    "D": -0.997,
}
key_xs = {
    "01": 0.546,
    "02": 0.582,
    "03": 0.618,
    "04": 0.654,
}
key_zs = {
    "01": 0.050,
    "02": 0.096,
    "03": 0.140,
    "04": 0.185,
}

snapshot_home = Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "snapshots"

with open(snapshot_home / "VialHomeMaster.json", 'r') as fn:
    master_data = json.load(fn)

for column, row in itertools.product(key_ys, key_xs):
    if not key_zs.get(row):
        continue
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["x"] = key_xs.get(row)
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["z"] = key_zs.get(row)
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["y"] = key_ys.get(column)

    # Generate VialHome files
    out_name = "VialHome_{}_{}.json".format(column, row)
    with open(snapshot_home / out_name, "w+") as fn:
        json.dump(master_data, fn, indent=2)

print("Successfully generated snapshots.")

    # # Generate VialHomeAbv files
    # master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["z"] = key_zs.get(row) + 0.1
    # out_name_abv = "VialHome_{}_{}_Abv.json".format(column, row)
    # with open(os.path.join(snapshot_home, out_name_abv), "w+") as fn:
    #     json.dump(master_data, fn, indent=2)


