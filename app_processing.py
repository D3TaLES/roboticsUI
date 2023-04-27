import os
import json
import itertools
from pathlib import Path
from monty.serialization import loadfn


def get_exp_reagents(exp_json):
    orig_reagents = [e.get("reagents") for e in exp_json.get("experiments")]
    reagents = list(itertools.chain(*orig_reagents))
    molecules = [(r.get("name"), r.get("smiles")) for r in reagents]
    return set(molecules)


def location_options():
    snapshot_home = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api" / "workflows" / "snapshots")
    # get vial home options
    v_options_raw = [f.split(".")[0].split("_")[1:3] for f in os.listdir(snapshot_home) if f.startswith("VialHome")]
    v_options_set = set([frozenset(o) for o in v_options_raw if not o[0].isdigit()])
    v_options = sorted([sorted(list(s), reverse=True) for s in v_options_set])
    # get solvent options
    s_options_raw = [f.split(".")[0].split("_")[1] for f in os.listdir(snapshot_home) if f.startswith("Solvent")]
    s_options = [['solv', i] for i in s_options_raw]
    return v_options + s_options


def assign_reagent_locations(raw_app_data, experiment_data):
    # clean reagent data
    smiles_dict = {k[1]: v.replace('\'', "").strip('][').strip(')(').split(', ') for k, v in raw_app_data.items()}
    reagent_dict = json.loads((json.dumps(smiles_dict)))

    # get experiment reagents
    orig_reagents = [e.get("reagents") for e in experiment_data.get("experiments")]
    reagents = list(itertools.chain(*orig_reagents))
    reagent_locations = {"no_redox_mol": ["A", "02"]}
    for r in reagents:
        r_id = r.get("_id") or r.get("uuid")
        reagent_locations[r_id] = reagent_dict.get(r.get("smiles"))
    print('reagent locations: ', reagent_locations)
    return dict(reagent_locations=reagent_locations)


if __name__ == "__main__":
    json_file = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "downloaded_wfs" / "robot_diffusion_2_workflow.json")
    raw_dict = {('Acetonitrile', 'CC#N'): "('A', '02')", ('anthracene-9,10-dione', 'O=C1c2ccccc2C(=O)c3ccccc13'): "('A', '03')", ('cyclohexa-2,5-diene-1,4-dione', 'O=c1ccc(=O)cc1'): "('A', '04')"}
    expflow_exp = loadfn(json_file)
    assign_reagent_locations(raw_dict, expflow_exp)
