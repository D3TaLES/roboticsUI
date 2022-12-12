# FireTasks for individual experiment processing
# Copyright 2022, University of Kentucky

import traceback
from datetime import datetime
from atomate.utils.utils import env_chk
from d3tales_api.D3database.d3database import *
from d3tales_api.Processors.d3tales_parser import *
from robotics_api.workflows.actions.utilities import DeviceConnection
from robotics_api.workflows.actions.standard_actions import *
from robotics_api.workflows.actions.standard_variables import *
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
class CVProcessor(FiretaskBase):
    # FireTask for processing CV file

    def run_task(self, fw_spec):
        metadata = fw_spec.get("metadata") or self.get("metadata", [])  # TODO add metadata to fw_specs
        cv_locations = fw_spec.get("cv_locations") or self.get("cv_locations", [])
        cv_locations = cv_locations if isinstance(cv_locations, list) else [cv_locations]
        processing_id = str(fw_spec.get("fw_id") or self.get("fw_id"))
        mol_id = fw_spec.get("mol_id") or self.get("mol_id")

        submission_info = {}
        if cv_locations:
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

        processed_data = []
        print(cv_locations)
        for cv_location in cv_locations:
            # Process data file
            data = ProcessCV(cv_location, _id=mol_id, submission_info=submission_info, metadata=metadata,
                             parsing_class=ParseChiCV).data_dict
            processed_data.append(data)

            # Plot CV
            image_path = ".".join(cv_location.split(".")[:-1]) + ".png"
            CVPlotter(connector={"scan_data": "data.scan_data"}).live_plot(data, fig_path=image_path)

            # TODO  Launch send to storage FireTask

            # Insert data into database
            _id = data["_id"]
            D3Database(database="robotics_backend", collection_name="experimentation", instance=data).insert(_id)

        return FWAction(update_spec={'submission_info': submission_info, 'processed_data': processed_data})


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
        destination_path = "{}/d3tales/{}/{}/{}".format(storage_base_loc, fw_spec.get("mol_id"), data_category, data_type)
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
