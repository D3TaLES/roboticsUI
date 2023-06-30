# Copyright 2022, University of Kentucky
import abc
from six import add_metaclass
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
        self.metadata = fw_spec.get("metadata", {})
        self.location_data = fw_spec.get("location_data", {})

        self.exp_vial = VialMove(exp_name=self.exp_name, wflow_name=self.wflow_name)
        print(f"VIAL: {self.exp_vial}")

    def updated_specs(self):
        return {"success": self.success, "metadata": self.metadata, "location_data": self.location_data}


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
            self.success += self.exp_vial.place_station(solv_station)
            self.success += solv_station.dispense(volume)

        # TODO calculate concentration
        self.metadata.update({"redox_mol_concentration": DEFAULT_CONCENTRATION})

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
        temperature = self.get("temperature")
        stir_time = self.get("time")

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
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # time = self.get("time")
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class CleanElectrode(RoboticsBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # time = self.get("time")
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class SetupPotentiostat(RoboticsBase):
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # Get vial for CV
        start_reagent = ReagentStatus(_id=self.get("start_uuid"))
        if start_reagent.type == "solvent":
            solvent = SolventStation(start_reagent.location)
            cv_vial = VialMove(_id=solvent.blank_vial)
            self.metadata.update({"cv_tag": f"solv_{start_reagent.name.replace(' ', '_')}"})
        else:
            cv_vial = self.exp_vial

        # Uncap vial if capped
        self.success += cv_vial.uncap(raise_error=CAPPED_ERROR)

        # Move vial to potentiostat elevator
        potentiostat = StationStatus().get_first_available("potentiostat")
        print("POTENTIOSTAT: ", potentiostat)
        self.success += cv_vial.place_station(PotentiostatStation(potentiostat))

        self.metadata.update({"potentiostat": potentiostat, "cv_vial": cv_vial.id})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class FinishPotentiostat(RoboticsBase):
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        potentiostat = PotentiostatStation(self.metadata.get("potentiostat"))
        vial_id = self.metadata.get("cv_vial") or potentiostat.current_content

        if vial_id:
            # Get vial
            cv_vial = VialMove(_id=vial_id)
            # self.success += cv_vial.retrieve(raise_error=True)
            # self.success += cv_vial.cap(raise_error=CAPPED_ERROR)
            print("STARTING HOME PLACEMENT")
            self.success += cv_vial.place_home()
            print("ENDING HOME PLACEMENT")

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class BenchmarkCV(RoboticsBase):
    # FireTask for testing electrode cleanliness

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        self.location_data.update({"benchmark_locations": []})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RunCV(RoboticsBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CV parameters and keywords
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        collect_params = generate_col_params(voltage_sequence, scan_rate)

        # Prep output file info
        cv_idx = self.metadata.get("cv_idx", 1)
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        cv_tag = self.metadata.get("cv_tag")
        data_path = os.path.join(data_dir,
                                 time.strftime("{}_%H_%M_%S.csv".format(cv_tag or "exp{:02d}".format(cv_idx))))

        # Run CV experiment
        print("RUN CV WITH COLLECTION PARAMS: ", collect_params)
        potentiostat = PotentiostatStation(self.metadata.get("potentiostat"))  # TODO setup multi potentiostats
        potentiostat.initiate_cv()
        if RUN_CV:
            expt = CvExperiment([voltage_step(**p) for p in collect_params], load_firm=True)
            expt.run_experiment()
            time.sleep(TIME_AFTER_CV)
            expt.to_txt(data_path)

        locations_name = "{}_locations".format(cv_tag.split("_")[0] if cv_tag else "cv")
        locations = self.location_data.get(locations_name, [])
        locations.append(data_path)

        self.metadata.update({"cv_tag": ""} if cv_tag else {"cv_idx": cv_idx + 1})
        self.location_data.update({locations_name: locations})
        return FWAction(update_spec=self.updated_specs())
