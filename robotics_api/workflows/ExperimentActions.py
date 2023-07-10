# Copyright 2022, University of Kentucky
import abc
from six import add_metaclass
from fireworks import LaunchPad
from fireworks import FiretaskBase, explicit_serialize, FWAction
from robotics_api.workflows.actions.cv_techniques import *
from robotics_api.workflows.actions.standard_actions import *
from robotics_api.workflows.actions.status_db_manipulations import *


@add_metaclass(abc.ABCMeta)
class RoboticsBase(FiretaskBase):
    _fw_name = "RoboticsBase"

    def setup_task(self, fw_spec):
        self.wflow_name = fw_spec.get("wflow_name", self.get("wflow_name"))
        self.exp_name = fw_spec.get("exp_name", self.get("exp_name"))
        self.full_name = fw_spec.get("full_name", self.get("full_name"))
        print(f"WORKFLOW: {self.wflow_name}")
        print(f"EXPERIMENT: {self.exp_name}")

        self.success = True
        self.lpad = LaunchPad().from_file(LAUNCHPAD)
        self.metadata = fw_spec.get("metadata", {})
        self.collection_data = fw_spec.get("collection_data", [])
        self.processing_data = fw_spec.get("processing_data", {})

        self.exp_vial = VialMove(exp_name=self.exp_name, wflow_name=self.wflow_name)
        print(f"VIAL: {self.exp_vial}")

    def updated_specs(self, **kwargs):
        # When updating specs, check for open potentiostat
        if StationStatus().get_all_available("potentiostat"):
            defused_fws = self.lpad.fireworks.find({"state": "DEFUSED", "name": {"$regex": "_setup_"}}).distinct("fw_id")
            [self.lpad.reignite_fw(fw) for fw in defused_fws]
        # Update main spec categories: success, metadata, collection_data, and processing_data
        specs = {"success": self.success, "metadata": self.metadata, "collection_data": self.collection_data,
                 "processing_data": self.processing_data}
        specs.update(dict(**kwargs))
        return specs


@explicit_serialize
class EndWorkflow(FiretaskBase):
    # FireTask for ending a workflow
    def run_task(self, fw_spec):
        success = snapshot_move(SNAPSHOT_END_HOME)
        return FWAction(update_spec={"success": success})


@explicit_serialize
class DispenseLiquid(RoboticsBase):
    # FireTask for dispensing liquid

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        volume = self.get("volume")
        solvent = ReagentStatus(_id=self.get("start_uuid"))
        if solvent.type != "solvent":
            solvent = ReagentStatus(_id=fw_spec.get("solv_id"))
        solv_station = SolventStation(_id=solvent.location, wflow_name=self.wflow_name)

        # Uncap vial if capped
        self.success += self.exp_vial.retrieve()
        self.success += self.exp_vial.uncap(raise_error=CAPPED_ERROR)

        if solvent.location == "experiment_vial":
            self.exp_vial.add_reagent(solvent, amount=volume, default_unit=VOLUME_UNIT)
        else:
            # self.success += self.exp_vial.place_station(solv_station) TODO setup liquid dispensing
            actual_volume = solv_station.dispense(volume)
            self.exp_vial.add_reagent(solvent, amount=actual_volume, default_unit=VOLUME_UNIT)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class DispenseSolid(RoboticsBase):
    # FireTask for dispensing solid

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        mass = self.get("mass")
        reagent = ReagentStatus(_id=self.get("start_uuid"))
        if reagent.location == "experiment_vial":
            self.exp_vial.add_reagent(reagent, amount=mass, default_unit=MASS_UNIT)
        else:
            pass  # TODO Dispense solid

        self.metadata.update({"mass": mass})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RecordWorkingElectrodeArea(RoboticsBase):
    # FireTask for recording size of working electrode

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        # working_electrode_area = self.get("size", DEFAULT_WORKING_ELECTRODE_AREA)
        working_electrode_area = DEFAULT_WORKING_ELECTRODE_AREA
        self.metadata.update({"working_electrode_surface_area": working_electrode_area})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class Heat(RoboticsBase):
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        temperature = self.get("temperature")
        heat_time = self.get("time")
        self.success += self.exp_vial.cap(raise_error=CAPPED_ERROR)

        stir_station = StationStatus().get_first_available("stir-heat")
        self.success += stir_station.perform_stir_heat(self.exp_vial, temperature=temperature, heat_time=heat_time)

        self.metadata.update({"temperature": DEFAULT_TEMPERATURE})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class HeatStir(RoboticsBase):
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        # temperature = self.get("temperature")
        # stir_time = self.get("time")

        self.success += self.exp_vial.cap(raise_error=CAPPED_ERROR)

        # TODO fix stirring
        # stir_station = StirHeatStation(StationStatus().get_first_available("stir-heat"))
        # self.success += stir_station.perform_stir_heat(self.exp_vial, stir_time=stir_time, temperature=temperature)

        self.metadata.update({"temperature": DEFAULT_TEMPERATURE})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RinseElectrode(RoboticsBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        # time = self.get("time")
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class CleanElectrode(RoboticsBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        # time = self.get("time")
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class SetupPotentiostat(RoboticsBase):
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # Pause all other setup fireworks
        setup_fws = self.lpad.fireworks.find({"state": {"$in": ["READY", "WAITING"]},
                                              "name": {"$regex": "_setup_"}}).distinct("fw_id")
        [self.lpad.defuse_fw(fw) for fw in setup_fws]

        # Get vial for CV
        start_reagent = ReagentStatus(_id=self.get("start_uuid"))
        if start_reagent.type == "solvent":
            solvent = SolventStation(start_reagent.location)
            collect_vial = VialMove(_id=solvent.blank_vial)
            self.metadata.update({"collect_tag": "solv_cv"})
        else:
            collect_vial = self.exp_vial
            cycle = self.metadata.get("cv_cycle", 0)
            self.metadata.update({"collect_tag": f"Cycle{cycle+1:02d}_cv", "cv_cycle": cycle+1, "cv_idx": 1})

        # Uncap vial if capped
        self.success += collect_vial.uncap(raise_error=CAPPED_ERROR)

        # Move vial to potentiostat elevator
        if collect_vial.current_station.type == "potentiostat":
            potentiostat = collect_vial.current_station.id
        else:
            # Use the same potentiostat as previous actions in this experiment if applicable
            if self.metadata.get("potentiostat"):
                potentiostat = PotentiostatStation(self.metadata.get("potentiostat"))
                self.success += potentiostat.wait_till_available(max_time=MAX_WAIT_TIME)
            else:
                potentiostat = StationStatus().get_first_available("potentiostat")
            self.success += collect_vial.place_station(PotentiostatStation(potentiostat))
        print("POTENTIOSTAT: ", potentiostat)

        self.metadata.update({"potentiostat": potentiostat, "collect_vial_id": collect_vial.id})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class FinishPotentiostat(RoboticsBase):
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        potentiostat = PotentiostatStation(self.metadata.get("potentiostat"))
        vial_id = self.metadata.get("collect_vial_id") or potentiostat.current_content

        if vial_id:
            # Get vial
            collect_vial = VialMove(_id=vial_id)
            # self.success += collect_vial.retrieve(raise_error=True)
            # self.success += collect_vial.cap(raise_error=CAPPED_ERROR)
            print("STARTING HOME PLACEMENT")
            self.success += collect_vial.place_home()
            print("ENDING HOME PLACEMENT")

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class BenchmarkCV(RoboticsBase):
    # FireTask for testing electrode cleanliness

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CV parameters and keywords
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        collect_params = generate_col_params(voltage_sequence, scan_rate)

        # Prep output file info
        collect_vial_id = self.metadata.get("collect_vial_id")
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"benchmark_%H_%M_%S.csv"))

        # Run CV experiment
        print("RUN CV WITH COLLECTION PARAMS: ", collect_params)
        potent = PotentiostatStation(self.metadata.get("potentiostat"))
        potent.initiate_cv()
        ir_comp = None
        if RUN_CV:
            # Benchmark CV for voltage range
            expt = CvExperiment([voltage_step(**p) for p in collect_params], load_firm=True,
                                potentiostat_address=potent.p_address, potentiostat_channel=potent.p_channel)
            expt.run_experiment()
            time.sleep(TIME_AFTER_CV)
            expt.to_txt(data_path)

            # iR compensation
            # TODO iR compensation
            ir_comp = 0

        self.collection_data.append({"collect_tag": "benchmark_cv",
                                     "vial_contents": VialStatus(collect_vial_id).vial_content,
                                     "data_location": data_path})
        return FWAction(update_spec=self.updated_specs(ir_comp=ir_comp))


@explicit_serialize
class RunCV(RoboticsBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CV parameters and keywords
        ir_comp = fw_spec.get("ir_comp") or self.get("ir_comp", "")
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        collect_params = generate_col_params(voltage_sequence, scan_rate)

        # Prep output file info
        collect_tag = self.metadata.get("collect_tag")
        collect_vial_id = self.metadata.get("collect_vial_id")
        cv_idx = self.metadata.get("cv_idx", 1)
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        file_tag = f"cv{cv_idx:02d}" if collect_tag.startswith("Cycle") else collect_tag
        data_path = os.path.join(data_dir, time.strftime(f"{file_tag}_%H_%M_%S.csv"))

        # Run CV experiment
        print("RUN CV WITH COLLECTION PARAMS: ", collect_params)
        potent = PotentiostatStation(self.metadata.get("potentiostat"))
        potent.initiate_cv()
        if RUN_CV:
            expt = CvExperiment([voltage_step(**p) for p in collect_params], load_firm=True,
                                potentiostat_address=potent.p_address, potentiostat_channel=potent.p_channel)
            expt.run_experiment()
            time.sleep(TIME_AFTER_CV)
            expt.to_txt(data_path)

        self.metadata.update({"cv_idx": cv_idx + 1})
        self.collection_data.append({"collect_tag": collect_tag,
                                     "vial_contents": VialStatus(collect_vial_id).vial_content,
                                     "data_location": data_path})
        return FWAction(update_spec=self.updated_specs())
