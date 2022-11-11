# Copyright 2022, University of Kentucky
from fireworks import FiretaskBase, explicit_serialize, FWAction
from robotics_api.workflows.actions.cv_techniques import *
from robotics_api.workflows.actions.standard_actions import *
from robotics_api.workflows.actions.utilities import DeviceConnection

TESTING = True


@explicit_serialize
class GetSample(FiretaskBase):
    # FireTask for getting solid sample

    def run_task(self, fw_spec):
        vial_uuid = self.get("vial_uuid")
        reagent_locations = self.get("reagent_locations") or fw_spec.get("reagent_locations", {})
        column, row = reagent_locations.get(vial_uuid)  # Get Sample vial location

        # Start at home
        success = snapshot_move(SNAPSHOT_HOME)
        # Get vial
        success += vial_home(row, column, action_type='get')

        return FWAction(update_spec={"success": success, "cap_on": False})


@explicit_serialize
class EndExperiment(FiretaskBase):
    # FireTask for getting solid sample

    def run_task(self, fw_spec):
        vial_uuid = self.get("vial_uuid")
        cap_on = self.get("cap_on") or fw_spec.get("cap_on", False)
        reagent_locations = self.get("reagent_locations") or fw_spec.get("reagent_locations", {})
        column, row = reagent_locations.get(vial_uuid)  # Get Sample vial location

        # Place vial back home
        success = vial_home(row, column, action_type='place')
        success += snapshot_move(SNAPSHOT_HOME)

        return FWAction(update_spec={"success": success, "cap_on": cap_on})


@explicit_serialize
class DispenseLiquid(FiretaskBase):
    # FireTask for dispensing liquid

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        volume = self.get("volume")
        reagent_locations = self.get("reagent_locations") or fw_spec.get("reagent_locations", {})
        _, solv_idx = reagent_locations.get(start_uuid)  # Get Solvent location

        snapshot_solv = os.path.join(SNAPSHOT_DIR, "Solvent_{:02}.json".format(int(solv_idx)))
        success = snapshot_move(snapshot_solv)

        # TODO dispense liquid

        return FWAction(update_spec={"success": success, "cap_on": False})


@explicit_serialize
class DispenseSolid(FiretaskBase):
    # FireTask for dispensing solid

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        mass = self.get("mass")

        return FWAction(update_spec={})


@explicit_serialize
class TransferApparatus(FiretaskBase):
    # FireTask for transferring apparatus

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        return FWAction(update_spec={})


@explicit_serialize
class Heat(FiretaskBase):
    # FireTask for heating

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        temperature = self.get("temperature")
        return FWAction(update_spec={})


@explicit_serialize
class HeatStir(FiretaskBase):
    # FireTask for heating and siring

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        temperature = self.get("temperature")
        time = self.get("time")
        return FWAction(update_spec={})


@explicit_serialize
class RecordWorkingElectrodeArea(FiretaskBase):
    # FireTask for recording size of working electrode

    def run_task(self, fw_spec):
        working_electrode_area = self.get("size") or DEFAULT_WORKING_ELECTRODE_AREA
        return FWAction(update_spec={"working_electrode_area": working_electrode_area})


@explicit_serialize
class Polish(FiretaskBase):
    # FireTask for polishing electrode

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        size = self.get("size")
        return FWAction(update_spec={})


@explicit_serialize
class Sonicate(FiretaskBase):
    # FireTask for sonicating electrode

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        time = self.get("time")
        return FWAction(update_spec={})


@explicit_serialize
class Rinse(FiretaskBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        time = self.get("time")
        return FWAction(update_spec={})


@explicit_serialize
class Dry(FiretaskBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        time = self.get("time")
        return FWAction(update_spec={})


@explicit_serialize
class RunCV(FiretaskBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        start_uuid = self.get("start_uuid")
        end_uuid = self.get("end_uuid")
        expflow_exp = self.get("expflow_exp")
        data_paths = fw_spec.get("data_paths") or self.get("data_paths", [])
        name = fw_spec.get("name") or self.get("name", "no_name")
        success = True

        pot_location = snapshot_move(SNAPSHOT_HOME) if not fw_spec.get("pot_location") else True
        snapshot_pot = os.path.join(SNAPSHOT_DIR, "Potentiostat.json")
        success += snapshot_move(snapshot_pot)

        file_name = time.strftime("exp_%H_%M_%S.csv")
        data_dir = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "data" / name / time.strftime("%Y%m%d"))
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, file_name)

        ex_steps = [
            voltage_step(0.8, 10),  # 1V 10mV/s
            voltage_step(0, 10),  # 0V 10mV/s
            voltage_step(0.8, 10),  # 1V 10mV/s
            voltage_step(0, 10),  # 0V 10mV/s
        ]  # TODO specify steps
        experiment = CvExperiment(ex_steps, load_firm=False)
        experiment.run_experiment()
        time.sleep(TIME_AFTER_CV)
        experiment.to_txt(data_path)
        data_paths.append(data_path)

        # if TESTING:
        #     import shutil
        #     src_path = Path("C:/Users") / "Lab" / "D3talesRobotics" / "data" / "test_cv.csv"
        #     shutil.copyfile(src_path, data_path)
        return FWAction(update_spec={"cv_locations": data_paths, "success": success, "cap_on": False, "pot_location": pot_location})


@explicit_serialize
class TestMovement(FiretaskBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        # Import the utilities helper module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Parse arguments
        connector = Namespace(ip="192.168.1.10", username="admin", password="admin")

        # Create connection to the device and get the router
        with DeviceConnection.createTcpConnection(connector) as router:
            # Create required services
            base = BaseClient(router)
            base_cyclic = BaseCyclicClient(router)

            # Example core
            success = True

            success &= example_move_to_home_position(base)
            success &= example_cartesian_action_movement(base, base_cyclic)
            success &= example_angular_action_movement(base)

            success &= example_move_to_home_position(base)
            success &= example_cartesian_trajectory_movement(base, base_cyclic)
            success &= example_angular_trajectory_movement(base)

        return FWAction(update_spec={"success": success})
