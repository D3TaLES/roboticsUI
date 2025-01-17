# Workflows for running full experiments
# Copyright 2024, University of Kentucky

import copy
import os.path
from functools import reduce
from operator import iconcat
from fireworks import Workflow
from d3tales_api.Processors.expflow_parser import ProcessExperimentRun, get_id

from robotics_api.fireworks.Fireworks import *
from robotics_api.fireworks.Firetasks_Actions import *


class EF2Experiment:
    """
    Class for converting an ExpFlow robotics workflow into a Fireworks Workflow that
    can be run on the robotic setup.

    Args:
        expflow_obj: The ExpFlow object (often parsed from a JSON).
        source_group (str): Source group for the experiment.
        fw_parents (list): List of parent Fireworks.
        priority (int): Priority of the Firework.
        data_type (str): Type of experiment data.
        exp_name (str): Name of the experiment.
        wflow_name (str): Name of the workflow.
        **kwargs: Additional keyword arguments.

    Attributes:
        fw_parents (list): List of parent Fireworks.
        priority (int): Priority of the Firework.
        full_name (str): Full name of the experiment.
        wflow_name (str): Name of the workflow.
        rom_id (str): Redox molecule ID.
        rom_name (str): Redox molecule name.
        solv_id (str): Solvent ID.
        metadata (dict): Metadata related to the experiment.
        fw_specs (dict): Specifications for the Firework.
        workflow (list): List of tasks in the experiment workflow.

    """

    def __init__(self, expflow_obj, source_group, fw_parents=None, priority=0, data_type=None, exp_name='exp',
                 wflow_name='robotic_wflow', **kwargs):
        expflow_parser = ProcessExperimentRun(expflow_obj, source_group, redox_id_error=False, try_restapi=True, **kwargs)
        self.fw_parents = fw_parents or []
        self.priority = priority if priority > 2 else 2
        self.mol_id = expflow_parser.molecule_id or getattr(expflow_parser.redox_mol, "smiles", None)
        self.rom_name = getattr(expflow_parser.redox_mol, "name", "no_redox_mol_name")
        self.full_name = "{}_{}".format(exp_name, self.mol_id)
        self.wflow_name = wflow_name

        self.rom_id = get_id(expflow_parser.redox_mol) or "no_redox_mol"
        self.solv_id = get_id(expflow_parser.solvent) or "no_solvent"
        self.elect_id = get_id(expflow_parser.electrolyte) or "no_electrolyte"
        self.metadata = getattr(expflow_parser, data_type + "_metadata", {})
        self.end_exps = []

        self.fw_specs = {"full_name": self.full_name, "wflow_name": self.wflow_name, "exp_name": exp_name,
                         "mol_id": self.mol_id, "rom_id": self.rom_id, "solv_id": self.solv_id,
                         "elect_id": self.elect_id, "metadata": self.metadata, "rom_name": self.rom_name}

        # Check for multi tasks
        self.workflow = []
        [self.workflow.extend(self.check_multi_task(t)) for t in expflow_parser.expflow_obj.workflow]

    @staticmethod
    def instrument_task(collect_task, tag="setup", default_analysis=""):
        """Generates setup or finish tasks"""
        analysis_methods = ["cv", "cvUM", "ca", "ir", ]
        analysis = default_analysis
        for method in analysis_methods:
            if f"_{method}_" in collect_task.name:
                analysis = method
        task_dict = copy.deepcopy(collect_task.__dict__)
        task_dict["name"] = f"{tag}_{analysis}"
        new_task = dict2obj(task_dict)
        return new_task

    @staticmethod
    def process_task(collect_task):
        """Generates a processing task"""
        task_dict = copy.deepcopy(collect_task.__dict__)
        task_dict["name"] = f"process_data"
        new_task = dict2obj(task_dict)
        return new_task

    @staticmethod
    def is_inst_task(task):
        """Checks if a task is an instrument task"""
        task_name = task if isinstance(task, str) else getattr(task, "name", "")
        instrument_tasks = ['collect']
        for i_t in instrument_tasks:
            if i_t in task_name:
                return True
        return False

    @staticmethod
    def check_multi_task(task):
        """Checks for multitasks in the workflow."""
        if "multi_cv" in task.name:
            task_list = []
            scan_rates_param = [p for p in task.parameters if "scan_rate" in p.description][0]
            other_params = [p for p in task.parameters if "scan_rate" not in p.description]
            for i, scan_rate in enumerate(scan_rates_param.value.strip(" ").split(",")):
                task_dict = copy.deepcopy(task.__dict__)
                task_dict["name"] = "collect_cv_data"
                task_dict["parameters"] = other_params + [
                    {
                        "description": "scan_rate",
                        "value": scan_rate,
                        "unit": scan_rates_param.unit
                    }
                ]
                task_list.append(dict2obj(task_dict))
            return task_list
        else:
            return [task]

    @staticmethod
    def same_positions(task1, task2):
        if getattr(task1, "start_uuid", 1) == getattr(task2, "start_uuid", 2):
            if getattr(task1, "end_uuid") == getattr(task2, "end_uuid"):
                return True
        return False

    @property
    def task_clusters(self):
        """Generates task clusters for the workflow."""

        all_tasks, task_cluster, active_method = [], [], 'robot'
        if self.is_inst_task(self.workflow[0]):
            task_cluster = [self.instrument_task(self.workflow[0], tag="setup")]
            active_method = self.workflow[0].name.split("_")[1]
        for i, task in enumerate(self.workflow):
            # Get previous and next task names
            previous_name = self.workflow[:i][-1].name if self.workflow[:i] else ""
            next_name = self.workflow[i + 1:][0].name if self.workflow[i + 1:] else ""
            # Get next non-processing name
            next_nonP_tasks = [t for t in self.workflow[i + 1:] if "process" not in t.name]
            next_nonP = next_nonP_tasks[0] if next_nonP_tasks else ""

            # If a dispense liquid action dispense 0 volume, skip all remaining tasks.
            if EXIT_ZERO_VOLUME and task.name == "transfer_liquid":
                volumes = [float(p.value) for p in task.parameters if p.description == "volume"]
                if not sum(volumes):
                    warnings.warn(f"Action {task.name} dispenses 0 volume. Because setting EXIT_ZERO_VOLUME is True, "
                                  f"all remaining tasks will be skipped.")
                    break

            # Set up task clusters based on task types
            if "process" in task.name or "rinse" in task.name:
                # Make own Fireworks for processing or rinse jobs
                all_tasks.extend([task_cluster, [task]]) if task_cluster else all_tasks.append([task])
                task_cluster = []
                if "process" in next_name:
                    continue
            elif self.is_inst_task(task) and not self.is_inst_task(previous_name):
                # Make own Firework for collect jobs
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = [task]
            else:
                # Extend current task cluster if not a special case
                task_cluster.append(task)

            # Create setup Firetasks if about to start collect jobs and finish Firetasks if at end of measurements
            next_method = next_nonP.name.split("_")[1] if self.is_inst_task(next_nonP) else 'robot'

            # Separate test CV runs by erasing active method if the positions in collect tasks are not teh same
            if self.is_inst_task(task) and self.is_inst_task(next_nonP) and (not self.same_positions(task, next_nonP)):
                active_method = None

            # Add additional tasks based on active and next methods
            if next_method != active_method:  # or "transfer_liquid" in task.name:
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = []
                if "collect" in task.name and "process" not in next_name:
                    all_tasks.append([self.process_task(task)])
                if self.is_inst_task(task):
                    task_cluster.append(self.instrument_task(task, tag="finish"))
                if self.is_inst_task(next_nonP):
                    task_cluster.append(self.instrument_task(next_nonP, tag="setup"))
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = []

            active_method = next_method

        all_tasks.append(task_cluster) if task_cluster else None
        [print(f"FW {i + 1}:\t", [c.name for c in clus]) for i, clus in enumerate(all_tasks)]
        return all_tasks

    @property
    def fireworks(self):
        """Generates a list of Fireworks for the experiment"""
        # Return active Firework
        fireworks, end_exp = [], None
        parent = self.fw_parents
        collect_parent = None
        for i, cluster in enumerate(self.task_clusters):
            fw_type = cluster[0].name
            # Turn tasks into Firetasks and flatten resulting list
            tasks = reduce(iconcat, [self.get_firetask(task) for task in cluster], [])
            if "process" in fw_type:
                fw = ProcessingFirework(tasks, name=f"{self.full_name}_{fw_type}", parents=collect_parent or parent,
                                        fw_specs=self.fw_specs, mol_id=self.mol_id, priority=self.priority - 1)
                parent = fw if "benchmark" in fw_type else parent
            elif "rinse" in fw_type:
                r1 = RobotFirework(
                    [SetupRinsePotentiostat(start_uuid=cluster[0].start_uuid, end_uuid=cluster[0].end_uuid)],
                    name=f"{self.full_name}_setup", parents=parent, priority=self.priority + 2,
                    wflow_name=self.wflow_name, fw_specs=self.fw_specs
                )
                r2 = AnalysisFirework(tasks, name=f"{self.full_name}_{fw_type}", parents=[r1],
                                      priority=self.priority + 1, wflow_name=self.wflow_name, fw_specs=self.fw_specs)
                r3 = RobotFirework([FinishPotentiostat()], name=f"{self.full_name}_finish", parents=[r2],
                                   priority=self.priority + 3, wflow_name=self.wflow_name, fw_specs=self.fw_specs)
                fireworks.extend([r1, r2, r3])
                self.end_exps.append(r3)
                continue
            elif "setup" in fw_type:
                name = f"{self.full_name}_{fw_type}"
                fw = InstrumentPrepFirework(tasks, name=name, wflow_name=self.wflow_name, priority=self.priority + 1,
                                            analysis=fw_type.split("_")[1], parents=parent, fw_specs=self.fw_specs)
                parent = fw
            elif self.is_inst_task(fw_type):
                fw = AnalysisFirework(tasks, name=f"{self.full_name}_{fw_type}", wflow_name=self.wflow_name,
                                      priority=self.priority, parents=parent, fw_specs=self.fw_specs)
                parent = fw
                collect_parent = fw
            else:
                p = self.priority + 2 if "finish" in fw_type else self.priority - 2 if "transfer" in fw_type else self.priority
                fw = RobotFirework(tasks, name=f"{self.full_name}_{fw_type}", wflow_name=self.wflow_name,
                                   priority=p, parents=parent, fw_specs=self.fw_specs)
                parent = fw
                end_exp = fw
            fireworks.append(fw)
        end_exp.spec.update({"end_experiment": True})
        self.end_exps.append(end_exp)
        return fireworks

    def get_firetask(self, task):
        """Retrieves associated Firetasks for the given ExpFlow task."""
        firetasks = self.task_dictionary.get(task.name)
        if not firetasks:
            raise KeyError(f"Firetask {task.name} not found in task_dictionary.")
        parameters_dict = {"start_uuid": task.start_uuid, "end_uuid": task.end_uuid}
        for param in getattr(task, 'parameters', []) or []:
            if param.value:
                parameters_dict[param.description] = "{}{}".format(param.value, param.unit)
        print("Firetask {} added.".format(task.name))
        return [firetask(parameters_dict) for firetask in firetasks]

    @property
    def task_dictionary(self):
        """Returns dictionary mapping ExpFlow tasks to Firetasks."""
        return {
            "transfer_liquid": [DispenseLiquid],  # needs: VOLUME
            "transfer_solid": [DispenseSolid],  # needs: MASS
            "heat": [Heat],  # needs: TEMPERATURE
            "stir": [Stir],  # needs: TIME
            "measure_density": [MeasureDensity],
            "rinse_electrode": [RinseElectrode],  # needs: TIME
            "clean_electrode": [CleanElectrode],
            "collect_cv_data": [RunCV],
            "collect_cvUM_data": [RunCVUM],
            "collect_ca_data": [RunCA],
            "collect_temperature": [CollectTemp],
            "process_calibration": [ProcessCalibration],
            "process_data": [DataProcessor],
            "collect_cv_benchmark_data": [BenchmarkCV, ProcessCVBenchmarking],

            "setup_cv": [SetupCVPotentiostat],
            "setup_cvUM": [SetupCVUMPotentiostat],
            "setup_ca": [SetupCAPotentiostat],
            "finish_cv": [FinishPotentiostat],
            "finish_cvUM": [FinishPotentiostat],
            "finish_ca": [FinishPotentiostat],

            # TODO Deprecated. Remove eventually
            "process_working_electrode_area": [],  # needs: SIZE
            "heat_stir": [Stir],  # needs: TEMPERATURE, TIME
            "process_cv_benchmarking": [ProcessCVBenchmarking],
            "measure_working_electrode_area": [],
            "process_cv_data": [DataProcessor],
            "collect_electrode_test": [RunCV],
            "collect_electrode_test_data": [RunCV],
            "finish_": [FinishPotentiostat],
        }


def run_expflow_wf(expflow_wf: dict, name_tag='', exp_params=None, **kwargs):
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
    f10 = InitializeWorkflow(wflow_name=wflow_name, fw_specs=exp_params)
    fws = [f10]
    robot_experiments = []

    for i, expflow_exp in enumerate(reversed(expflow_wf.get("experiments", []))):
        idx = len(expflow_wf.get("experiments", [])) - i
        experiment = EF2Experiment(expflow_exp, "Robotics", fw_parents=[f10], data_type=kwargs.get('data_type', 'cv'),
                                   exp_name="exp{:02d}".format(idx), wflow_name=wflow_name, priority=i + 2)
        fws.extend(experiment.fireworks)
        robot_experiments.extend(experiment.end_exps)
        print("------- EXPERIMENT {:02d} ADDED -------".format(idx))
    fws.append(EndWorkflowProcess(parents=robot_experiments))
    wf = Workflow(fws, name="{}_workflow".format(wflow_name))
    return wf


def run_ex_processing(experiment_dir=None, molecule_id="test", name_tag="", **kwargs):
    """
    FOR TESTING ONLY
    Establishes Fireworks workflow for running an example basic CV processing job.
    Args:
        experiment_dir (str): path the directory containing experimental CV files
        molecule_id (str): D3TaLES ID for redox active molecule
        name_tag (str): tame tag for workflow
        **kwargs: Additional keyword arguments.
    """
    cv_locations = [f for f in os.listdir(experiment_dir) if f.endswith(".csv")]

    fws = [ProcessingFirework(mol_id=molecule_id, cv_locations=cv_locations, **kwargs)]

    wf = Workflow(fws, name="{}_workflow".format(name_tag))
    return wf


if __name__ == "__main__":
    # run_ex_processing()
    expflow_file = TEST_DATA_DIR / 'workflows' / 'Cond3_all_TEMPO_workflow.json'
    expflow_experiment = loadfn(expflow_file)
    # experiment = EF2Experiment(expflow_experiment.get("experiments")[1], "Robotics", data_type='cv')
    # tc = experiment.task_clusters
    ex_params = {"experiment_vials": {"exp01": "A_01", "exp02": "A_02"},
                 "reagents": [{"_id": "29690ed4-bf85-4945-9c2d-907eb942515d","description": "solvent","location": "solvent_02","name": "Acetonitrile","notes": "","purity": "","smiles": "CC#N","source": "sigma_aldrich","type": "solvent"},
                              {"_id": "f12e7ae7-e893-44b9-8fee-51787f23fbdb","description": "supporting electrolyte","location": "experiment_vial","name": "TBAPF6","notes": "","purity": "","smiles": " F[P-](F)(F)(F)(F)F.CCCC[N+](CCCC)(CCCC)CCCC","source": "sigma_aldrich","type": "electrolyte"},
                              {"_id": "330391e4-855b-4a1d-851e-59445c65fad0","description": "redox active molecule(s) (a.k.a. redox core)","location": "experiment_vial","name": "TEMPO","notes": "","purity": "","smiles": "CC1(C)CCCC(C)(C)N1[O]","source": "uk_lab","type": "redox_molecule"}]
                 }
    wf_obj = run_expflow_wf(expflow_experiment, exp_params=ex_params)
    # LaunchPad().from_file(os.path.abspath(LAUNCHPAD)).add_wf(wf_obj)
