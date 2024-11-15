import json
import itertools
from pathlib import Path

theta_x = 90
theta_y = 0
theta_z = 103
key_ys = {
    "S": 0.266,
    "A": 0.162,
    "B": 0.058,
    "C": -0.035,
    "D": -0.997,
}
key_xs = {
    "01": 0.551,
    "02": 0.586,
    "03": 0.622,
    "04": 0.658,
}
key_zs = {
    "01": 0.053,
    "02": 0.098,
    "03": 0.143,
    "04": 0.188,
}

snapshot_home = Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "snapshots"

with open(snapshot_home / "VialHomeMaster.json", 'r') as fn:
    master_data = json.load(fn)

for column, row in itertools.product(key_ys, key_xs):
    if not key_zs.get(row):
        continue
    out_name = "VialHome_{}_{}.json".format(column, row)
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["x"] = key_xs.get(row)
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["z"] = key_zs.get(row)
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["y"] = key_ys.get(column)
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["thetaX"] = theta_x
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["thetaY"] = theta_y
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["thetaZ"] = theta_z
    master_data["poses"]["pose"][0]["name"] = "VHome_{}_{}".format(column, row)
    # Generate VialHome files
    with open(snapshot_home / out_name, "w+") as fn:
        json.dump(master_data, fn, indent=2)

print("Successfully generated snapshots.")

# # Generate VialHomeAbv files
# master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["z"] = key_zs.get(row) + 0.1
# out_name_abv = "VialHome_{}_{}_Abv.json".format(column, row)
# with open(os.path.join(snapshot_home, out_name_abv), "w+") as fn:
#     json.dump(master_data, fn, indent=2)
