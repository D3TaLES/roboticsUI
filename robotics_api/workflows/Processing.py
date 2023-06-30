# FireTasks for individual experiment processing
# Copyright 2022, University of Kentucky

import traceback
from six import add_metaclass
from atomate.utils.utils import env_chk
from d3tales_api.D3database.d3database import *
from d3tales_api.Processors.back2front import *
from robotics_api.workflows.actions.utilities import DeviceConnection
from robotics_api.workflows.actions.processing_utils import *
from robotics_api.workflows.actions.standard_actions import *
from robotics_api.workflows.actions.status_db_manipulations import *
from robotics_api.standard_variables import *
from fireworks import FiretaskBase, explicit_serialize, FWAction
from kortex_api.autogen.client_stubs.BaseCyclicClientRpc import BaseCyclicClient

# Copyright 2021, University of Kentucky
TESTING = False
VERBOSE = 1


@explicit_serialize
class InitializeRobot(FiretaskBase):
    # FireTask for initializing robot and testing connection

    def run_task(self, fw_spec):
        # Import the utilities helper module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Create connection to the device and get the router
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
        reset_reagent_db(reagents, current_wflow_name=wflow_name)
        reset_vial_db(experiments, current_wflow_name=wflow_name)
        reset_station_db(current_wflow_name=wflow_name)
        return FWAction(update_spec={"success": True})


@add_metaclass(abc.ABCMeta)
class ProcessBase(FiretaskBase):
    _fw_name = "ProcessBase"

    def setup_task(self, fw_spec):
        self.metadata = fw_spec.get("metadata", {})
        self.collection_data = fw_spec.get("collection_data", {})
        self.processing_data = fw_spec.get("processing_data", {})
        self.mol_id = fw_spec.get("mol_id") or self.get("mol_id")
        self.name = fw_spec.get("full_name") or self.get("full_name")
        self.processing_id = str(fw_spec.get("fw_id") or self.get("fw_id"))

        if not self.collection_data:
            warnings.warn("WARNING! No CV locations were found, so no file processing occurred.")
            return FWAction(update_spec=self.updated_specs())

    def updated_specs(self):
        return {"metadata": self.metadata, "collection_data": self.collection_data,
                "processing_data": self.processing_data}

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

    def process_local_data(self, cv_loc, metadata, insert=True):
        # Process data file
        print("Data File: ", cv_loc)
        if not os.path.isfile(cv_loc):
            warnings.warn("WARNING. File {} not found. Processing did not occur.".format(cv_loc))
            return None
        file_type = cv_loc.split('.')[-1]
        p_data = ProcessCV(cv_loc, _id=self.mol_id, submission_info=self.submission_info(file_type),
                           metadata=metadata, parsing_class=ParseChiCV).data_dict
        # Plot CV
        image_path = ".".join(cv_loc.split(".")[:-1]) + "_plot.png"
        CVPlotter(connector={"scan_data": "data.scan_data",
                             "we_surface_area": "data.conditions.working_electrode_surface_area"
                             }).live_plot(p_data, fig_path=image_path,
                                          title=f"CV Plot for {self.name}",
                                          xlabel=MULTI_PLOT_XLABEL,
                                          ylabel=MULTI_PLOT_YLABEL,
                                          current_density=PLOT_CURRENT_DENSITY,
                                          a_to_ma=CONVERT_A_TO_MA)
        # TODO  Launch send to storage FireTask

        # Insert data into database
        _id = p_data["_id"]
        if self.mol_id and insert:
            D3Database(database="robotics", collection_name="experimentation", instance=p_data).insert(_id)
        return p_data



@explicit_serialize
class ProcessCVBenchmarking(FiretaskBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        metadata = fw_spec.get("metadata", {})
        location_data = fw_spec.get("location_data", {})

        mol_id = fw_spec.get("mol_id") or self.get("mol_id")
        name = fw_spec.get("full_name") or self.get("full_name")
        cv_locations = location_data.get("benchmark_locations")
        if not cv_locations:
            warnings.warn("WARNING! No CV locations found for CV benchmarking, so DEFAULT VOLTAGE RANGES WILL BE USED.")
            return FWAction(update_spec={"metadata": metadata, "location_data": location_data})

        cv_location = cv_locations[-1]
        if not os.path.isfile(cv_location):
            warnings.warn(
                "WARNING! CV file {} not found for CV benchmarking, so DEFAULT VOLTAGE RANGES WILL BE USED.".format(
                    cv_location))
            return FWAction(update_spec={"metadata": metadata, "location_data": location_data})
        data = ProcessCV(cv_location, _id=mol_id, parsing_class=ParseChiCV).data_dict

        # Plot CV
        image_path = os.path.join("\\".join(cv_location.split("\\")[:-1]), "benchmark_plot.png")
        CVPlotter(connector={"scan_data": "data.scan_data",
                             "we_surface_area": "data.conditions.working_electrode_surface_area"
                             }).live_plot(data, fig_path=image_path,
                                          title=f"Benchmark CV Plot for {name}",
                                          xlabel=MULTI_PLOT_XLABEL,
                                          ylabel=MULTI_PLOT_YLABEL,
                                          current_density=PLOT_CURRENT_DENSITY,
                                          a_to_ma=CONVERT_A_TO_MA)
        descriptor_cal = CVDescriptorCalculator(connector={"scan_data": "data.scan_data"})
        peaks_dict = descriptor_cal.peaks(data)
        print(peaks_dict)
        forward_peak = max([p[0] for p in peaks_dict.get("forward", [])])
        reverse_peak = min([p[0] for p in peaks_dict.get("reverse", [])])

        voltage_sequence = "{}, {}, {}V".format(reverse_peak - AUTO_VOLT_BUFFER, forward_peak + AUTO_VOLT_BUFFER,
                                                reverse_peak - AUTO_VOLT_BUFFER)

        print("BENCHMARKED VOLTAGE SEQUENCE: ", voltage_sequence)

        return FWAction(update_spec={"voltage_sequence": voltage_sequence,
                                     "metadata": metadata, "location_data": location_data})


@explicit_serialize
class CVProcessor(ProcessBase):
    # FireTask for processing CV file

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        solv_locations = location_data.get("solv_locations")
        cv_locations = location_data.get("cv_locations")
        data_path = os.path.join("\\".join(cv_locations[0].split("\\")[:-1]))
        processing_id = str(fw_spec.get("fw_id") or self.get("fw_id"))

        for solv_loc in solv_locations:
            self.process_local_data(solv_loc, insert=False)

        processed_data = []
        for cv_location in cv_locations:
            data = self.process_local_data(cv_location)
            if data:
                processed_data.append(data)

        # Plot all CVs
        multi_path = os.path.join(data_path, "multi_cv_plot.png")
        CVPlotter(connector={"scan_data": "data.scan_data",
                             "variable_prop": "data.conditions.scan_rate.value",
                             "we_surface_area": "data.conditions.working_electrode_surface_area"}).live_plot_multi(
            processed_data, fig_path=multi_path, title=f"Multi CV Plot for {self.mol_id}", xlabel=MULTI_PLOT_XLABEL,
            ylabel=MULTI_PLOT_YLABEL, legend_title=MULTI_PLOT_LEGEND, current_density=PLOT_CURRENT_DENSITY,
            a_to_ma=CONVERT_A_TO_MA)

        # Meta Properties
        print("Calculating metadata...")
        metadata_dict = CV2Front(backend_data=processed_data, run_anodic=RUN_ANODIC, insert=False).meta_dict
        metadata_id = str(uuid.uuid4())
        D3Database(database="robotics", collection_name="metadata", instance=dict(metadata=metadata_dict),
                   validate_schema=False).insert(metadata_id)

        # Record all data
        with open(data_path + "\\all_data.txt", 'w') as fn:
            fn.write(json.dumps(processed_data))
        with open(data_path + "\\summary.txt", 'w') as fn:
            fn.write(print_cv_analysis(processed_data, metadata_dict, verbose=VERBOSE))

        self.processing_data.update({'processed_data': processed_data, "metadata_id": metadata_id,
                                     'processing_ids': [d.get("_id") for d in processed_data]})
        return FWAction(update_spec=self.updated_specs())


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
                    "to {}".format("rtansfer", self["files"], self["dest"]))

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
