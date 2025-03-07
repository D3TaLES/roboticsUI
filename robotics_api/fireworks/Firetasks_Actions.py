# Copyright 2024, University of Kentucky
import abc
from datetime import datetime
from six import add_metaclass
from fireworks import LaunchPad
from fireworks import FiretaskBase, explicit_serialize, FWAction
from robotics_api.actions.standard_actions import *
from robotics_api.actions.db_manipulations import *
from robotics_api.utils.processing_utils import DefaultConditions


@add_metaclass(abc.ABCMeta)
class RoboticsBase(FiretaskBase):
    """Base class for robotics-related FireTasks.

    Attributes:
        wflow_name (str): Name of the workflow.
        exp_name (str): Name of the experiment.
        full_name (str): Full name combining workflow and experiment.
        success (bool): Flag indicating task success.
        lpad (LaunchPad): LaunchPad instance for fireworks operations.
        metadata (dict): Dictionary to hold task metadata.
        collection_data (list): List of data collected during the experiment.
        processing_data (dict): Dictionary of data related to processing.
        exp_vial (VialMove): Instance representing a vial in the experiment.
        end_experiment (bool): Flag indicating whether the experiment is ending.
    """

    _fw_name = "RoboticsBase"
    success = False

    def setup_task(self, fw_spec, get_exp_vial=True):
        """Sets up the task with the provided fireworks spec.

        Args:
            fw_spec (dict): Firework spec containing task setup information.
            get_exp_vial (bool): Whether to initialize the experiment vial.

        Returns:
            bool: False if exiting the workflow, True otherwise.
        """
        self.wflow_name = ""
        self.exp_name = ""
        self.full_name = ""
        self.end_experiment = False
        self.metadata = {}
        self.collection_data = []
        self.processing_data = {}
        self.exp_vial = None
        self.success = True

        self.lpad = LaunchPad().from_file(os.path.abspath(LAUNCHPAD))
        self.wflow_name = fw_spec.get("wflow_name", self.get("wflow_name"))
        self.exp_name = fw_spec.get("exp_name", self.get("exp_name"))
        self.full_name = fw_spec.get("full_name", self.get("full_name"))
        self.end_experiment = fw_spec.get("end_experiment", self.get("end_experiment", False))
        self.ftask_id = self.get("firetask_id")
        print(f"WORKFLOW: {self.wflow_name}")
        print(f"EXPERIMENT: {self.exp_name}")

        self.metadata = fw_spec.get("metadata", {})
        self.collection_data = fw_spec.get("collection_data", [])
        self.processing_data = fw_spec.get("processing_data", {})

        if get_exp_vial:
            self.exp_vial = VialMove(exp_name=self.exp_name, wflow_name=self.wflow_name)
            print(f"VIAL: {self.exp_vial}")

    def rerun_fizzed_robot(self):
        """
        When updating specs, check for fizzled robot jobs and rerun
        """
        if RERUN_FIZZLED_ROBOT:
            fizzled_fws = self.lpad.fireworks.find({"state": "FIZZLED", "$or": [
                {"name": {"$regex": "_setup_"}},
                {"name": {"$regex": "robot"}}
            ]}).distinct("fw_id")
            [self.lpad.rerun_fw(fw) for fw in fizzled_fws]
            print(f"Fireworks {str(fizzled_fws)} released from fizzled state.")

    def updated_specs(self, **kwargs):
        """Updates the fireworks spec with current task data.

        Args:
            **kwargs: Additional specifications to be updated.

        Returns:
            dict: Updated specifications dictionary.
        """

        # Update main spec categories: success, metadata, collection_data, and processing_data
        specs = {"success": self.success, "metadata": self.metadata, "collection_data": self.collection_data,
                 "processing_data": self.processing_data}
        specs.update(dict(**kwargs))
        return specs

    def self_fizzle(self):
        """Raises an exception to stop the task and mark it as failed."""
        self.updated_specs()
        raise Exception(f"Self defusing Firetask {self._fw_name}")


@explicit_serialize
class DispenseLiquid(RoboticsBase):
    """FireTask for dispensing liquid into an experiment vial."""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        solvent = ReagentStatus(_id=self.get("start_uuid"))
        volume = self.get("volume", 0)
        if solvent.type != "solvent":
            raise TypeError(f"DispenseLiquid task requires a solvent start_uuid. The start_uuid is type {solvent.type}")

        if self.exp_vial.check_addition_id(self.ftask_id):  # Check if addition has already been made
            if solvent.location == "experiment_vial":
                self.exp_vial.add_reagent(solvent, amount=volume, default_unit=VOLUME_UNIT, addition_id=self.ftask_id)
            else:
                solv_station = LiquidStation(_id=solvent.location, wflow_name=self.wflow_name)
                if WEIGH_SOLVENTS:
                    solv_station.dispense_mass(self.exp_vial, volume, addition_id=self.ftask_id)
                else:
                    solv_station.dispense_volume(self.exp_vial, volume, addition_id=self.ftask_id)
        else:
            warnings.warn(f"ADDITION NOT MADE! Addition of {volume} of {solvent.name} to vial {self} not added to "
                          f"the vial because addition id {self.ftask_id} already exists in content history ")

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class DispenseSolid(RoboticsBase):
    """FireTask for dispensing solid into an experiment vial."""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        mass = self.get("mass")
        reagent = ReagentStatus(_id=self.get("start_uuid"))

        if self.exp_vial.check_addition_id(self.ftask_id):  # Check if addition has already been made
            if reagent.location != "experiment_vial":
                pass  # TODO Dispense solid
            self.exp_vial.add_reagent(reagent, amount=mass, default_unit=MASS_UNIT, addition_id=self.ftask_id)
        else:
            warnings.warn(f"ADDITION NOT MADE! Addition of {mass} of {reagent.name} to vial {self} not added to "
                          f"the vial because addition id {self.ftask_id} already exists in content history ")
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class Heat(RoboticsBase):
    """FireTask for heating an experiment vial."""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        # temperature = self.get("temperature")
        # heat_time = self.get("time")

        self.metadata.update({"temperature": DEFAULT_TEMPERATURE})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class Stir(RoboticsBase):
    """FireTask for holding an experiment vial over the stir plate and stirring."""
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        stir_time = self.get("time")

        if stir_time:
            stir_station = StirStation(StationStatus().get_first_available("stir"))
            self.success &= stir_station.stir_vial(self.exp_vial, stir_time=stir_time)
        else:
            print(f"WARNING. HEAT_STIR action skipped because stir time was {stir_time}.")

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class CollectTemp(RoboticsBase):
    """Firetask for collecting temperature. IN DEVELOPMENT!!!"""
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # Collect temperature
        temperature = TemperatureStation().temperature()
        print("RECORDED TEMPERATURE: ", temperature)

        self.metadata.update({"temperature": temperature})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class MeasureDensity(RoboticsBase):
    """FireTask for measuring solution density"""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
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

        # Calculate solution density
        extracted_mass = initial_mass - final_mass
        raw_density = f"{extracted_mass / volume} {MASS_UNIT}/{VOLUME_UNIT}"
        soln_density = "{:.3f}{}".format(unit_conversion(raw_density, default_unit=DENSITY_UNIT), DENSITY_UNIT)
        print(f"Raw Density: {extracted_mass:.3f} / {volume:.3f} {MASS_UNIT}/{VOLUME_UNIT}")
        print("--> SOLUTION DENSITY: ", soln_density)
        self.metadata.update({"soln_density": soln_density})

        # Return extracted solution
        if DISCARD_DENSITY_SOLN:
            pipette_station.discard_soln()
            self.exp_vial.extract_soln(extracted_mass=extracted_mass)
        else:
            pipette_station.return_soln(vial=self.exp_vial)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class Extract(RoboticsBase):
    """FireTask for extracting and discarding solution"""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        volume = unit_conversion(self.get("volume", 0), default_unit=VOLUME_UNIT)

        if self.exp_vial.check_addition_id(self.ftask_id):  # Check if addition has already been made

            # Establish stations
            bal_station = BalanceStation(StationStatus().get_first_available("balance"))
            pipette_station = PipetteStation(StationStatus().get_first_available("pipette"))

            # Extract solution
            initial_mass = bal_station.existing_weight(self.exp_vial)
            while volume > 0:
                pipette_volume = MAX_PIPETTE_VOL if volume > MAX_PIPETTE_VOL else volume
                print("PIPETTING VOLUME ", pipette_volume)
                pipette_station.pipette(volume=pipette_volume, vial=self.exp_vial)  # Extract pipette volume
                pipette_station.discard_soln()  # Discard the extracted volume
                volume -= pipette_volume

            # Find extracted mass
            final_mass = bal_station.weigh(self.exp_vial)
            extracted_mass = initial_mass - final_mass

            # Update vial contents
            self.exp_vial.extract_soln(extracted_mass=extracted_mass)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class SetupRinsePotentiostat(RoboticsBase):
    """FireTask for setting up the electrode rinse action by moving the correct
    vial to the potentiostat elevator"""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        potentiostat = PotentiostatStation(self.metadata.get(f"{self.metadata.get('active_method')}_potentiostat"))
        action_vial = VialMove(_id=RINSE_VIALS.get(potentiostat.id))

        # If potentiostat not available, return current vial home and fizzle.
        if not potentiostat.wait_till_available():
            warnings.warn(f"Station {potentiostat} not available. Fizzling rinse.")
            return self.self_fizzle()

        self.success &= potentiostat.place_vial(action_vial)
        self.metadata.update({"active_vial_id": action_vial.id})

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class RinseElectrode(RoboticsBase):
    """FireTask for rinsing an electrode"""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        rinse_time = unit_conversion(self.get("time", 0), default_unit='s')
        method = self.metadata.get("active_method")

        potentiostat = PotentiostatStation(self.metadata.get(f"{method}_potentiostat"))
        potentiostat.initiate_pot(vial=RINSE_VIALS.get(potentiostat.id))
        print(f"RINSING POTENTIOSTAT {potentiostat} FOR {rinse_time} SECONDS.")
        time.sleep(rinse_time)
        potentiostat.update_clean(True)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class CleanElectrode(RoboticsBase):
    """FireTask for cleaning and electrode"""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        # time = self.get("time")
        return FWAction(update_spec=self.updated_specs())


@add_metaclass(abc.ABCMeta)
class SetupPotentiostat(RoboticsBase):
    """Base FireTask for setting up a potentiostat action by moving the correct
    vial to the potentiostat elevator"""
    method: str

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
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

                # Check if potentiostat is clean
                if CHECK_CLEAN_ELECTRODES and not potentiostat.clean:
                    print(f"WARNING. Potentiostat {potentiostat} is not clean.")
                    return self.self_fizzle()

                # Wait till potentiostat is available
                self.success = potentiostat.wait_till_available()
                print("WAITING ", self.success)
                if not self.success:
                    return self.self_fizzle()
            else:
                available_pot = StationStatus().get_first_available(pot_type, check_clean=CHECK_CLEAN_ELECTRODES)
                potentiostat = PotentiostatStation(available_pot) if available_pot else None

            print("SUCCESS, POTENT: ", self.success, potentiostat)
            # If potentiostat not available, return current vial home and fizzle.
            if not (self.success and potentiostat):
                warnings.warn(f"Station {potentiostat} not available. Moving vial {self.exp_vial} back home.")
                self.exp_vial.place_home()
                return self.self_fizzle()
            potentiostat.update_experiment(self.exp_name)
            self.success &= potentiostat.place_vial(self.exp_vial)
        print("POTENTIOSTAT: ", potentiostat)

        # Setup metadata
        cycle = self.metadata.get("cycle", 0)
        self.metadata.update({"collect_tag": f"cycle{cycle + 1:02d}_{self.method}", "cycle": cycle + 1,
                              f"{self.method}_idx": self.metadata.get(f"{self.method}_idx", 1),
                              f"{self.method}_potentiostat": potentiostat, "active_vial_id": self.exp_vial.id,
                              "active_method": self.method, "instrument": f"robotics_{potentiostat}"})
        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class SetupCVPotentiostat(SetupPotentiostat):
    """FireTask setting up CV potentiostat"""
    method = "cv"


@explicit_serialize
class SetupCVUMPotentiostat(SetupPotentiostat):
    """FireTask setting up CV UM potentiostat"""
    method = "cvUM"


@explicit_serialize
class SetupCAPotentiostat(SetupPotentiostat):
    """FireTask setting up CA potentiostat"""
    method = "ca"


@explicit_serialize
class FinishPotentiostat(RoboticsBase):
    """FireTask finishing potentiostat action by removing vial"""
    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        method = self.metadata.get("active_method")
        potentiostat = PotentiostatStation(self.metadata.get(f"{method}_potentiostat"))
        vial_id = self.metadata.get("active_vial_id") or potentiostat.current_content

        if vial_id:
            # Get vial
            active_vial = VialMove(_id=vial_id)
            if active_vial.current_location == potentiostat.id:
                print(f"COLLECTING VIAL {active_vial} FROM {potentiostat}")
                self.success &= active_vial.retrieve()

                # Always return home solvent rinse vials.
                if vial_id.startswith("S_"):
                    active_vial.place_home()
            else:
                print(f"Active vial {active_vial} has already been collected from {potentiostat}")

        self.rerun_fizzed_robot()

        if self.end_experiment:
            potentiostat.update_experiment(None)

        return FWAction(update_spec=self.updated_specs())


@explicit_serialize
class BenchmarkCV(RoboticsBase):
    """FireTask performing CV benchmark measurement"""
    method = "cv"

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CV parameters and keywords
        defaults = DefaultConditions(self, fw_spec, method=self.method)
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", defaults.voltage_sequence)
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", defaults.scan_rate)
        sample_interval = fw_spec.get("sample_interval") or self.get("sample_interval", defaults.sample_interval)
        sens = fw_spec.get("sensitivity") or self.get("sensitivity", defaults.sensitivity)

        # Prep output file info
        active_vial_id = self.metadata.get("active_vial_id")
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"benchmark_%H_%M_%S.txt"))

        # Run CV experiment
        potent = CVPotentiostatStation(self.metadata.get(f"{self.method}_potentiostat"))
        potent.initiate_pot(vial=self.metadata.get("active_vial_id"))
        resistance = potent.run_ircomp_test(data_path=data_path.replace("benchmark_", "iRComp_"))
        collection_time = str(datetime.now())
        self.success &= potent.run_cv(data_path=data_path, voltage_sequence=voltage_sequence, scan_rate=scan_rate,
                                      resistance=resistance, sample_interval=sample_interval, sens=sens)
        # [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        self.collection_data.append({"collect_tag": f"cycle{self.metadata.get('cycle', 0):02d}_benchmark_cv",
                                     "collection_time": collection_time,
                                     "vial_contents": VialStatus(active_vial_id).vial_content,
                                     "soln_density": self.metadata.get("soln_density"),
                                     "data_location": data_path})
        self.metadata.update({"resistance": resistance})
        return FWAction(update_spec=self.updated_specs())


@add_metaclass(abc.ABCMeta)
class RunCVBase(RoboticsBase):
    """Base FireTask for running CV"""
    method: str

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CV parameters and keywords
        defaults = DefaultConditions(self, fw_spec, method=self.method)
        resistance = self.metadata.get("resistance", 0)
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", defaults.voltage_sequence)
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", defaults.scan_rate)
        sample_interval = fw_spec.get("sample_interval") or self.get("sample_interval", defaults.sample_interval)
        sens = fw_spec.get("sensitivity") or self.get("sensitivity", defaults.sensitivity)

        # Prep output data file info
        collect_tag = self.metadata.get("collect_tag")
        active_vial_id = self.metadata.get("active_vial_id")
        cv_idx = self.metadata.get(f"{self.method}_idx", 1)
        data_dir = os.path.join(Path(DATA_DIR) / self.wflow_name / time.strftime("%Y%m%d") / self.full_name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, time.strftime(f"{collect_tag}{cv_idx:02d}_%H_%M_%S.txt"))

        # Run CV experiment
        potent = CVPotentiostatStation(self.metadata.get(f"{self.method}_potentiostat"))
        potent.initiate_pot(vial=self.metadata.get("active_vial_id"))
        collection_time = str(datetime.now())
        self.success &= potent.run_cv(data_path=data_path, voltage_sequence=voltage_sequence, scan_rate=scan_rate,
                                      resistance=resistance, sample_interval=sample_interval, sens=sens)
        # [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        self.metadata.update({f"{self.method}_idx": cv_idx + 1})
        self.collection_data.append({"collect_tag": collect_tag,
                                     "collection_time": collection_time,
                                     "vial_contents": VialStatus(active_vial_id).vial_content,
                                     "soln_density": self.metadata.get("soln_density"),
                                     "data_location": data_path})
        return FWAction(
            update_spec=self.updated_specs(voltage_sequence=voltage_sequence)
        )  # TODO Do we want to propagate voltage sequence??


@explicit_serialize
class RunCV(RunCVBase):
    """FireTask running CV potentiostat"""
    method = "cv"


@explicit_serialize
class RunCVUM(RunCVBase):
    """FireTask running CV UM potentiostat"""
    method = "cvUM"


@explicit_serialize
class RunCA(RoboticsBase):
    """FireTask for running CA"""

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # CA parameters and keywords
        defaults = DefaultConditions(self, fw_spec, method="ca")
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", defaults.voltage_sequence)
        sample_interval = fw_spec.get("sample_interval") or self.get("sample_interval", defaults.sample_interval)
        pulse_width = fw_spec.get("pulse_width") or self.get("pulse_width", defaults.pulse_width)
        sens = fw_spec.get("sensitivity") or self.get("sensitivity", defaults.sensitivity)
        steps = fw_spec.get("steps") or self.get("steps", defaults.steps)

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
        collection_time = str(datetime.now())
        self.success &= potent.run_ca(data_path=data_path, voltage_sequence=voltage_sequence, si=sample_interval,
                                      pw=pulse_width, sens=sens, steps=steps)
        # [os.remove(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if f.endswith(".bin")]

        temperature = TemperatureStation().temperature() or self.metadata.get("temperature")
        print("RECORDED TEMPERATURE: ", temperature)

        self.metadata.update({"ca_idx": ca_idx + 1, "temperature": temperature})
        self.collection_data.append({"collect_tag": collect_tag,
                                     "collection_time": collection_time,
                                     "vial_contents": VialStatus(active_vial_id).vial_content,
                                     "soln_density": self.metadata.get("soln_density"),
                                     "temperature": temperature,
                                     "data_location": data_path})
        return FWAction(update_spec=self.updated_specs())
