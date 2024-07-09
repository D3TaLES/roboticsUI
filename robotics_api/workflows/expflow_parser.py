import copy
from functools import reduce
from operator import iconcat
from d3tales_api.Processors.expflow_parser import *
from robotics_api.workflows.Robotics_FW import *
from robotics_api.workflows.ExperimentActions import *


class EF2Experiment(ProcessExpFlowObj):
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
        super().__init__(expflow_obj, source_group, redox_id_error=False, **kwargs)
        self.fw_parents = fw_parents or []
        self.priority = priority if priority > 2 else 2
        self.mol_id = self.molecule_id or getattr(self.redox_mol, "smiles", None)
        self.rom_name = getattr(self.redox_mol, "name", "no_redox_mol_name")
        self.full_name = "{}_{}".format(exp_name, self.rom_name)
        self.wflow_name = wflow_name
        self.rom_id = get_id(self.redox_mol) or "no_redox_mol"
        self.solv_id = get_id(self.solvent) or "no_solvent"
        self.elect_id = get_id(self.electrolyte) or "no_electrolyte"
        self.metadata = getattr(ProcessExperimentRun(expflow_obj, source_group, redox_id_error=False), data_type + "_metadata", {})
        self.end_exps = []

        self.fw_specs = {"full_name": self.full_name, "wflow_name": self.wflow_name, "exp_name": exp_name,
                         "mol_id": self.mol_id, "rom_id": self.rom_id, "solv_id": self.solv_id,
                         "elect_id": self.elect_id, "metadata": self.metadata, "rom_name": self.rom_name}

        # Check for multi tasks
        self.workflow = []
        [self.workflow.extend(self.check_multi_task(t)) for t in self.expflow_obj.workflow]

    @staticmethod
    def instrument_task(collect_task, tag="setup", default_analysis=""):
        """Generates setup or finish tasks"""
        if "_cv_" in collect_task.name:
            analysis = "cv"
        elif "_ca_" in collect_task.name:
            analysis = "ca"
        elif "_ir_" in collect_task.name:
            analysis = "ir"
        else:
            analysis = default_analysis
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
            next_name = self.workflow[i+1:][0].name if self.workflow[i+1:] else ""
            # Get next non-processing name
            next_nonP_tasks = [t for t in self.workflow[i+1:] if "process" not in t.name]
            next_nonP = next_nonP_tasks[0] if next_nonP_tasks else ""

            # Set up task clusters based on task types
            if "process" in task.name or "rinse" in task.name:
                # Make new Fireworks for processing or rinse jobs
                all_tasks.extend([task_cluster, [task]]) if task_cluster else all_tasks.append([task])
                task_cluster = []
                if "process" in next_name:
                    continue
            elif self.is_inst_task(task) and not self.is_inst_task(previous_name):
                # Make new Firework for collect jobs
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

            if next_method != active_method:
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = []
                if "collect" in task.name and "process" not in next_name:
                    all_tasks.append([self.process_task(task)])
                if self.is_inst_task(task):
                    task_cluster.append(self.instrument_task(task, tag="finish"))
                if self.is_inst_task(next_nonP):
                    task_cluster.append(self.instrument_task(next_nonP, tag="setup"))
                all_tasks.append(task_cluster)
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
                fw = CVProcessing(tasks, name=f"{self.full_name}_{fw_type}", parents=collect_parent or parent,
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
                r3 = RobotFirework([FinishPotentiostat()], name=f"{self.full_name}_finish",  parents=[r2],
                                   priority=self.priority + 3, wflow_name=self.wflow_name, fw_specs=self.fw_specs)
                fireworks.extend([r1, r2, r3])
                self.end_exps.append(r3)
                continue
            elif "setup" in fw_type:
                name = f"{self.full_name}_{fw_type}"
                fw = InstrumentPrepFirework(tasks, name=name, wflow_name=self.wflow_name, priority=self.priority+1,
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
        parameters_dict = {"start_uuid": task.start_uuid, "end_uuid": task.end_uuid}
        for param in getattr(task, 'parameters', []) or []:
            if param.value:
                parameters_dict[param.description] = "{}{}".format(param.value, param.unit)
        print("Firetask {} added.".format(task.name))
        return [firetask(**parameters_dict) for firetask in firetasks]

    @property
    def task_dictionary(self):
        """Returns dictionary mapping ExpFlow tasks to Firetasks."""
        return {
            "transfer_liquid": [DispenseLiquid],  # needs: VOLUME
            "transfer_solid": [DispenseSolid],  # needs: MASS
            "heat": [Heat],  # needs: TEMPERATURE
            "stir": [Stir],  # needs: TIME
            "process_working_electrode_area": [RecordWorkingElectrodeArea],  # needs: SIZE
            "rinse_electrode": [RinseElectrode],  # needs: TIME
            "clean_electrode": [CleanElectrode],
            "collect_cv_data": [RunCV],
            "collect_ca_data": [RunCA],
            "process_calibration": [ProcessCalibration],
            "process_data": [RecordWorkingElectrodeArea, DataProcessor],
            "collect_cv_benchmark_data": [BenchmarkCV, ProcessCVBenchmarking],

            "setup_cv": [SetupCVPotentiostat],
            "setup_ca": [SetupCAPotentiostat],
            "finish_cv": [FinishPotentiostat],
            "finish_ca": [FinishPotentiostat],

            # TODO Deprecated. Remove eventually
            "heat_stir": [Stir],  # needs: TEMPERATURE, TIME
            "process_cv_benchmarking": [ProcessCVBenchmarking],
            "measure_working_electrode_area": [RecordWorkingElectrodeArea],
            "process_cv_data": [DataProcessor],
            "collect_electrode_test": [RunCV],
            "collect_electrode_test_data": [RunCV],
            "finish_": [FinishPotentiostat],
        }


if __name__ == "__main__":
    downloaded_wfls_dir = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "downloaded_wfs")
    expflow_file = os.path.join(downloaded_wfls_dir, 'Cond3_all_TEMPO_workflow.json')
    expflow_exp = loadfn(expflow_file)
    experiment = EF2Experiment(expflow_exp.get("experiments")[0], "Robotics", data_type='cv')
    tc = experiment.task_clusters
