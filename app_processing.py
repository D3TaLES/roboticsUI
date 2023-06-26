import os
import json
import itertools
from pathlib import Path
from monty.serialization import loadfn


def get_exp_reagents(exp_json):
    orig_reagents = [e.get("reagents") for e in exp_json.get("experiments")]
    reagents = list(itertools.chain(*orig_reagents))
    solvents = [(r.get("name"), r.get("smiles")) for r in reagents if r.get("type") == 'solvent']
    molecules = [(r.get("name"), r.get("smiles")) for r in reagents if r.get("type") != 'solvent']
    return sorted(list(set(solvents)), key=lambda x: x[0]) + sorted(list(set(molecules)), key=lambda x: x[0])


def get_exps(exp_json):
    return ["exp{:02d}".format(i+1) for i, _ in enumerate(exp_json.get("experiments"))]


def vial_location_options():
    snapshot_home = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "workflows" / "snapshots")
    # get vial home options
    v_options_raw = [str(f).split(".")[0].strip("VialHome_") for f in os.listdir(snapshot_home) if str(f).startswith("VialHome_")]
    v_options = sorted(list(set(v_options_raw)))
    return v_options


def reagent_location_options():
    snapshot_home = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "workflows" / "snapshots")
    # get solvent options
    s_options = [str(f).split(".")[0] for f in os.listdir(snapshot_home) if str(f).startswith("Solvent")]
    return ["None"] + vial_location_options() + s_options


def assign_locations(reagent_dict, exp_dict, experiment_data):
    print(reagent_dict)
    print(exp_dict)
    # clean reagent data
    reagent_dict = json.loads((json.dumps(reagent_dict)))
    # get experiment reagents
    orig_reagents = [e.get("reagents") for e in experiment_data.get("experiments")]
    reagents = list(itertools.chain(*orig_reagents))
    reagent_locations = {}  # "no_redox_mol": "A_02"}
    for r in reagents:
        r_id = r.get("_id") or r.get("uuid")
        reagent_locations[r_id] = reagent_dict.get(r.get("smiles"))
    print('reagent locations: ', reagent_locations)

    # clean exp data
    exp_dict = json.loads((json.dumps(exp_dict)))

    return dict(reagent_locations=reagent_locations, experiment_locations=exp_dict)


if __name__ == "__main__":
    json_file = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "downloaded_wfs" / "robot_diffusion_2_workflow.json")
    raw_dict = {('Acetonitrile', 'CC#N'): "A_02", ('anthracene-9,10-dione', 'O=C1c2ccccc2C(=O)c3ccccc13'): "A_03"}
    expflow_exp = loadfn(json_file)
    print(assign_locations(raw_dict, expflow_exp))
    # print(location_options())
