# Workflows for running full experiments
# Copyright 2024, University of Kentucky

from fireworks import Workflow
from robotics_api.workflows.Robotics_FW import *
from robotics_api.workflows.expflow_parser import EF2Experiment


def run_expflow_wf(expflow_wf: dict,  name_tag='', exp_params=None, **kwargs):
    """
    Establishes Fireworks workflow for running multiple iterations of the same experiment with different molecules
    Args:
        expflow_wf (dict): experiment dictionary from an ExpFlow instance
        name_tag (str): name tag for workflow
        exp_params (dict): experimental parameters that will be passed to the Fireworks specs
        **kwargs: Additional keyword arguments.
    Returns:
        Fireworks Workflow object
    """
    wflow_name = expflow_wf.get("name") + "_" + name_tag.strip("_")
    f10 = InitializeExperiment(wflow_name=wflow_name, fw_specs=exp_params)
    fws = [f10]
    robot_experiments = []

    for i, expflow_exp in enumerate(reversed(expflow_wf.get("experiments", []))):
        idx = len(expflow_wf.get("experiments", [])) - i
        experiment = EF2Experiment(expflow_exp, "Robotics", fw_parents=[f10], data_type=kwargs.get('data_type', 'cv'),
                                   exp_name="exp{:02d}".format(idx), wflow_name=wflow_name,  priority=i+2)
        fws.extend(experiment.fireworks)
        robot_experiments.extend(experiment.end_exps)
        print("------- EXPERIMENT {:02d} ADDED -------".format(idx))
    fws.append(EndWorkflowProcess(parents=robot_experiments))
    wf = Workflow(fws, name="{}_workflow".format(wflow_name))
    return wf


def run_ex_processing(cv_dir=None, molecule_id="test", name_tag="", **kwargs):
    """
    FOR TESTING ONLY
    Establishes Fireworks workflow for running an example basic CV processing job.
    Args:
        cv_dir (str): path the directory containing experimental CV files
        molecule_id (str): D3TaLES ID for redox active molecule
        name_tag (str): tame tag for workflow
        **kwargs: Additional keyword arguments.
    """
    cv_locations = [f for f in os.listdir(cv_dir) if f.endswith(".csv")]

    fws = [CVProcessing(mol_id=molecule_id, cv_locations=cv_locations, **kwargs)]

    wf = Workflow(fws, name="{}_workflow".format(name_tag))
    return wf


if __name__ == "__main__":
    # run_ex_processing()
    downloaded_wfls_dir = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "downloaded_wfs")
    expflow_file = os.path.join(downloaded_wfls_dir, 'SE_Scan_TBAPF6_workflow.json')
    run_expflow_wf(loadfn(expflow_file))
