# FireTasks for individual experiment processing
# Copyright 2022, University of Kentucky

import traceback
from six import add_metaclass
from fireworks import LaunchPad
from atomate.utils.utils import env_chk
from d3tales_api.D3database.d3database import *
from robotics_api.workflows.actions.utilities import DeviceConnection
from robotics_api.workflows.actions.processing_utils import *
from robotics_api.workflows.actions.standard_actions import *
from robotics_api.workflows.actions.db_manipulations import *
from robotics_api.standard_variables import *
from fireworks import FiretaskBase, explicit_serialize, FWAction
from kortex_api.autogen.client_stubs.BaseCyclicClientRpc import BaseCyclicClient

# Copyright 2023, University of Kentucky
TESTING = False
VERBOSE = 1


@explicit_serialize
class InitializeRobot(FiretaskBase):
    # FireTask for initializing robot and testing connection

    def run_task(self, fw_spec):
        # Import the utilities helper module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Create connection to the device and get the router
        if RUN_ROBOT:
            connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
            with DeviceConnection.createTcpConnection(connector) as router:
                BaseClient(router)
                BaseCyclicClient(router)

        return FWAction(update_spec={"success": True})


@explicit_serialize
class InitializeStatusDB(FiretaskBase):
    # FireTask for initializing status database contents

    def run_task(self, fw_spec):
        reagents = fw_spec.get("reagents") or self.get("reagents") or {}
        experiments = fw_spec.get("experiment_vials") or self.get("experiment_vials") or {}
        wflow_name = fw_spec.get("wflow_name") or self.get("wflow_name") or "unknown_wflow"
        print("REAGENTS: ", reagents)
        print("EXPS: ", experiments)
        reset_reagent_db(reagents, current_wflow_name=wflow_name)
        reset_vial_db(experiments, current_wflow_name=wflow_name)
        reset_station_db(current_wflow_name=wflow_name)

        # Setup standards databases
        setup_formal_potentials()
        return FWAction(update_spec={"success": True})


@add_metaclass(abc.ABCMeta)
class ProcessBase(FiretaskBase):
    _fw_name = "ProcessBase"
    metadata: dict
    collection_data: dict
    processing_data: dict
    mol_id: str
    name: str
    processing_id: str
    coll_dict: dict
    cv_cycle: float
    collect_tag: str
    lpad: LaunchPad
    data_path: str
    processed_locs: list

    def setup_task(self, fw_spec, data_len_error=True):
        self.metadata = fw_spec.get("metadata", {})
        self.collection_data = fw_spec.get("collection_data") or {}
        self.processing_data = fw_spec.get("processing_data") or {}
        self.processed_locs = self.processing_data.get("processed_locs") or []
        self.mol_id = fw_spec.get("mol_id") or self.get("mol_id")
        self.name = fw_spec.get("full_name") or self.get("full_name")
        self.processing_id = str(fw_spec.get("fw_id") or self.get("fw_id"))

        self.coll_dict = collection_dict(self.collection_data)
        self.cv_cycle = self.metadata.get("cv_cycle", 1)
        self.collect_tag = self.metadata.get("collect_tag", f"Cycle{self.cv_cycle:02d}_cv")
        self.lpad = LaunchPad().from_file(LAUNCHPAD)

        if not self.collection_data and data_len_error:
            warnings.warn("WARNING! No data locations were found, so no file processing occurred.")
            return FWAction(update_spec=self.updated_specs())

        if self.collection_data:
            self.data_path = os.path.join("\\".join(self.collection_data[0].get("data_location").split("\\")[:-1]))

    def updated_specs(self, **kwargs):
        if RERUN_FIZZLED_ROBOT:
            fizzled_fws = self.lpad.fireworks.find({"state": "FIZZLED", "$or": [
                {"name": {"$regex": "_setup_"}},
                {"name": {"$regex": "robot"}}
            ]}).distinct("fw_id")
            [self.lpad.rerun_fw(fw) for fw in fizzled_fws]
            print(f"Fireworks {str(fizzled_fws)} released from fizzled state.")
        specs = {"metadata": self.metadata, "collection_data": self.collection_data,
                 "processing_data": self.processing_data}
        specs.update(dict(**kwargs))
        return specs

    def submission_info(self, file_type):
        return {
            "processing_id": self.processing_id,
            "source": "d3tales_robot",
            "author": "d3tales_robot",
            "author_email": 'd3tales@gmail.com',
            "upload_time": datetime.now().isoformat(),
            "file_type": file_type,
            "data_category": "experimentation",
            "data_type": "cv",
        }

    def plot_cv(self, cv_loc, p_data, title_tag=""):
        # Plot CV
        if 'chi' not in POTENTIOSTAT_A_EXE_PATH:
            image_path = ".".join(cv_loc.split(".")[:-1]) + "_plot.png"
            CVPlotter(connector={"scan_data": "data.scan_data",
                                 "we_surface_area": "data.conditions.working_electrode_surface_area"
                                 }).live_plot(p_data, fig_path=image_path,
                                              title=f"{title_tag} CV Plot for {self.name}",
                                              xlabel=MULTI_PLOT_XLABEL,
                                              ylabel=MULTI_PLOT_YLABEL,
                                              current_density=PLOT_CURRENT_DENSITY,
                                              a_to_ma=CONVERT_A_TO_MA)

    def process_pot_data(self, file_loc, metadata, insert=True, processing_class=None):
        # Process data file
        print("Data File: ", file_loc)
        if not os.path.isfile(file_loc):
            warnings.warn("WARNING. File {} not found. Processing did not occur.".format(file_loc))
            return None
        if file_loc in self.processed_locs:
            warnings.warn("WARNING. File {} already processed. Further processing did not occur.".format(file_loc))
            return None
        file_type = file_loc.split('.')[-1]
        e_ref = ChemStandardsDB(standards_type="mol_props", _id=self.mol_id).get_prop("formal_potential")
        metadata.update({"instrument": f"robotics_{self.metadata.get('potentiostat')}",
                         "e_ref": e_ref})
        processing_class = processing_class or ProcessCVMicro if MICRO_ELECTRODES else ProcessCV
        p_data = processing_class(file_loc, _id=self.mol_id, submission_info=self.submission_info(file_type),
                                  metadata=metadata).data_dict

        # Insert data into database
        _id = p_data["_id"]
        if self.mol_id and insert:
            D3Database(database="robotics", collection_name="experimentation",
                       instance=p_data, validate_schema=False).insert(_id)
        self.processed_locs.append(file_loc)
        return p_data

    def process_solv_data(self):
        # Process solvent CV data
        solv_data = self.coll_dict.get("solv_cv", [])
        for d in solv_data:
            p_data = self.process_pot_data(d.get("data_location"), metadata=self.metadata, insert=False)
            self.plot_cv(d.get("data_location"), p_data)
            if FIZZLE_DIRTY_ELECTRODE:
                dirty_calc = DirtyElectrodeDetector(connector={"scan_data": "data.scan_data"})
                dirty = dirty_calc.calculate(p_data, max_current_range=DIRTY_ELECTRODE_CURRENT)
                if dirty:
                    raise SystemError("WARNING! Electrode may be dirty!")
            print(f"Solvent {d} processed.")


@explicit_serialize
class ProcessCVBenchmarking(ProcessBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        self.setup_task(fw_spec, data_len_error=False)

        # Check Benchmarking data file
        cv_data = self.coll_dict.get("benchmark_cv")
        if not cv_data:
            warnings.warn("WARNING! No CV locations found for CV benchmarking; DEFAULT VOLTAGE RANGES WILL BE USED.")
            return FWAction(update_spec=self.updated_specs())
        cv_loc = cv_data[0].get("data_location")
        if not os.path.isfile(cv_loc):
            warnings.warn(f"WARNING! CV benchmarking file {cv_loc} not found; DEFAULT VOLTAGE RANGES WILL BE USED.")
            return FWAction(update_spec=self.updated_specs())

        try:
            # Process benchmarking data
            self.metadata.update(
                {"redox_mol_concentration": get_rmol_concentration(cv_data[0].get("vial_contents"), fw_spec)})
            p_data = self.process_pot_data(cv_loc, metadata=self.metadata, insert=False)
            self.plot_cv(cv_loc, p_data, title_tag="Benchmark")

            # Calculate new voltage sequence
            if MICRO_ELECTRODES:
                e_half = p_data.get("data", {}).get("e_half")[0]
                forward_peak, reverse_peak = e_half + ADD_MICRO_BUFFER, e_half - ADD_MICRO_BUFFER
            else:
                descriptor_cal = CVDescriptorCalculator(connector={"scan_data": "data.scan_data"})
                peaks_dict = descriptor_cal.peaks(p_data)
                forward_peak = max([p[0] for p in peaks_dict.get("forward", [])])
                reverse_peak = min([p[0] for p in peaks_dict.get("reverse", [])])
        except Exception as e:
            print(e)
            warnings.warn(f"WARNING! Error calculating benchmark peaks; DEFAULT VOLTAGE RANGES WILL BE USED.")
            return FWAction(update_spec=self.updated_specs())

        voltage_sequence = "{:.3f}, {:.3f}, {:.3f}V".format(reverse_peak - AUTO_VOLT_BUFFER,
                                                            forward_peak + AUTO_VOLT_BUFFER,
                                                            reverse_peak - AUTO_VOLT_BUFFER)
        print("BENCHMARKED VOLTAGE SEQUENCE: ", voltage_sequence)

        return FWAction(update_spec=self.updated_specs(voltage_sequence=voltage_sequence))


# noinspection PyTypeChecker
@explicit_serialize
class ProcessCalibration(ProcessBase):
    # FireTask for processing Calibration jobs

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # Process CA calibration data
        ca_data = self.coll_dict.get(f"{self.collect_tag.split('_')[0]}_ca", [])
        processed_ca_data = []
        for d in ca_data:
            m_data = self.metadata
            ca_calib_measured, ca_calib_true = get_calib(d.get("vial_contents"), fw_spec)
            m_data.update({"redox_mol_concentration": get_rmol_concentration(d.get("vial_contents"), fw_spec),
                           "calib_measured": ca_calib_measured, "calib_true": ca_calib_true})
            p_data = self.process_pot_data(d.get("data_location"), metadata=m_data, processing_class=ProcessCA)
            if p_data:
                processed_ca_data.append(p_data)

            # Insert CA calibration
            calib_instance = {
                "_id": datetime.now().isoformat(),  # Date
                "date": datetime.now().strftime('%Y_%m_%d'),  # Day
                "calib_measured": p_data.get("measured_conductivity"),
                "calib_true": CA_CALIB_STDS.get(self.mol_id)
            }
            ChemStandardsDB(standards_type="ca_calib", instance=calib_instance)

        self.processing_data.update({'processed_locs': self.processed_locs})
        return FWAction(update_spec=self.updated_specs())


# noinspection PyTypeChecker
@explicit_serialize
class DataProcessor(ProcessBase):
    # FireTask for processing CV file

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        self.process_solv_data()

        cv_data = self.coll_dict.get(f"{self.collect_tag.split('_')[0]}_cv", [])
        ca_data = self.coll_dict.get(f"{self.collect_tag.split('_')[0]}_ca", [])
        metadata_dict = {}

        # Process CV data for cycle
        processed_cv_data = []
        for d in cv_data:
            m_data = self.metadata
            m_data.update({"redox_mol_concentration": get_rmol_concentration(d.get("vial_contents"), fw_spec)})
            p_data = self.process_pot_data(d.get("data_location"), metadata=m_data)
            self.plot_cv(d.get("data_location"), p_data)
            if p_data:
                processed_cv_data.append(p_data)

        # CV Meta Calcs and Data Recording
        if processed_cv_data:
            # Plot all CVs
            multi_path = os.path.join(self.data_path, f"{self.collect_tag}_multi_cv_plot.png")
            CVPlotter(connector={"scan_data": "data.scan_data",
                                 "variable_prop": "data.conditions.scan_rate.value",
                                 "we_surface_area": "data.conditions.working_electrode_surface_area"}).live_plot_multi(
                processed_cv_data, fig_path=multi_path, title=f"Multi CV Plot for {self.mol_id}",
                xlabel=MULTI_PLOT_XLABEL,
                ylabel=MULTI_PLOT_YLABEL, legend_title=MULTI_PLOT_LEGEND, current_density=PLOT_CURRENT_DENSITY,
                a_to_ma=CONVERT_A_TO_MA)

            # CV Meta Properties
            print("Calculating metadata...")
            metadata_dict.update(CV2Front(backend_data=processed_cv_data, run_anodic=RUN_ANODIC, insert=False,
                                          micro_electrodes=MICRO_ELECTRODES).meta_dict)

            # Record all data
            with open(self.data_path + f"\\{self.collect_tag}_cv_all_data.txt", 'w') as fn:
                fn.write(json.dumps(processed_cv_data))
            with open(self.data_path + f"\\{self.collect_tag}_cv_summary.txt", 'w') as fn:
                fn.write(print_cv_analysis(processed_cv_data, metadata_dict, verbose=VERBOSE))

        # Process CA data for cycle
        processed_ca_data = []
        for d in ca_data:
            m_data = self.metadata
            ca_calib_measured, ca_calib_true = get_calib()
            m_data.update({"redox_mol_concentration": get_rmol_concentration(d.get("vial_contents"), fw_spec),
                           "calib_measured": ca_calib_measured, "calib_true": ca_calib_true})
            p_data = self.process_pot_data(d.get("data_location"), metadata=m_data, processing_class=ProcessCA)
            if p_data:
                processed_ca_data.append(p_data)

        if processed_ca_data:
            # CA Meta Properties
            save_props = ["conductivity", "measured_conductivity", "resistance", "measured_resistance"]
            metadata_dict.update({p: processed_ca_data[-1].get(p) for p in save_props})
            # Record all data
            with open(self.data_path + f"\\{self.collect_tag}_ca_all_data.txt", 'w') as fn:
                fn.write(json.dumps(processed_ca_data))
            with open(self.data_path + f"\\{self.collect_tag}_cv_summary.txt", 'w') as fn:
                fn.write(print_ca_analysis(processed_ca_data, verbose=VERBOSE))

        metadata_id = str(uuid.uuid4())
        D3Database(database="robotics", collection_name="metadata", instance=dict(metadata=metadata_dict),
                   validate_schema=False).insert(metadata_id)
        self.processing_data.update({'processed_data': processed_cv_data, "metadata_id": metadata_id,
                                     'processing_ids': [d.get("_id") for d in processed_cv_data],
                                     'processed_locs': self.processed_locs})
        return FWAction(update_spec=self.updated_specs(), propagate=True)


@explicit_serialize
class SendToStorage(FiretaskBase):
    _fw_name = "SendToStorage"

    def run_task(self, fw_spec):
        max_retry = self.get('max_retry', 0)
        retry_delay = self.get('retry_delay', 10)
        ignore_errors = self.get('ignore_errors', False)

        filepath = self["filepath"]
        remote_server = self.get("remote_server", )
        storage_base_loc = env_chk(self.get("storage_base_loc"), fw_spec) or fw_spec["_fw_env"]["storage_base_loc"]
        key_file = env_chk(self.get("storage_key"), fw_spec) or fw_spec["_fw_env"]["storage_key"]
        remote_server["key_filename"] = key_file

        submission_data = fw_spec["submission_data"]
        data_category = submission_data["data_category"]
        data_type = submission_data["data_type"]
        destination_path = "{}/d3tales/{}/{}/{}".format(storage_base_loc, fw_spec.get("mol_id"), data_category,
                                                        data_type)
        destination = os.path.join(destination_path, filepath.split("/")[-1]).replace("//", "/")

        def mkdir_p(sftp, remote_directory):
            dir_path = str()
            for dir_folder in remote_directory.split("/"):
                if dir_folder == "":
                    continue
                dir_path += r"/{0}".format(dir_folder)
                try:
                    sftp.listdir(dir_path)
                except IOError:
                    sftp.mkdir(dir_path)

        import paramiko
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(**remote_server)
        sftp = ssh.open_sftp()

        try:
            mkdir_p(sftp, destination_path)
            sftp.put(filepath, destination)

        except Exception:
            traceback.print_exc()
            if max_retry:

                # we want to avoid hammering either the local or remote machine
                time.sleep(retry_delay)
                self['max_retry'] -= 1
                self.run_task(fw_spec)

            elif not ignore_errors:
                raise ValueError(
                    "There was an error performing operation {} from {} "
                    "to {}".format("transfer", self["files"], self["dest"]))

        # Update processed data fireworks spec
        processed_data = fw_spec["processed_data"]
        processed_data["submission_info"].update({"stored_location": destination})

        if not TESTING:
            try:
                sftp.remove(filepath)
                pass
            except FileNotFoundError:
                pass
        sftp.close()
        ssh.close()

        return FWAction(update_spec={"processed_data": processed_data})


@explicit_serialize
class EndWorkflow(FiretaskBase):
    # FireTask for ending a workflow
    def run_task(self, fw_spec):
        success = snapshot_move(SNAPSHOT_END_HOME)
        return FWAction(update_spec={"success": success})
