import os

# Workflows for running full experiments
# Copyright 2022, University of Kentucky

from fireworks import Workflow
from robotics_api.workflows.Robotics_FW import *
from robotics_api.expflow_parser import EF2Experiment


def run_expflow_wf(expflow_wf: dict,  name_tag='', exp_params=None, **kwargs):
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
    exp_params.update({"name": name})
    f10 = InitializeExperiment(name=expflow_wf.get("name") + "_" + name_tag.strip("_"))
    robot_experiments = []
    fws = [f10]

    for i, expflow_exp in enumerate(expflow_wf.get("experiments")):
        exp_params.update({"name": "{}_exp{:02d}_{}".format(name_tag.strip("_"), i+1, expflow_wf.get("name")), "wflow_name": expflow_wf.get("name")})
        experiment = EF2Experiment(expflow_exp, "Robotics", fw_parents=f10, data_type=kwargs.get('data_type', 'cv'), exp_params=exp_params, priority=2)
        exp_fw = experiment.firework
        process_fw = CVProcessing(mol_id=experiment.molecule_id, parents=exp_fw, metadata=experiment.metadata, priority=3, **kwargs)
        fws.extend([exp_fw, process_fw])
        robot_experiments.append(exp_fw)
    fws.append(EndWorkflowProcess(parents=robot_experiments))

    wf = Workflow(fws, name="{}_workflow".format(name))
    return wf


def run_ex_cv(identifiers: list, expflow_wf: dict,  name_tag='', **kwargs):
    """
    Establishes Fireworks workflow for running an example basic CV
    """
    f10 = InitializeExperiment(mol_ids=identifiers, name_tag=name_tag)

    fws = [f10]
    for expflow_exp in expflow_wf.get("experiments"):
        experiment = EF2Experiment(expflow_exp, "Robotics")
        exp_fw = BasicCV()
        process_fw = CVProcessing(mol_id=experiment.molecule_id, parents=exp_fw, **kwargs)
        fws.extend([exp_fw, process_fw])

    wf = Workflow(fws, name="{}_workflow".format(name_tag))
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
