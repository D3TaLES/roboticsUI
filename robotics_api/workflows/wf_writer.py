import os

# Workflows for running full experiments
# Copyright 2022, University of Kentucky

from fireworks import Workflow
from robotics_api.workflows.Robotics_FW import *
from robotics_api.expflow_parser import EF2Experiment


def run_expflow_wf(expflow_wf: dict,  name_tag='', exp_params={}, **kwargs):
    """
    Establishes Fireworks workflow for running multiple iterations of the same experiment with different molecules
    Args:
        exp_params:
        expflow_wf: dict, experiment dictionary from an ExpFlow instance
        name_tag: str, name tag for workflow
        **kwargs:
    Returns:
        Fireworks Workflow object
    """
    name = expflow_wf.get("name") + "_" + name_tag.strip("_")
    reagents = exp_params.get("reagent_locations", {})
    f10 = InitializeExperiment(name=expflow_wf.get("name") + ("_" + name_tag).strip("_"), reagent_locations=reagents)
    fws = [f10]
    robot_experiments = []

    for i, expflow_exp in enumerate(expflow_wf.get("experiments")):
        exp_params.update({"name": "exp{:02d}".format(i+1), "wflow_name": name})
        experiment = EF2Experiment(expflow_exp, "Robotics", fw_parents=f10, data_type=kwargs.get('data_type', 'cv'), exp_params=exp_params, priority=2)
        fws.extend(experiment.fireworks)
        robot_experiments.append(experiment.end_exp)
        print("------- EXPERIMENT {:02d} ADDED -------".format(i+1))
    fws.append(EndWorkflowProcess(parents=robot_experiments))
    wf = Workflow(fws, name="{}_workflow".format(name))
    return wf


def run_ex_processing(cv_dir=None, molecule_id="test", name_tag="", **kwargs):
    """
    Establishes Fireworks workflow for running an example basic CV
    """
    cv_dir = cv_dir or ["/mnt/external_drive/D3TaLES/robotics/roboticsUI/test_data/scaled_down_exp01_robot_diffusion_cp_8sr/20230320/"]
    cv_locations = [f for f in os.listdir(cv_dir) if f.endswith(".csv")]
    print(cv_locations)
    fws = [CVProcessing(mol_id=molecule_id, cv_locations=cv_locations, **kwargs)]

    wf = Workflow(fws, name="{}_workflow".format(name_tag))
    return wf


if __name__ == "__main__":
    run_ex_processing()
