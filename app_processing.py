import json
import itertools
from monty.serialization import loadfn
from robotics_api.standard_variables import *


def get_exp_reagents(exp_json):
    orig_reagents = [e.get("reagents") for e in exp_json.get("experiments")]
    reagents = list(itertools.chain(*orig_reagents))
    solvents = list(set([(r.get("name"), r.get("smiles")) for r in reagents if r.get("type") == 'solvent']))
    molecules = list(set([(r.get("name"), r.get("smiles")) for r in reagents if r.get("type") == 'redox_molecule']))
    others = list(set([(r.get("name"), r.get("smiles")) for r in reagents if r.get("type") not in ['solvent', 'redox_molecule']]))
    return sorted(solvents, key=lambda x: x[0]) + sorted(molecules, key=lambda x: x[0]) + sorted(others, key=lambda x: x[0])


def get_exps(exp_json):
    return ["exp{:02d}".format(i + 1) for i, _ in enumerate(exp_json.get("experiments"))]


def vial_location_options():
    return [v for v in VIALS if v not in SOLVENT_VIALS.values()]


def reagent_location_options():
    return ["experiment_vial"] + DISPENSE_STATIONS


def assign_locations(reagent_dict, exp_dict, experiment_data):
    # get experiment reagents
    reagent_dict = json.loads((json.dumps(reagent_dict)))
    orig_reagents = [e.get("reagents") for e in experiment_data.get("experiments")]
    reagents = list(itertools.chain(*orig_reagents))
    for r in reagents:
        r["location"] = reagent_dict.get(r.get("smiles"))

    # clean exp data
    exp_dict = json.loads((json.dumps(exp_dict)))

    return dict(reagents=reagents, experiment_vials=exp_dict)


if __name__ == "__main__":
    json_file = os.path.join(
        Path("C:/Users") / "Lab" / "D3talesRobotics" / "downloaded_wfs" / "robot_diffusion_2_workflow.json")
    raw_dict = {('Acetonitrile', 'CC#N'): "A_02", ('anthracene-9,10-dione', 'O=C1c2ccccc2C(=O)c3ccccc13'): "A_03"}
    expflow_exp = loadfn(json_file)
    print(assign_locations(raw_dict, expflow_exp))
    # print(location_options())
