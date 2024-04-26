# Copyright 2024, University of Kentucky
import abc
import time
import warnings

from six import add_metaclass
from fireworks import LaunchPad
from fireworks import FiretaskBase, explicit_serialize, FWAction
from robotics_api.actions.standard_actions import *
from robotics_api.actions.db_manipulations import *


@add_metaclass(abc.ABCMeta)
class RoboticsBase(FiretaskBase):
    wflow_name: str
    exp_name: str
    full_name: str
    success: bool
    lpad: LaunchPad
    metadata: dict
    collection_data: list
    processing_data: dict
    exp_vial: VialMove
    end_experiment: bool
    _fw_name = "RoboticsBase"

    def setup_task(self, fw_spec, get_exp_vial=True):
        self.wflow_name = fw_spec.get("wflow_name", self.get("wflow_name"))
        self.exp_name = fw_spec.get("exp_name", self.get("exp_name"))
        self.full_name = fw_spec.get("full_name", self.get("full_name"))
        self.end_experiment = fw_spec.get("end_experiment", self.get("end_experiment", False))
        print(f"WORKFLOW: {self.wflow_name}")
        print(f"EXPERIMENT: {self.exp_name}")

        self.success = True
        self.lpad = LaunchPad().from_file(LAUNCHPAD)
        self.metadata = fw_spec.get("metadata", {})
        self.collection_data = fw_spec.get("collection_data", [])
        self.processing_data = fw_spec.get("processing_data", {})

        if get_exp_vial:
            self.exp_vial = VialMove(exp_name=self.exp_name, wflow_name=self.wflow_name)
            print(f"VIAL: {self.exp_vial}")

    def updated_specs(self, **kwargs):
        # When updating specs, check for fizzled robot jobs and rerun
        if RERUN_FIZZLED_ROBOT:
            fizzled_fws = self.lpad.fireworks.find({"state": "FIZZLED", "$or": [
                {"name": {"$regex": "_setup_"}},
                {"name": {"$regex": "robot"}}
            ]}).distinct("fw_id")
            [self.lpad.rerun_fw(fw) for fw in fizzled_fws]
            print(f"Fireworks {str(fizzled_fws)} released from fizzled state.")

        # Update main spec categories: success, metadata, collection_data, and processing_data
        specs = {"success": self.success, "metadata": self.metadata, "collection_data": self.collection_data,
                 "processing_data": self.processing_data}
        specs.update(dict(**kwargs))
        return specs

    def self_fizzle(self):
        self.updated_specs()
        raise Exception(f"Self defusing Firetask {self._fw_name}")


@explicit_serialize
class DispenseLiquid(RoboticsBase):
    # FireTask for dispensing liquid

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        volume = self.get("volume")
        solvent = ReagentStatus(_id=self.get("start_uuid"))
        if solvent.type != "solvent":
            raise TypeError(f"DispenseLiquid task requires a solvent start_uuid. The start_uuid is type {solvent.type}")
        if solvent.location != "experiment_vial":
            solv_station = LiquidStation(_id=solvent.location, wflow_name=self.wflow_name)

            # Uncap vial if capped
            self.success += self.exp_vial.retrieve()
            self.success += self.exp_vial.uncap(raise_error=CAPPED_ERROR)

            volume = solv_station.dispense(self.exp_vial, volume)
        self.exp_vial.add_reagent(solvent, amount=volume, default_unit=VOLUME_UNIT)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class DispenseSolid(RoboticsBase):
    # FireTask for dispensing solid

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        mass = self.get("mass")

        reagent = ReagentStatus(_id=self.get("start_uuid"))
        if reagent.location != "experiment_vial":
            pass  # TODO Dispense solid
        self.exp_vial.add_reagent(reagent, amount=mass, default_unit=MASS_UNIT)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RecordWorkingElectrodeArea(RoboticsBase):
    # FireTask for recording size of working electrode

    def run_task(self, fw_spec):
        self.setup_task(fw_spec, get_exp_vial=False)
        # working_electrode_area = self.get("size", DEFAULT_WORKING_ELECTRODE_AREA)
        # working_electrode_radius = self.get("size", DEFAULT_WORKING_ELECTRODE_RADIUS)
        self.metadata.update({"working_electrode_surface_area": DEFAULT_WORKING_ELECTRODE_AREA,
                              "working_electrode_radius": DEFAULT_WORKING_ELECTRODE_RADIUS})
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
        stir_station = StirHeatStation(StationStatus().get_first_available("stir-heat"))
        self.success += stir_station.perform_stir_heat(self.exp_vial, stir_time=stir_time, temperature=temperature)

        self.metadata.update({"temperature": DEFAULT_TEMPERATURE})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RinseElectrode(RoboticsBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        rinse_time = unit_conversion(self.get("time", 0), default_unit='s')
        method = self.metadata.get("active_method")

        potentiostat = PotentiostatStation(self.metadata.get(f"{method}_potentiostat"))
        potentiostat.initiate_pot()
        print(f"RINSING POTENTIOSTAT {potentiostat} FOR {rinse_time} SECONDS.")
        time.sleep(rinse_time)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class CleanElectrode(RoboticsBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        # time = self.get("time")
        return FWAction(update_spec=self.updated_specs())


@add_metaclass(abc.ABCMeta)
class SetupPotentiostat(RoboticsBase):
    method: str

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        self.method = self.method or self.metadata.get("active_method")

        # Get vial for CV
        start_reagent = ReagentStatus(_id=self.get("start_uuid"))
        if start_reagent.type == "solvent":
            solvent = LiquidStation(start_reagent.location)
            collect_vial = VialMove(_id=solvent.blank_vial)
            self.metadata.update({"collect_tag": f"solv_{self.method}"})
        else:
            collect_vial = self.exp_vial
            cycle = self.metadata.get("cv_cycle", 0)
            self.metadata.update({"collect_tag": f"cycle{cycle+1:02d}_{self.method}", "cv_cycle": cycle+1,
                                  "cv_idx": 1, "ca_idx": 1})

        # Uncap vial if capped
        self.success += collect_vial.uncap(raise_error=CAPPED_ERROR)

        # Move vial to potentiostat elevator
        if self.method in collect_vial.current_station.type:
            potentiostat = collect_vial.current_station.id
            if self.exp_name != PotentiostatStation(potentiostat).current_experiment:
                return self.self_fizzle()
        else:
            # Use the same potentiostat as previous actions in this experiment if applicable
            pot_type = f"{self.method}_potentiostat"
            if self.metadata.get(pot_type):
                potentiostat = PotentiostatStation(self.metadata.get(pot_type))
                self.success += potentiostat.wait_till_available()
            else:
                available_pot = StationStatus().get_first_available(pot_type)
                potentiostat = PotentiostatStation(available_pot) if available_pot else None
            # If potentiostat not available, return current vial home and fizzle.
            if not (self.success and potentiostat):
                warnings.warn(f"Station {potentiostat} not available. Moving vial {collect_vial} back home.")
                collect_vial.place_home()
                self.updated_specs()
                return self.self_fizzle()
            potentiostat.update_experiment(self.exp_name)
            self.success += collect_vial.place_station(potentiostat)
        print("POTENTIOSTAT: ", potentiostat)
        self.metadata.update({f"{self.method}_potentiostat": potentiostat, "collect_vial_id": collect_vial.id,
                              "active_method": self.method})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class SetupActivePotentiostat(SetupPotentiostat):
    method = None


@explicit_serialize
class SetupCVPotentiostat(SetupPotentiostat):
    method = "cv"


@explicit_serialize
class SetupCAPotentiostat(SetupPotentiostat):
    method = "ca"


@explicit_serialize
class FinishPotentiostat(RoboticsBase):
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        method = self.metadata.get("active_method")
        potentiostat = PotentiostatStation(self.metadata.get(f"{method}_potentiostat"))
        vial_id = self.metadata.get("collect_vial_id") or potentiostat.current_content

        if vial_id:
            # Get vial
            collect_vial = VialMove(_id=vial_id)
            print("STARTING HOME PLACEMENT")
            self.success += collect_vial.place_home()
            print("ENDING HOME PLACEMENT")

        if self.end_experiment:
            potentiostat.update_experiment(None)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class BenchmarkCV(RoboticsBase):
    # FireTask for testing electrode cleanliness

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CV parameters and keywords
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")

        # Prep output file info
        collect_vial_id = self.metadata.get("collect_vial_id")
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"benchmark_%H_%M_%S.txt"))

        # Run CV experiment
        potent = CVPotentiostatStation(self.metadata.get("cv_potentiostat"))
        potent.initiate_pot()
        resistance = potent.run_ircomp_test(data_path=data_path.replace("benchmark_", "iRComp_")) if IR_COMP else 0
        self.success += potent.run_cv(data_path=data_path, voltage_sequence=voltage_sequence, scan_rate=scan_rate,
                                      resistance=resistance)
        [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        self.collection_data.append({"collect_tag": "benchmark_cv",
                                     "vial_contents": VialStatus(collect_vial_id).vial_content,
                                     "data_location": data_path})
        self.metadata.update({"resistance": resistance})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RunCV(RoboticsBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CV parameters and keywords
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        resistance = self.metadata.get("resistance", 0)

        # Prep output data file info
        collect_tag = self.metadata.get("collect_tag")
        collect_vial_id = self.metadata.get("collect_vial_id")
        cv_idx = self.metadata.get("cv_idx", 1)
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"{collect_tag}{cv_idx:02d}_%H_%M_%S.txt"))

        # Run CV experiment
        potent = CVPotentiostatStation(self.metadata.get("cv_potentiostat"))
        potent.initiate_pot()
        self.success += potent.run_cv(data_path=data_path, voltage_sequence=voltage_sequence, scan_rate=scan_rate,
                                      resistance=resistance)
        [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        self.metadata.update({"cv_idx": cv_idx + 1})
        self.collection_data.append({"collect_tag": collect_tag,
                                     "vial_contents": VialStatus(collect_vial_id).vial_content,
                                     "data_location": data_path})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RunCA(RoboticsBase):
    # FireTask for running CA

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CA parameters and keywords
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")

        # Prep output data file info
        collect_tag = self.metadata.get("collect_tag")
        collect_vial_id = self.metadata.get("collect_vial_id")
        ca_idx = self.metadata.get("ca_idx", 1)
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"{collect_tag}{ca_idx:02d}_%H_%M_%S.txt"))

        # Run CA experiment
        potent = CAPotentiostatStation(self.metadata.get("ca_potentiostat"))
        potent.initiate_pot()
        self.success += potent.run_ca(data_path=data_path, voltage_sequence=voltage_sequence)
        [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        temperature = potent.get_temperature() or self.metadata.get("temperature")
        print("RECORDED TEMPERATURE: ", temperature)

        self.metadata.update({"ca_idx": ca_idx + 1, "temperature": temperature})
        self.collection_data.append({"collect_tag": collect_tag,
                                     "vial_contents": VialStatus(collect_vial_id).vial_content,
                                     "temperature": temperature,
                                     "data_location": data_path})
        return FWAction(update_spec=self.updated_specs())
