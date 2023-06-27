# Copyright 2022, University of Kentucky
import abc
import time
import warnings
from nanoid import generate
from six import add_metaclass
from fireworks import FiretaskBase, explicit_serialize, FWAction
from robotics_api.workflows.actions.cv_techniques import *
from robotics_api.workflows.actions.standard_actions import *
from robotics_api.workflows.actions.status_db_manipulations import *
from robotics_api.workflows.actions.utilities import DeviceConnection
from kortex_api.autogen.client_stubs.BaseCyclicClientRpc import BaseCyclicClient


@explicit_serialize
class EndExperiment(FiretaskBase):
    # FireTask for getting solid sample

    def run_task(self, fw_spec):
        wf_name = fw_spec.get("wflow_name", self.get("wflow_name"))
        vial = VialMove(r_uuid=self.get("vial_uuid"), wflow_name=wf_name)

        # Place vial back home
        success = vial.place(vial.home_snapshot)
        success += snapshot_move(SNAPSHOT_HOME)

        return FWAction(update_spec={"success": success})


@explicit_serialize
class DispenseLiquid(FiretaskBase):
    # FireTask for dispensing liquid

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        wf_name = fw_spec.get("wflow_name", self.get("wflow_name"))
        solv = StationStatus(state_id=self.get("start_uuid"), wflow_name=wf_name) # TODO figure out solvent stuff
        vial = VialMove(r_uuid=self.get("end_uuid"), wflow_name=wf_name)
        metadata = fw_spec.get("metadata", self.get("metadata", {}))
        volume = self.get("volume")
        success = True

        # Uncap vial if capped
        success += vial.uncap
        if not success:
            BaseException("Vial cap is on! CV cannot be run with cap on.")

        # TODO dispense liquid
        # success += vial.place(solv)

        # TODO calculate concentration
        metadata.update({"redox_mol_concentration": DEFAULT_CONCENTRATION})

        updated_specs.update({"success": success})
        return FWAction(update_spec=updated_specs)


@explicit_serialize
class DispenseSolid(FiretaskBase):
    # FireTask for dispensing solid

    def run_task(self, fw_spec):
        # TODO Change once we have solid dispensing
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        wf_name = fw_spec.get("wflow_name", self.get("wflow_name"))
        vial = VialStatus(r_uuid=self.get("start_uuid"), wflow_name=wf_name)
        end_uuid = self.get("end_uuid")
        mass = self.get("mass")

        success = True  # TODO measure solids

        updated_specs.update({"success": success})
        return FWAction(update_spec=updated_specs)


@explicit_serialize
class RecordWorkingElectrodeArea(FiretaskBase):
    # FireTask for recording size of working electrode

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        # working_electrode_area = self.get("size", ) or DEFAULT_WORKING_ELECTRODE_AREA
        working_electrode_area = DEFAULT_WORKING_ELECTRODE_AREA
        metadata = fw_spec.get("metadata", self.get("metadata", {}))
        metadata.update({"working_electrode_surface_area": working_electrode_area})
        updated_specs.update({"metadata": metadata})
        return FWAction(update_spec=updated_specs)


@explicit_serialize
class Heat(FiretaskBase):
    # FireTask for heating

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # temperature = self.get("temperature")
        metadata = fw_spec.get("metadata", self.get("metadata", {}))
        metadata.update({"temperature": DEFAULT_TEMPERATURE})
        updated_specs.update({"metadata": metadata})
        return FWAction(update_spec=updated_specs)


@explicit_serialize
class HeatStir(FiretaskBase):
    # FireTask for heating and siring

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        wf_name = fw_spec.get("wflow_name", self.get("wflow_name"))
        vial = VialStatus(r_uuid=self.get("start_uuid"), wflow_name=wf_name)
        temperature = self.get("temperature")
        stir_time = self.get("time")
        metadata = fw_spec.get("metadata") or self.get("metadata", {})

        if not vial.capped:
            # TODO cap vial
            warnings.warn("Warning. Vial cap is not on and stirring is about to commence.")

        stir_location = os.path.join(SNAPSHOT_DIR, "Stir_plate.json")
        success = snapshot_move(SNAPSHOT_HOME)
        # success += snapshot_move(stir_location)
        # success += stir_plate(stir_time=stir_time)  # TODO add temperature once we have temp capacity
        success += snapshot_move(SNAPSHOT_HOME)

        metadata.update({"temperature": DEFAULT_TEMPERATURE})
        updated_specs.update({"success": success, "metadata": metadata})
        return FWAction(update_spec=updated_specs)


@explicit_serialize
class RinseElectrode(FiretaskBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # time = self.get("time")
        return FWAction(update_spec=updated_specs)


@explicit_serialize
class CleanElectrode(FiretaskBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        # start_uuid = self.get("start_uuid")
        # end_uuid = self.get("end_uuid")
        # time = self.get("time")
        return FWAction(update_spec=updated_specs)


@explicit_serialize
class TestElectrode(FiretaskBase):
    # FireTask for testing electrode cleanliness

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        start_uuid = self.get("start_uuid")  # should be solvent UUID
        orig_locations = self.get("reagent_locations") or fw_spec.get("reagent_locations", {})
        test_electrode_data = fw_spec.get("test_electrode_data") or self.get("test_electrode_data", [])
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        name = fw_spec.get("name") or self.get("name", "no_name_{}".format(generate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", size=4)))
        wflow_name = fw_spec.get("wflow_name", self.get("wflow_name"))
        collect_params = generate_col_params(voltage_sequence, scan_rate)

        # Get solvent vial
        column, row = orig_locations.get(start_uuid)  # Get Sample vial location
        success = snapshot_move(SNAPSHOT_HOME)  # Start at home
        success += vial_home(row, column, action_type='get')  # Get vial

        # Uncap vial if capped
        if VialStatus(r_uuid=start_uuid, wflow_name=wflow_name).capped:
            # TODO uncap vial
            BaseException("Vial cap is on! CV cannot be run with cap on.")

        # Move vial to potentiostat elevator
        success += move_vial_to_potentiostat(at_potentiostat=False)

        # Prep output file info
        file_name = time.strftime("ElectrodeTest_%H_%M_%S.csv")
        data_dir = os.path.join(
            Path("C:/Users") / "Lab" / "D3talesRobotics" / "data" / wflow_name / time.strftime("%Y%m%d") / name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, file_name)
        test_electrode_data.append(data_path)

        # Run CV experiment
        print("RUN CV WITH COLLECTION PARAMS: ", collect_params)
        if RUN_CV:
            expt = CvExperiment([voltage_step(**p) for p in collect_params], load_firm=True)
            expt.run_experiment()
            time.sleep(TIME_AFTER_CV)
            expt.to_txt(data_path)

        # Place vial back home
        retrieve_vial_from_potentiostat()
        success += vial_home(row, column, action_type='place')
        success += snapshot_move(SNAPSHOT_HOME)

        updated_specs.update({"test_electrode_data": test_electrode_data, "success": success,
                              "name": name, "wflow_name": wflow_name})
        return FWAction(update_spec=updated_specs)


@explicit_serialize
class SetupPotentiostat(FiretaskBase):
    # FireTask for testing electrode cleanliness

    def run_task(self, fw_spec):

        return FWAction(update_spec={})


@add_metaclass(abc.ABCMeta)
class RunPotentiostatBase(FiretaskBase):
    _fw_name = "RunPotentiostatBase"


@explicit_serialize
class BenchmarkCV(FiretaskBase):
    # FireTask for testing electrode cleanliness

    def run_task(self, fw_spec):

        return FWAction(update_spec={})


@explicit_serialize
class RunCV(FiretaskBase):
    # FireTask for running CV

    def run_task(self, fw_spec):
        vial_uuid = self.get("start_uuid")
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        cv_type = fw_spec.get("cv_type") or self.get("cv_type", None)
        cv_idx = fw_spec.get("cv_idx") or self.get("cv_idx", 1)
        metadata = fw_spec.get("metadata") or self.get("metadata", {})
        cv_locations = fw_spec.get("cv_locations") or self.get("cv_locations", [])
        voltage_sequence = fw_spec.get("voltage_sequence") or self.get("voltage_sequence", "")
        scan_rate = fw_spec.get("scan_rate") or self.get("scan_rate", "")
        collect_params = generate_col_params(voltage_sequence, scan_rate)
        at_potentiostat = fw_spec.get("at_potentiostat", False) or self.get("at_potentiostat")
        name = fw_spec.get("name") or self.get("name",
                                               "no_name_{}".format(generate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", size=4)))
        wflow_name = fw_spec.get("wflow_name") or self.get("name", "no_name_{}".format(
            generate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", size=4)))
        success = True

        # Uncap vial if capped
        if VialStatus(r_uuid=vial_uuid).capped:
            # TODO uncap vial
            BaseException("Vial cap is on! CV cannot be run with cap on.")

        # Move vial to potentiostat elevator
        at_potentiostat = move_vial_to_potentiostat(at_potentiostat=at_potentiostat)
        print("AT POTENTIOSTAT: ", at_potentiostat)

        # Prep output file info
        file_name = time.strftime("{}_%H_%M_%S.csv".format(cv_type or "exp{:02d}".format(cv_idx)))
        data_dir = os.path.join(Path(DATA_DIR) / wflow_name / time.strftime("%Y%m%d") / name)
        os.makedirs(data_dir, exist_ok=True)
        data_path = os.path.join(data_dir, file_name)

        # Run CV experiment
        print("RUN CV WITH COLLECTION PARAMS: ", collect_params)
        if RUN_CV:
            expt = CvExperiment([voltage_step(**p) for p in collect_params], load_firm=True)
            expt.run_experiment()
            time.sleep(TIME_AFTER_CV)
            expt.to_txt(data_path)
        cv_locations.append(data_path)

        updated_specs.update({"cv_locations": cv_locations, "success": success,
                              "at_potentiostat": at_potentiostat, "name": name, "wflow_name": wflow_name,
                              "cv_idx": cv_idx + 1, "metadata": metadata})
        return FWAction(update_spec=updated_specs)


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

        return FWAction(update_spec={"success": success})
