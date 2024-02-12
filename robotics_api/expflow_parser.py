from d3tales_api.Processors.expflow_parser import *
from robotics_api.workflows.Robotics_FW import *
from robotics_api.workflows.ExperimentActions import *


class EF2Experiment(ProcessExpFlowObj):
    def __init__(self, expflow_obj, source_group, fw_parents=None, priority=0, data_type=None, exp_name='exp',
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

        # Check for multi tasks
        self.workflow = []
        [self.workflow.extend(self.check_multi_task(t)) for t in self.expflow_obj.workflow]


    @staticmethod
    def collect_task(collect_task, tag="setup", default_analysis="cv"):
        if any(kw in collect_task.name for kw in ["_cv_", "electrode"]):
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
    def check_multi_task(task):
        if "multi_cv" in task.name:
            task_list = []
            scan_rates_param = [p for p in task.parameters if p.description == "scan_rates"][0]
            voltages_param = [p for p in task.parameters if p.description == "voltage_sequence"][0]
            for i, scan_rate in enumerate(scan_rates_param.value.strip(" ").split(",")):
                task_dict = copy.deepcopy(task.__dict__)
                task_dict["name"] = "collect_cv_data"
                task_dict["parameters"] = [
                        voltages_param.__dict__,
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

    @property
    def task_clusters(self):
        all_tasks, task_cluster, active_method = [], [], None
        if "collect" in self.workflow[0].name:
            task_cluster = [self.collect_task(self.workflow[0], tag="setup")]
        for i, task in enumerate(self.workflow):
            # Get previous and next task name
            previous_name = self.workflow[:i][-1].name if self.workflow[:i] else ""
            next_name = self.workflow[i+1:][0].name if self.workflow[i+1:] else ""
            # Get next non-processing name
            next_nonP_tasks = [t for t in self.workflow[i+1:] if "process" not in t.name]
            next_nonP_name = next_nonP_tasks[0].name if next_nonP_tasks else ""
            next_nonP_start = next_nonP_tasks[0].start_type if next_nonP_tasks else ""

            # Set up task clusters based on task types
            if "process" in task.name:
                # Make new Fireworks for processing jobs
                all_tasks.extend([task_cluster, [task]]) if task_cluster else all_tasks.append([task])
                task_cluster = []
                if "process" in next_name:
                    continue
            elif "collect" in task.name and "collect" not in previous_name:
                # Make new Firework for collect jobs
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = [task]
            else:
                # Extend current task cluster if not a special case
                task_cluster.append(task)

            # Create setup Firetasks if about to start collect jobs
            method = next_nonP_name.split("_")[1] if "collect" in next_nonP_name else None
            print(task.name)
            print(task.start_type)
            print("---", active_method)
            if method != active_method and "collect" in next_nonP_name:
                setup_task = self.collect_task(next_nonP_tasks[0], tag="setup")
                all_tasks.extend([task_cluster, [setup_task]]) if task_cluster else all_tasks.append([setup_task])
                task_cluster = []
            # TODO figure out a better way to separate test CV runs
            active_method = method if next_nonP_start != "solvent" else None
            # Create finish Firetasks if at end of measurements
            if "collect" in task.name and "collect" not in next_nonP_name:
                all_tasks.append(task_cluster) if task_cluster else None
                task_cluster = [self.collect_task(task, tag="finish")]
                active_method = None

        all_tasks.append(task_cluster) if task_cluster else None
        [print(f"FW {i + 1}:\t", [c.name for c in clus]) for i, clus in enumerate(all_tasks)]
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
            priority = self.priority - 1 if i == 0 else self.priority
            if "process" in fw_type:
                fw = CVProcessing(tasks, name="{}_{}".format(self.full_name, fw_type), parents=collect_parent or parent,
                                  fw_specs=self.fw_specs, mol_id=self.molecule_id, priority=priority - 1)
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
            "process_working_electrode_area": RecordWorkingElectrodeArea,  # needs: SIZE
            "rinse_electrode": RinseElectrode,  # needs: TIME
            "clean_electrode": CleanElectrode,
            "collect_cv_data": RunCV,
            "collect_ca_data": RunCA,
            "process_data": DataProcessor,
            "collect_cv_benchmark_data": BenchmarkCV,
            "process_cv_benchmarking": ProcessCVBenchmarking,

            "setup_cv": SetupCVPotentiostat,
            "setup_ca": SetupCAPotentiostat,
            "finish_cv": FinishPotentiostat,
            "finish_ca": FinishPotentiostat,

            "measure_working_electrode_area": RecordWorkingElectrodeArea,  # TODO Deprecated. Remove eventually
            "process_cv_data": DataProcessor,  # TODO Deprecated. Remove eventually
            "collect_electrode_test": RunCV,  # TODO Deprecated. Remove eventually
            "collect_electrode_test_data": RunCV,  # TODO Deprecated. Remove eventually
        }


if __name__ == "__main__":
    downloaded_wfls_dir = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "downloaded_wfs")
    # expflow_file = os.path.join(downloaded_wfls_dir, 'BasicCACVTest_workflow.json')
    expflow_file = os.path.join(downloaded_wfls_dir, 'TEST_ConcStudy_Cond1Cond3_5C_MACRO_workflow.json')
    expflow_exp = loadfn(expflow_file)
    experiment = EF2Experiment(expflow_exp.get("experiments")[0], "Robotics", data_type='cv')
    tc = experiment.task_clusters
