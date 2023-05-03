# Copyright 2022, University of Kentucky
import time
import warnings

from nanoid import generate
from fireworks import FiretaskBase, explicit_serialize, FWAction
from robotics_api.workflows.actions.cv_techniques import *
from robotics_api.workflows.actions.standard_actions import *
from robotics_api.workflows.actions.utilities import DeviceConnection
from kortex_api.autogen.client_stubs.BaseCyclicClientRpc import BaseCyclicClient


@explicit_serialize
class GetSample(FiretaskBase):
    # FireTask for getting solid sample

    def run_task(self, fw_spec):
        vial_uuid = self.get("vial_uuid")
        orig_locations = self.get("reagent_locations") or fw_spec.get("reagent_locations", {})
        column, row = orig_locations.get(vial_uuid)  # Get Sample vial location

        # Start at home
        success = snapshot_move(SNAPSHOT_HOME)
        # Get vial
        success += vial_home(row, column, action_type='get')

        return FWAction(update_spec={"success": success, "cap_on": False})


@explicit_serialize
class EndExperiment(FiretaskBase):
    # FireTask for getting solid sample

    def run_task(self, fw_spec):
        success = True
        if fw_spec.get("pot_location"):
            print("send command to elevator")
            success += cv_elevator(endpoint="down")
            success += get_place_vial(fw_spec.get("pot_location"), action_type="get",
                                      pre_position_file=fw_spec.get("pre_pot_location"), raise_amount=0.028)
            success += snapshot_move(SNAPSHOT_HOME)

        vial_uuid = self.get("vial_uuid")
        cap_on = self.get("cap_on") or fw_spec.get("cap_on", False)
        orig_locations = self.get("reagent_locations") or fw_spec.get("reagent_locations", {})
        column, row = orig_locations.get(vial_uuid)  # Get Sample vial location

        # Place vial back home
        success += vial_home(row, column, action_type='place')
        success += snapshot_move(SNAPSHOT_HOME)

        return FWAction(update_spec={"success": success, "cap_on": cap_on})


@explicit_serialize
class DispenseLiquid(FiretaskBase):
    # FireTask for dispensing liquid

    def run_task(self, fw_spec):
        solv_uuid = self.get("start_uuid")
        vial_uuid = self.get("end_uuid")
        volume = self.get("volume")
        success = True
        cap_on = self.get("cap_on") or fw_spec.get("cap_on", False)
        metadata = fw_spec.get("metadata") or self.get("metadata", {})
        orig_locations = self.get("reagent_locations") or fw_spec.get("reagent_locations", {})
        _, solv_idx = orig_locations.get(solv_uuid)  # Get Solvent location
        success = True

        # Uncap vial if capped
        if cap_on:
            # TODO uncap vial
            cap_on = False
            BaseException("Vial cap is on! CV cannot be run with cap on.")

        # TODO dispense liquid
        snapshot_solv = os.path.join(SNAPSHOT_DIR, "Solvent_{:02}.json".format(int(solv_idx)))
        # success += snapshot_move(snapshot_solv)

        # TODO calculate concentration
        metadata.update({"redox_mol_concentration": DEFAULT_CONCENTRATION})

        return FWAction(update_spec={"success": success, "cap_on": cap_on})


@explicit_serialize
class DispenseSolid(FiretaskBase):
    # FireTask for dispensing solid

    def run_task(self, fw_spec):
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # mass = self.get("mass")

        return FWAction(update_spec={})


@explicit_serialize
class TransferApparatus(FiretaskBase):
    # FireTask for transferring apparatus

    def run_task(self, fw_spec):
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        return FWAction(update_spec={})


@explicit_serialize
class Heat(FiretaskBase):
    # FireTask for heating

    def run_task(self, fw_spec):
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # temperature = self.get("temperature")
        metadata = fw_spec.get("metadata") or self.get("metadata", {})
        metadata.update({"temperature": DEFAULT_TEMPERATURE})
        return FWAction(update_spec={})


@explicit_serialize
class HeatStir(FiretaskBase):
    # FireTask for heating and siring

    def run_task(self, fw_spec):
        vial_uuid = self.get("start_uuid")
        temperature = self.get("temperature")
        stir_time = self.get("time")
        cap_on = self.get("cap_on") or fw_spec.get("cap_on", False)
        metadata = fw_spec.get("metadata") or self.get("metadata", {})

        if not cap_on:
            # TODO cap vial
            warnings.warn("Warning. Vial cap is not on and stirring is about to commence.")

        stir_location = os.path.join(SNAPSHOT_DIR, "Stir_plate.json")
        success = snapshot_move(SNAPSHOT_HOME)
        # success += snapshot_move(stir_location)
        # success += stir_plate(stir_time=stir_time)  # TODO add temperature once we have temp capacity
        success += snapshot_move(SNAPSHOT_HOME)

        metadata.update({"temperature": DEFAULT_TEMPERATURE})
        return FWAction(update_spec={"success": success, "cap_on": cap_on, "metadata": metadata})


@explicit_serialize
class RecordWorkingElectrodeArea(FiretaskBase):
    # FireTask for recording size of working electrode

    def run_task(self, fw_spec):
        working_electrode_area = self.get("size") or DEFAULT_WORKING_ELECTRODE_AREA
        return FWAction(update_spec={"working_electrode_surface_area": working_electrode_area})


@explicit_serialize
class Polish(FiretaskBase):
    # FireTask for polishing electrode

    def run_task(self, fw_spec):
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # size = self.get("size")
        return FWAction(update_spec={})


@explicit_serialize
class Sonicate(FiretaskBase):
    # FireTask for sonicating electrode

    def run_task(self, fw_spec):
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # time = self.get("time")
        return FWAction(update_spec={})


@explicit_serialize
class Rinse(FiretaskBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # time = self.get("time")
        return FWAction(update_spec={})


@explicit_serialize
class Dry(FiretaskBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # time = self.get("time")
        return FWAction(update_spec={})


@explicit_serialize
class RunCV(FiretaskBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        cv_idx = fw_spec.get("cv_idx") or self.get("cv_idx", 1)
        metadata = fw_spec.get("metadata") or self.get("metadata", {})
        cv_locations = fw_spec.get("cv_locations") or self.get("cv_locations", [])
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        collect_params = generate_col_params(voltage_sequence, scan_rate)
        name = fw_spec.get("name") or self.get("name", "no_name_{}".format(generate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", size=4)))
        cap_on = self.get("cap_on") or fw_spec.get("cap_on", False)
        wflow_name = fw_spec.get("wflow_name") or self.get("name", "no_name_{}".format(generate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", size=4)))
        success = True

        # Uncap vial if capped
        if cap_on:
            # TODO uncap vial
            BaseException("Vial cap is on! CV cannot be run with cap on.")

        # Move vial to potentiostat elevator
        pot_location = os.path.join(SNAPSHOT_DIR, "Potentiostat.json")
        pre_pot_location = os.path.join(SNAPSHOT_DIR, "Pre_potentiostat.json")
        if not fw_spec.get("pot_location") == pot_location:
            metadata.update({"working_electrode_surface_area": DEFAULT_WORKING_ELECTRODE_AREA})
            success += snapshot_move(SNAPSHOT_HOME)
            success += get_place_vial(pot_location, action_type="place", pre_position_file=pre_pot_location, raise_amount=0.028)
            success += snapshot_move(SNAPSHOT_HOME)
            success += cv_elevator(endpoint="up")
            time.sleep(10)

        # Prep output file info
        file_name = time.strftime("exp{:02d}_%H_%M_%S.csv".format(cv_idx))
        data_dir = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "data" / wflow_name / time.strftime("%Y%m%d")) / name
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, file_name)

        # Run CV experiment
        print("RUN CV...")
        print("COLLECTION PARAMS: ", collect_params)
        if RUN_CV:
            exp_steps = [voltage_step(**p) for p in collect_params]
            expt = CvExperiment(exp_steps, load_firm=True)
            expt.run_experiment()
            time.sleep(TIME_AFTER_CV)
            expt.to_txt(data_path)
        cv_locations.append(data_path)

        return FWAction(update_spec={"cv_locations": cv_locations, "success": success, "cap_on": False,
                                     "pot_location": pot_location, "pre_pot_location": pre_pot_location,
                                     "name": name, "cv_idx": cv_idx + 1, "metadata": metadata})


@explicit_serialize
class TestMovement(FiretaskBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        # Import the utilities helper module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Parse arguments
        # connector = Namespace(ip="192.168.1.10", username="admin", password="admin")
        #
        # # Create connection to the device and get the router
        # with DeviceConnection.createTcpConnection(connector) as router:
        #     # Create required services
        #     base = BaseClient(router)
            # base_cyclic = BaseCyclicClient(router)
            #
            # # Example core
            # success = True
            #
            # success &= example_move_to_home_position(base)
            # success &= example_cartesian_action_movement(base, base_cyclic)
            # success &= example_angular_action_movement(base)
            #
            # success &= example_move_to_home_position(base)
            # success &= example_cartesian_trajectory_movement(base, base_cyclic)
            # success &= example_angular_trajectory_movement(base)

        # return FWAction(update_spec={"success": success})
