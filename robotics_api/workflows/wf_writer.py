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
    wf_name = expflow_wf.get("name") + "_" + name_tag.strip("_")
    f10 = InitializeExperiment(wflow_name=wf_name, exp_params=exp_params)
    fws = [f10]
    robot_experiments = []

    for i, expflow_exp in enumerate(expflow_wf.get("experiments")):
        experiment = EF2Experiment(expflow_exp, "Robotics", fw_parents=f10, data_type=kwargs.get('data_type', 'cv'),
                                   exp_name="exp{:02d}".format(i+1), wflow_name=wf_name,  priority=2)
        fws.extend(experiment.fireworks)
        robot_experiments.append(experiment.end_exp)
        print("------- EXPERIMENT {:02d} ADDED -------".format(i+1))
    fws.append(EndWorkflowProcess(parents=robot_experiments))
    wf = Workflow(fws, name="{}_workflow".format(wf_name))
    return wf


def run_ex_processing(cv_dir=None, molecule_id="test", name_tag="", **kwargs):
    """
    Establishes Fireworks workflow for running an example basic CV
    """
    cv_locations = [f for f in os.listdir(cv_dir) if f.endswith(".csv")]
    print(cv_locations)
    fws = [CVProcessing(mol_id=molecule_id, cv_locations=cv_locations, **kwargs)]

    wf = Workflow(fws, name="{}_workflow".format(name_tag))
    return wf


if __name__ == "__main__":
    run_ex_processing()
