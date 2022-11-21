from fireworks import Firework
from monty.serialization import loadfn
from d3tales_api.Processors.expflow_parser import *
from robotics_api.workflows.ExperimentActions import *

BASE_DIR = Path(__file__).resolve().parent


class EF2Experiment(ProcessExpFlowObj):
    def __init__(self, expflow_obj, source_group, fw_parents=None, priority=None, data_type=None, exp_params=None, **kwargs):
        super().__init__(expflow_obj, source_group, **kwargs)
        self.fw_parents = fw_parents
        self.priority = priority
        self.exp_params = exp_params
        self.name = getattr(self.expflow_obj, 'name') or 'experiment_fw'

        self.metadata = getattr(ProcessExperimentRun(expflow_obj, source_group), data_type + "_metadata", {})

    @property
    def firetasks(self):
        vial_id = get_id(self.redox_mol)  # TODO change once we have solid dispenser
        all_tasks = [GetSample(vial_uuid=vial_id)]
        for task in self.workflow:
            firetask = self.get_firetask(task)
            all_tasks.append(firetask)
        all_tasks.append(EndExperiment(vial_uuid=vial_id))
        return all_tasks

    @property
    def firework(self):
        # Define Firework specific to this experiment
        class ExpFirework(Firework):
            def __init__(self, firetasks, name=self.name, mol_id=self.molecule_id, priority=self.priority,
                         parents=self.fw_parents, exp_params=self.exp_params, **kwargs):
                spec = {'_category': 'robotics', '_priority': priority} if priority else {'_category': 'robotics'}
                if exp_params:
                    spec.update(exp_params)
                tasks = firetasks
                super(ExpFirework, self).__init__(tasks, parents=parents, spec=spec, name="{}_{}".format(mol_id, name),
                                                  **kwargs)

        # Return active Firework
        return ExpFirework(self.firetasks)

    def get_firetask(self, task):
        firetask = self.task_dictionary.get(task.name)
        parameters_dict = {"start_uuid": task.start_uuid, "end_uuid": task.end_uuid}
        for param in getattr(task, 'parameters', []):
            parameters_dict[param.description] = "{}{}".format(param.value, param.unit)
        return firetask(**parameters_dict)

    @property
    def task_dictionary(self):
        return {
            "transfer_liquid": DispenseLiquid,  # needs: VOLUME
            "transfer_solid": DispenseSolid,  # needs: MASS
            "transfer_apparatus": TransferApparatus,
            "heat": Heat,  # needs: TEMPERATURE
            "heat_stir": HeatStir,  # needs: TEMPERATURE, TIME
            "measure_working_electrode_area": RecordWorkingElectrodeArea,  # needs: SIZE
            "polish": Polish,  # needs: MATERIAL, SIZE
            "sonicate": Sonicate,  # needs: TIME
            "rinse": Rinse,  # needs: TIME
            "dry": Dry,  # needs: TIME
            "collect_cv_data": RunCV,
        }


if __name__=="__main__":
    expflow_file = os.path.join(BASE_DIR, 'management/example_expflows', 'example_expflow.json')
    expflow_exp = loadfn(expflow_file)
    experiment = EF2Experiment(expflow_exp.get("experiments")[0], "Robotics", data_type='cv')
