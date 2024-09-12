# Copyright 2024, University of Kentucky
import abc
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
    exit: bool
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

        if fw_spec.get("exit", self.get("exit", False)):
            print("EXITING WORKFLOW SEQUENCE")
            return False
        if get_exp_vial:
            self.exp_vial = VialMove(exp_name=self.exp_name, wflow_name=self.wflow_name)
            print(f"VIAL: {self.exp_vial}")
            
        return True

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
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        solvent = ReagentStatus(_id=self.get("start_uuid"))
        volume = self.get("volume", 0)
        if not volume and EXIT_ZERO_VOLUME:
            print(" \n \n!!!!!!!!! \n ATTENTION! This FW and all subsequent FWs will be exited. "
                  "DispenseLiquid task has volume 0 and EXIT_ZERO_VOLUME is set to True. \n !!!!!!!!! \n \n")
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        if solvent.type != "solvent":
            raise TypeError(f"DispenseLiquid task requires a solvent start_uuid. The start_uuid is type {solvent.type}")
        if solvent.location != "experiment_vial":
            solv_station = LiquidStation(_id=solvent.location, wflow_name=self.wflow_name)
            if WEIGH_SOLVENTS:
                solv_station.dispense_mass(self.exp_vial, volume)
            else:
                solv_station.dispense_volume(self.exp_vial, volume)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class DispenseSolid(RoboticsBase):
    # FireTask for dispensing solid

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        mass = self.get("mass")

        reagent = ReagentStatus(_id=self.get("start_uuid"))
        if reagent.location != "experiment_vial":
            pass  # TODO Dispense solid
        self.exp_vial.add_reagent(reagent, amount=mass, default_unit=MASS_UNIT)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class Heat(RoboticsBase):
    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        # temperature = self.get("temperature")
        # heat_time = self.get("time")

        self.metadata.update({"temperature": DEFAULT_TEMPERATURE})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class Stir(RoboticsBase):
    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        stir_time = self.get("time")

        if stir_time:
            stir_station = StirStation(StationStatus().get_first_available("stir"))
            self.success += stir_station.perform_stir(self.exp_vial, stir_time=stir_time)
        else:
            print(f"WARNING. HEAT_STIR action skipped because stir time was {stir_time}.")

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class MeasureDensity(RoboticsBase):
    # FireTask for measuring density

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        volume = self.get("volume", 0)
        volume = unit_conversion(volume, default_unit=VOLUME_UNIT)

        bal_station = BalanceStation(StationStatus().get_first_available("balance"))
        pipette_station = PipetteStation(StationStatus().get_first_available("pipette"))
        # Get initial mass
        initial_mass = bal_station.existing_weight(self.exp_vial)
        # Extract solution
        pipette_station.pipette(volume=volume, vial=self.exp_vial)
        # Get final mass
        final_mass = bal_station.weigh(self.exp_vial)

        # Discard pipetted solution
        pipette_station.pipette(volume=0)

        # Calculate solution density
        extracted_mass = initial_mass - final_mass
        raw_density = f"{extracted_mass / volume} {MASS_UNIT}/{VOLUME_UNIT}"
        soln_density = "{:.3f}{}".format(unit_conversion(raw_density, default_unit=DENSITY_UNIT), DENSITY_UNIT)
        print(f"Raw Density: {extracted_mass:.3f} / {volume:.3f} {MASS_UNIT}/{VOLUME_UNIT}")
        print("--> SOLUTION DENSITY: ", soln_density)
        self.metadata.update({"soln_density": soln_density})

        # Update vial contents
        self.exp_vial.extract_soln(extracted_mass=extracted_mass)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RecordWorkingElectrodeArea(RoboticsBase):
    # FireTask for recording size of working electrode

    def run_task(self, fw_spec):
        self.setup_task(fw_spec, get_exp_vial=False)
        self.metadata.update({"working_electrode_radius": DEFAULT_WORKING_ELECTRODE_RADIUS})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class SetupRinsePotentiostat(RoboticsBase):

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)

        potentiostat = PotentiostatStation(self.metadata.get(f"{self.metadata.get('active_method')}_potentiostat"))
        action_vial = VialMove(_id=RINSE_VIALS.get(potentiostat.id))

        # If potentiostat not available, return current vial home and fizzle.
        if not potentiostat.wait_till_available():
            warnings.warn(f"Station {potentiostat} not available. Fizzling rinse.")
            return self.self_fizzle()

        self.success += potentiostat.place_vial(action_vial)
        self.metadata.update({"active_vial_id": action_vial.id})

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RinseElectrode(RoboticsBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        rinse_time = unit_conversion(self.get("time", 0), default_unit='s')
        method = self.metadata.get("active_method")

        potentiostat = PotentiostatStation(self.metadata.get(f"{method}_potentiostat"))
        potentiostat.initiate_pot(vial=RINSE_VIALS.get(potentiostat.id))
        print(f"RINSING POTENTIOSTAT {potentiostat} FOR {rinse_time} SECONDS.")
        time.sleep(rinse_time)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class CleanElectrode(RoboticsBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        # time = self.get("time")
        return FWAction(update_spec=self.updated_specs())


@add_metaclass(abc.ABCMeta)
class SetupPotentiostat(RoboticsBase):
    method: str

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)
        self.method = self.method or self.metadata.get("active_method")

        # Move vial to potentiostat elevator
        if self.method in self.exp_vial.current_station.type:
            potentiostat = self.exp_vial.current_station.id
            if self.exp_name != PotentiostatStation(potentiostat).current_experiment:
                return self.self_fizzle()
        else:
            # Use the same potentiostat as previous actions in this experiment if applicable
            pot_type = f"{self.method}_potentiostat"
            if self.metadata.get(pot_type):
                potentiostat = PotentiostatStation(self.metadata.get(pot_type))
                print(f"This experiment already uses instrument {potentiostat}")
                self.success = potentiostat.wait_till_available()
                print("WAITING ", self.success)
            else:
                available_pot = StationStatus().get_first_available(pot_type)
                potentiostat = PotentiostatStation(available_pot) if available_pot else None
            print("SUCCESS, POTENT: ", self.success, potentiostat)
            # If potentiostat not available, return current vial home and fizzle.
            if not (self.success and potentiostat):
                warnings.warn(f"Station {potentiostat} not available. Moving vial {self.exp_vial} back home.")
                self.exp_vial.place_home()
                return self.self_fizzle()
            potentiostat.update_experiment(self.exp_name)
            self.success += potentiostat.place_vial(self.exp_vial)
        print("POTENTIOSTAT: ", potentiostat)

        # Setup metadata
        cycle = self.metadata.get("cycle", 0)
        self.metadata.update({"collect_tag": f"cycle{cycle + 1:02d}_{self.method}", "cycle": cycle + 1,
                              f"{self.method}_idx": self.metadata.get(f"{self.method}_idx", 1),
                              f"{self.method}_potentiostat": potentiostat, "active_vial_id": self.exp_vial.id,
                              "active_method": self.method})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class SetupCVPotentiostat(SetupPotentiostat):
    method = "cv"


@explicit_serialize
class SetupCAPotentiostat(SetupPotentiostat):
    method = "ca"


@explicit_serialize
class FinishPotentiostat(RoboticsBase):
    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)

        method = self.metadata.get("active_method")
        potentiostat = PotentiostatStation(self.metadata.get(f"{method}_potentiostat"))
        vial_id = self.metadata.get("active_vial_id") or potentiostat.current_content

        if vial_id:
            # Get vial
            active_vial = VialMove(_id=vial_id)
            if active_vial.current_location == potentiostat.id:
                print(f"COLLECTING VIAL {active_vial} FROM {potentiostat}")
                self.success += active_vial.retrieve()
            else:
                print(f"Active vial {active_vial} has already been collected from {potentiostat}")

        if self.end_experiment:
            potentiostat.update_experiment(None)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class BenchmarkCV(RoboticsBase):
    # FireTask for testing electrode cleanliness

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)

        # CV parameters and keywords
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        sample_interval = fw_spec.get("sample_interval") or self.get("sample_interval", "")
        sens = fw_spec.get("sens") or self.get("sens", "")

        # Prep output file info
        active_vial_id = self.metadata.get("active_vial_id")
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"benchmark_%H_%M_%S.txt"))

        # Run CV experiment
        potent = CVPotentiostatStation(self.metadata.get("cv_potentiostat"))
        potent.initiate_pot(vial=self.metadata.get("active_vial_id"))
        resistance = potent.run_ircomp_test(data_path=data_path.replace("benchmark_", "iRComp_")) if IR_COMP else 0
        self.success += potent.run_cv(data_path=data_path, voltage_sequence=voltage_sequence, scan_rate=scan_rate,
                                      resistance=resistance, sample_interval=sample_interval, sens=sens)
        # [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        self.collection_data.append({"collect_tag": "benchmark_cv",
                                     "vial_contents": VialStatus(active_vial_id).vial_content,
                                     "data_location": data_path})
        self.metadata.update({"resistance": resistance})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RunCV(RoboticsBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)

        # CV parameters and keywords
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        resistance = self.metadata.get("resistance", 0)
        sample_interval = fw_spec.get("sample_interval") or self.get("sample_interval", "")
        sens = fw_spec.get("sensitivity") or self.get("sensitivity", "")

        # Prep output data file info
        collect_tag = self.metadata.get("collect_tag")
        active_vial_id = self.metadata.get("active_vial_id")
        cv_idx = self.metadata.get("cv_idx", 1)
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"{collect_tag}{cv_idx:02d}_%H_%M_%S.txt"))

        # Run CV experiment
        potent = CVPotentiostatStation(self.metadata.get("cv_potentiostat"))
        potent.initiate_pot(vial=self.metadata.get("active_vial_id"))
        self.success += potent.run_cv(data_path=data_path, voltage_sequence=voltage_sequence, scan_rate=scan_rate,
                                      resistance=resistance, sample_interval=sample_interval, sens=sens)
        # [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        self.metadata.update({"cv_idx": cv_idx + 1})
        self.collection_data.append({"collect_tag": collect_tag,
                                     "vial_contents": VialStatus(active_vial_id).vial_content,
                                     "data_location": data_path})
        return FWAction(update_spec=self.updated_specs(voltage_sequence=voltage_sequence))  # TODO figure out if we want to propogate voltage sequence


@explicit_serialize
class RunCA(RoboticsBase):
    # FireTask for running CA

    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)

        # CA parameters and keywords
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        sample_interval = fw_spec.get("sample_interval") or self.get("sample_interval", "")
        pulse_width = fw_spec.get("pulse_width") or self.get("pulse_width", "")
        sens = fw_spec.get("sens") or self.get("sens", "")
        steps = fw_spec.get("steps") or self.get("steps", "")

        # Prep output data file info
        collect_tag = self.metadata.get("collect_tag")
        active_vial_id = self.metadata.get("active_vial_id")
        ca_idx = self.metadata.get("ca_idx", 1)
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"{collect_tag}{ca_idx:02d}_%H_%M_%S.txt"))

        # Run CA experiment
        potent = CAPotentiostatStation(self.metadata.get("ca_potentiostat"))
        potent.initiate_pot(vial=self.metadata.get("active_vial_id"))
        self.success += potent.run_ca(data_path=data_path, voltage_sequence=voltage_sequence, si=sample_interval,
                                      pw=pulse_width, sens=sens, steps=steps)
        # [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        temperature = potent.get_temperature() or self.metadata.get("temperature")
        print("RECORDED TEMPERATURE: ", temperature)

        self.metadata.update({"ca_idx": ca_idx + 1, "temperature": temperature})
        self.collection_data.append({"collect_tag": collect_tag,
                                     "vial_contents": VialStatus(active_vial_id).vial_content,
                                     "temperature": temperature,
                                     "data_location": data_path})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class CollectTemp(RoboticsBase):
    def run_task(self, fw_spec):
        if not self.setup_task(fw_spec):
            return FWAction(update_spec=self.updated_specs(exit=True), exit=True)

        # Collect temperature
        potent = CAPotentiostatStation(self.metadata.get("ca_potentiostat"))
        temperature = potent.get_temperature() or self.metadata.get("temperature")
        print("RECORDED TEMPERATURE: ", temperature)

        self.metadata.update({"temperature": temperature})
        return FWAction(update_spec=self.updated_specs())