from fireworks import Firework
from itertools import groupby
from monty.serialization import loadfn
from d3tales_api.Processors.expflow_parser import *
from robotics_api.workflows.Processing import *
from robotics_api.workflows.Robotics_FW import *
from robotics_api.workflows.ExperimentActions import *

BASE_DIR = Path(__file__).resolve().parent


class EF2Experiment(ProcessExpFlowObj):
    def __init__(self, expflow_obj, source_group, fw_parents=None, priority=None, data_type=None, exp_params=0,
                 **kwargs):
        super().__init__(expflow_obj, source_group, **kwargs)
        self.fw_parents = fw_parents
        self.priority = priority if priority > 2 else 2
        self.name = "{}_{}".format(exp_params.get("name") or getattr(self.expflow_obj, 'name', 'exp'), self.molecule_id)
        self.wflow_name = exp_params.get("wflow_name") or getattr(self.expflow_obj, 'wflow_name') or 'robotic_wflow'
        self.rom_id = get_id(self.redox_mol) or "no_redox_mol"
        self.solv_id = get_id(self.solvent) or "no_solvent"
        exp_params.update(
            {"name": self.name, "wflow_name": self.wflow_name, "mol_id": self.molecule_id, "solv_id": self.solv_id})
        self.exp_params = exp_params
        self.end_exp = None

        self.metadata = getattr(ProcessExperimentRun(expflow_obj, source_group), data_type + "_metadata", {})

    @property
    def task_clusters(self):
        all_tasks, task_cluster = [], []
        previous_name = ""
        for task in self.workflow:
            if "process" in task.name:
                all_tasks.append(task_cluster) if task_cluster else None
                all_tasks.append([task])
                task_cluster = []
            elif ("collect" in task.name) != ("collect" in previous_name):
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = [task]
            else:
                task_cluster.append(task)
            previous_name = task.name
        all_tasks.append(task_cluster) if task_cluster else None
        # print([[t.name for t in c] for c in all_tasks])
        return all_tasks

    @property
    def fireworks(self):
        # Return active Firework
        fireworks = []
        parent = self.fw_parents
        for i, cluster in enumerate(self.task_clusters):
            fw_type = cluster[0].name
            tasks = [self.get_firetask(task) for task in cluster]
            priority = self.priority-2 if i == 0 else self.priority-1 if "process" in fw_type else self.priority
            if "process" in fw_type:
                fw = CVProcessing(tasks, name="{}_{}".format(self.name, fw_type), parents=parent, exp_params=self.exp_params,
                                  metadata=self.metadata, mol_id=self.molecule_id, priority=priority)
                parent = fw if "benchmark" in fw_type else parent
            else:
                name = fw_type if "collect" in fw_type else "prep"
                fw = ExpFirework(tasks, name="{}_{}".format(self.name, name), wflow_name=self.wflow_name,
                                 priority=priority, parents=parent, exp_params=self.exp_params)
                parent = fw
            fireworks.append(fw)

        self.end_exp = ExpFirework([EndExperiment(vial_uuid=self.rom_id)], name="{}_end_experiment".format(self.name),
                                   wflow_name=self.wflow_name, priority=self.priority, parents=parent,
                                   exp_params=self.exp_params)  # TODO Change once we have solid dispensing
        fireworks.append(self.end_exp)
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
            "collect_electrode_test": TestElectrode,
        }


if __name__ == "__main__":
    expflow_file = os.path.join(BASE_DIR, 'management/example_expflows', 'cv_robot_diffusion_2_workflow.json')
    expflow_exp = loadfn(expflow_file)
    experiment = EF2Experiment(expflow_exp.get("experiments")[0], "Robotics", data_type='cv')
    experiment.fireworks
