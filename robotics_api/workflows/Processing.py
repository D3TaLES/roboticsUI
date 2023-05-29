# FireTasks for individual experiment processing
# Copyright 2022, University of Kentucky

import traceback
from statistics import mean
from datetime import datetime
from atomate.utils.utils import env_chk
from d3tales_api.D3database.d3database import *
from robotics_api.workflows.actions.utilities import DeviceConnection
from robotics_api.workflows.actions.processing_utils import *
from robotics_api.workflows.actions.standard_actions import *
from robotics_api.standard_variables import *
from fireworks import FiretaskBase, explicit_serialize, FWAction
from kortex_api.autogen.client_stubs.BaseCyclicClientRpc import BaseCyclicClient

# Copyright 2021, University of Kentucky
TESTING = False


@explicit_serialize
class InitializeRobot(FiretaskBase):
    # FireTask for initializing robot and testing connection

    def run_task(self, fw_spec):
        # Import the utilities helper module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Parse arguments
        connector = Namespace(ip="192.168.1.10", username="admin", password="admin")

        # Create connection to the device and get the router
        with DeviceConnection.createTcpConnection(connector) as router:
            # Create required services
            BaseClient(router)
            BaseCyclicClient(router)

        return FWAction(update_spec={"success": True})


@explicit_serialize
class EndWorkflow(FiretaskBase):
    # FireTask for ending a workflow
    def run_task(self, fw_spec):
        # Place vial back home
        success = snapshot_move(SNAPSHOT_END_HOME)
        return FWAction(update_spec={"success": success})


@explicit_serialize
class ProcessCVBenchmarking(FiretaskBase):
    # FireTask for dispensing solvent

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        mol_id = fw_spec.get("mol_id") or self.get("mol_id")
        name = fw_spec.get("name") or self.get("name")
        cv_locations = fw_spec.get("cv_locations") or self.get("cv_locations", [])
        cv_locations = cv_locations if isinstance(cv_locations, list) else [cv_locations]
        if not cv_locations:
            warnings.warn("WARNING! No CV locations found for CV benchmarking, so DEFAULT VOLTAGE RANGES WILL BE USED.")
            return FWAction(update_spec=dict(**updated_specs))

        cv_location = cv_locations[-1]
        if not os.path.isfile(cv_location):
            warnings.warn("WARNING! CV file {} not found for CV benchmarking, so DEFAULT VOLTAGE RANGES WILL BE USED.".format(cv_location))
            return FWAction(update_spec=dict(**updated_specs))
        data = ProcessCV(cv_location, _id=mol_id, parsing_class=ParseChiCV).data_dict
        new_location = os.path.join("\\".join(cv_location.split("\\")[:-1]), "benchmark_cv.csv")
        os.rename(cv_location, new_location)

        # Plot CV
        image_path = os.path.join("\\".join(cv_location.split("\\")[:-1]), "benchmark_plot.png")
        CVPlotter(connector={"scan_data": "data.scan_data"}).live_plot(data, fig_path=image_path,
                                                                       title=f"Benchmark CV Plot for {name}",
                                                                       xlabel=MULTI_PLOT_XLABEL,
                                                                       ylabel=MULTI_PLOT_YLABEL)
        descriptor_cal = CVDescriptorCalculator(connector={"scan_data": "data.scan_data"})
        peaks_dict = descriptor_cal.peaks(data)
        print(peaks_dict)
        forward_peak = max([p[0] for p in peaks_dict.get("forward", [])])
        reverse_peak = min([p[0] for p in peaks_dict.get("reverse", [])])

        voltage_sequence = "{}, {}, {}V".format(reverse_peak - AUTO_VOLT_BUFFER, forward_peak + AUTO_VOLT_BUFFER,
                                                reverse_peak - AUTO_VOLT_BUFFER)

        print("BENCHMARKED VOLTAGE SEQUENCE: ", voltage_sequence)

        updated_specs.update({"voltage_sequence": voltage_sequence, "cv_locations": [], "cv_idx": 0,
                              "benchmark_location": new_location})
        return FWAction(update_spec=dict(**updated_specs))


@explicit_serialize
class CVProcessor(FiretaskBase):
    # FireTask for processing CV file

    def run_task(self, fw_spec):
        updated_specs = {k: v for k, v in fw_spec.items() if not k.startswith("_")}
        metadata = fw_spec.get("metadata") or self.get("metadata", {})  # TODO add metadata to fw_specs
        meta_update = {"redox_mol_concentration": metadata.get("redox_mol_concentration", DEFAULT_CONCENTRATION),
                       "temperature": metadata.get("temperature", DEFAULT_TEMPERATURE),
                       "working_electrode_surface_area": metadata.get("working_electrode_surface_area",
                                                                      DEFAULT_WORKING_ELECTRODE_AREA),
                       }
        metadata.update(meta_update)

        test_electrode_data = fw_spec.get("test_electrode_data") or self.get("test_electrode_data", [])
        cv_locations = fw_spec.get("cv_locations") or self.get("cv_locations", [])
        cv_locations = cv_locations if isinstance(cv_locations, list) else [cv_locations]
        processing_id = str(fw_spec.get("fw_id") or self.get("fw_id"))
        mol_id = fw_spec.get("mol_id") or self.get("mol_id")
        name = fw_spec.get("name") or self.get("name")

        if not cv_locations:
            warnings.warn("WARNING! No CV locations were found, so no file processing occurred.")
            return FWAction(update_spec=dict(**updated_specs))

        submission_info = {
            "processing_id": processing_id,
            "source": "d3tales_robot",
            "author": "d3tales_robot",
            "author_email": 'd3tales@gmail.com',
            "upload_time": datetime.now().isoformat(),
            "file_type": cv_locations[0].split('.')[-1],
            "data_category": "experimentation",
            "data_type": "cv",
            "all_files_in_zip": [f.split('/')[-1] for f in cv_locations],
        }

        def process_local_data(cv_loc, insert=True):
            # Process data file
            print("Data File: ", cv_loc)
            if not os.path.isfile(cv_loc):
                warnings.warn("WARNING. File {} not found. Processing did not occur.".format(cv_loc))
                return None
            data = ProcessCV(cv_loc, _id=mol_id, submission_info=submission_info, metadata=metadata,
                             parsing_class=ParseChiCV).data_dict
            # Plot CV
            image_path = ".".join(cv_loc.split(".")[:-1]) + "_plot.png"
            CVPlotter(connector={"scan_data": "data.scan_data"}).live_plot(data, fig_path=image_path,
                                                                           title=f"CV Plot for {name}",
                                                                           xlabel=MULTI_PLOT_XLABEL,
                                                                           ylabel=MULTI_PLOT_YLABEL)
            # TODO  Launch send to storage FireTask

            # Insert data into database
            _id = data["_id"]
            if mol_id and insert:
                D3Database(database="robotics_backend", collection_name="experimentation", instance=data).insert(_id)
            return data

        for test_loc in test_electrode_data:
            process_local_data(test_loc, insert=False)

        processed_data = []
        for cv_location in cv_locations:
            data = process_local_data(cv_location)
            if data:
                processed_data.append(data)

        # Plot all CVs
        print(processed_data)
        multi_path = os.path.join("\\".join(cv_locations[0].split("\\")[:-1]), "multi_cv_plot.png")
        CVPlotter(connector={"scan_data": "data.scan_data",
                             "variable_prop": "data.conditions.scan_rate.value"}).live_plot_multi(
            processed_data, fig_path=multi_path, title=f"Multi CV Plot for {mol_id}", xlabel=MULTI_PLOT_XLABEL,
            ylabel=MULTI_PLOT_YLABEL, legend_title=MULTI_PLOT_LEGEND)
        # Record meta data
        all_path = "\\".join(cv_locations[0].split("\\")[:-1]) + "\\all_data.txt"
        with open(all_path, 'w') as fn:
            fn.write(json.dumps(processed_data))
        summary_path = "\\".join(cv_locations[0].split("\\")[:-1]) + "\\summary.txt"
        with open(summary_path, 'w') as fn:
            fn.write(print_cv_analysis(processed_data))

        return FWAction(update_spec={'submission_info': submission_info, 'processed_data': processed_data,
                                     'processing_ids': [d.get("_id") for d in processed_data]})


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
