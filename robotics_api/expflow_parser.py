from fireworks import Firework
from itertools import groupby
from monty.serialization import loadfn
from d3tales_api.Processors.expflow_parser import *
from robotics_api.workflows.Processing import *
from robotics_api.workflows.Robotics_FW import *
from robotics_api.workflows.ExperimentActions import *

BASE_DIR = Path(__file__).resolve().parent


class EF2Experiment(ProcessExpFlowObj):
    def __init__(self, expflow_obj, source_group, fw_parents=None, priority=None, data_type=None, exp_name='exp',
                 wflow_name='robotic_wflow', **kwargs):
        super().__init__(expflow_obj, source_group, **kwargs)
        self.fw_parents = fw_parents
        self.priority = priority if priority > 2 else 2
        self.full_name = "{}_{}".format(exp_name, self.molecule_id)
        self.wflow_name = wflow_name
        self.rom_id = get_id(self.redox_mol) or "no_redox_mol"
        self.solv_id = get_id(self.solvent) or "no_solvent"
        self.metadata = getattr(ProcessExperimentRun(expflow_obj, source_group), data_type + "_metadata", {})
        self.end_exp = None

        self.fw_specs = {"full_name": self.full_name, "wflow_name": self.wflow_name, "exp_name": exp_name,
                         "mol_id": self.molecule_id, "rom_id": self.rom_id, "solv_id": self.solv_id,
                         "metadata": self.metadata}

    @staticmethod
    def collect_task(collect_task, tag="setup", default_analysis="cv"):
        if "_cv_" in collect_task.name or "electrode" in collect_task.name:
            analysis = "cv"
        elif "_ir_" in collect_task.name:
            analysis = "ir"
        # TODO setup more instruments
        else:
            analysis = default_analysis
        task_dict = copy.deepcopy(collect_task.__dict__)
        task_dict["name"] = f"{tag}_{analysis}"
        new_task = dict2obj(task_dict)
        return new_task

    @property
    def task_clusters(self):
        all_tasks, task_cluster = [], []
        if "collect" in self.workflow[0].name:
            task_cluster = [self.collect_task(self.workflow[0], tag="setup")]
        for i, task in enumerate(self.workflow):
            # Get previous and next non-processing name
            next_name = self.workflow[i + 1].name if i + 1 < len(self.workflow) else ""
            count = 2
            while "process" in next_name:
                next_name = self.workflow[i + count].name if i + count < len(self.workflow) else ""
                count += 1
            previous_name = self.workflow[i - 1].name if i > 0 else ""
            count = 2
            while "process" in previous_name:
                previous_name = self.workflow[i - count].name if i - count > 0 else ""
                count += 1

            if "process" in task.name:
                all_tasks.append(task_cluster) if task_cluster else None
                all_tasks.append([task])
                task_cluster = []
            elif "collect" not in task.name and "collect" in previous_name:
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = [self.collect_task(self.workflow[i + 1], tag="finish"), task]
            elif "collect" in task.name and "collect" not in previous_name:
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = [task]
            else:
                task_cluster.append(task)
                if "collect" in next_name and "collect" not in task.name:
                    all_tasks.append(task_cluster) if task_cluster else None
                    task_cluster = [self.collect_task(self.workflow[i + 1], tag="setup")]

            # Finish experiment if at end
            if "collect" in task.name and not next_name:
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = [self.collect_task(self.workflow[i + 1], tag="finish")]

        all_tasks.append(task_cluster) if task_cluster else None
        print([[t.name for t in c] for c in all_tasks])
        return all_tasks

    @property
    def fireworks(self):
        # Return active Firework
        fireworks = []
        parent = self.fw_parents
        collect_parent = None
        for i, cluster in enumerate(self.task_clusters):
            fw_type = cluster[0].name
            tasks = [self.get_firetask(task) for task in cluster]
            priority = self.priority - 2 if i == 0 else self.priority - 1 if "process" in fw_type else self.priority
            if "process" in fw_type:
                fw = CVProcessing(tasks, name="{}_{}".format(self.full_name, fw_type), parents=collect_parent or parent,
                                  fw_specs=self.fw_specs, mol_id=self.molecule_id, priority=priority)
                parent = fw if "benchmark" in fw_type else parent
            elif "setup" in fw_type:
                name = "{}_{}".format(self.full_name, fw_type)
                fw = InstrumentPrepFirework(tasks, name=name, wflow_name=self.wflow_name, priority=priority,
                                            analysis=fw_type.split("_")[1], parents=parent, fw_specs=self.fw_specs)
                parent = fw
            elif "collect" in fw_type:
                fw = AnalysisFirework(tasks, name="{}_{}".format(self.full_name, fw_type), wflow_name=self.wflow_name,
                                      priority=priority, parents=parent, fw_specs=self.fw_specs)
                parent = fw
                collect_parent = fw
            else:
                fw = RobotFirework(tasks, name="{}_robot".format(self.full_name), wflow_name=self.wflow_name,
                                   priority=priority, parents=parent, fw_specs=self.fw_specs)
                parent = fw
                self.end_exp = fw
            fireworks.append(fw)
        self.end_exp.spec.update({"end_experiment": True})
        return fireworks

    def get_firetask(self, task):
        firetask = self.task_dictionary.get(task.name)
        parameters_dict = {"start_uuid": task.start_uuid, "end_uuid": task.end_uuid}
        for param in getattr(task, 'parameters', []) or []:
            parameters_dict[param.description] = "{}{}".format(param.value, param.unit)
        print("Firetask {} added.".format(task.name))
        return firetask(**parameters_dict)

    @property
    def task_dictionary(self):
        return {
            "transfer_liquid": DispenseLiquid,  # needs: VOLUME
            "transfer_solid": DispenseSolid,  # needs: MASS
            "heat": Heat,  # needs: TEMPERATURE
            "heat_stir": HeatStir,  # needs: TEMPERATURE, TIME
            "measure_working_electrode_area": RecordWorkingElectrodeArea,  # needs: SIZE
            "rinse_electrode": RinseElectrode,  # needs: TIME
            "clean_electrode": CleanElectrode,
            "collect_cv_data": RunCV,
            "process_cv_data": CVProcessor,
            "process_cv_benchmarking": ProcessCVBenchmarking,
            "collect_electrode_test": RunCV,  # TODO remove eventually
            "collect_electrode_test_data": RunCV,  # TODO remove eventually
            "collect_cv_benchmark_data": BenchmarkCV,

            "setup_cv": SetupPotentiostat,
            "finish_cv": FinishPotentiostat,
        }


if __name__ == "__main__":
    expflow_file = os.path.join(BASE_DIR, 'management/example_expflows', 'cv_robot_diffusion_2_workflow.json')
    expflow_exp = loadfn(expflow_file)
    experiment = EF2Experiment(expflow_exp.get("experiments")[0], "Robotics", data_type='cv')
    experiment.fireworks
