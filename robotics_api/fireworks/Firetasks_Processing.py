# FireTasks for individual experiment processing
# Copyright 2024, University of Kentucky
import traceback
from six import add_metaclass
from fireworks import LaunchPad
from atomate.utils.utils import env_chk
from d3tales_api.Calculators.calculators import *
from d3tales_api.D3database.back2front import CV2Front
from fireworks import FiretaskBase, explicit_serialize, FWAction
from kortex_api.autogen.client_stubs.BaseCyclicClientRpc import BaseCyclicClient
from robotics_api.actions.system_tests import reset_stations
from robotics_api.actions.standard_actions import *
from robotics_api.utils.processing_utils import *
from robotics_api.utils.kinova_utils import DeviceConnection

# Copyright 2024, University of Kentucky
TESTING = False
VERBOSE = 1


@explicit_serialize
class InitializeRobot(FiretaskBase):
    """FireTask for initializing the robot and testing connection.

    This task initializes a robot by creating a connection to the device and
    resetting stations to their default status.

    Args:
        fw_spec (dict): Fireworks spec that contains information for the task.

    Returns:
        FWAction: An action that updates the Fireworks spec indicating success.
    """

    def run_task(self, fw_spec):
        # Import the utilities helper module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Create connection to the device and get the router
        if RUN_ROBOT:
            connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
            with DeviceConnection.createTcpConnection(connector) as router:
                BaseClient(router)
                BaseCyclicClient(router)

        reset_stations()

        return FWAction(update_spec={"success": True})


@explicit_serialize
class InitializeStatusDB(FiretaskBase):
    """FireTask for initializing status database contents.

    This task resets and initializes the reagent, experiment, and station databases.

    Args:
        fw_spec (dict): Fireworks spec that contains information for the task.

    Returns:
        FWAction: An action that updates the Fireworks spec indicating success.
    """

    def run_task(self, fw_spec):
        reagents = fw_spec.get("reagents") or self.get("reagents") or {}
        experiments = fw_spec.get("experiment_vials") or self.get("experiment_vials") or {}
        wflow_name = fw_spec.get("wflow_name") or self.get("wflow_name") or "unknown_wflow"
        print("REAGENTS: ", reagents)
        print("EXPS: ", experiments)
        # Setup standard_data databases
        reset_reagent_db(reagents, current_wflow_name=wflow_name)
        reset_vial_db(experiments, current_wflow_name=wflow_name)
        reset_station_db(current_wflow_name=wflow_name)

        return FWAction(update_spec={"success": True})


@add_metaclass(abc.ABCMeta)
class ProcessBase(FiretaskBase):
    """Abstract base class for processing experiment data.

    This class provides common methods for processing experiment data such as
    setting up the task, updating specs, and handling potentiostat data.

    Attributes:
        metadata (dict): Metadata for the experiment.
        collection_data (dict): Data collection information.
        processing_data (dict): Data processing information.
        mol_id (str): Molecule ID.
        solv_id (str): Solvent ID.
        rom_id (str): Redox molecule ID.
        elect_id (str): Electrolyte ID.
        soln_density (str): Solution density.
        name (str): Name of the task.
        processing_id (str): Processing ID.
        coll_dict (dict): Dictionary of collected data.
        collect_tag (str): Tag for collection cycle.
        lpad (LaunchPad): Fireworks LaunchPad instance for rerunning fizzled jobs.
        data_path (str): Path to experiment data.
        processed_locs (list): List of processed data locations.
        wflow_name (str): Workflow name.

    Methods:
        setup_task(fw_spec, data_len_error=True): Set up task parameters from Fireworks spec.
        updated_specs(**kwargs): Update Fireworks specs with current task information.
        submission_info(file_type): Generate submission info for experiment data.
        conc_info(vial_contents): Calculate concentration information from vial contents.
        plot_cv(cv_loc, p_data, plot_name="", title_tag=""): Plot cyclic voltammetry (CV) data.
        process_pot_data(file_loc, metadata, insert=True, processing_class=None): Process potentiostat data file.
        process_solv_data(): Process solvent CV data.
    """
    _fw_name = "ProcessBase"
    metadata: dict
    collection_data: dict
    processing_data: dict
    mol_id: str
    solv_id: str
    rom_id: str
    elect_id: str
    soln_density: str
    name: str
    processing_id: str
    coll_dict: dict
    collect_tag: str
    lpad: LaunchPad
    data_path: str
    processed_locs: list
    wflow_name: list

    def setup_task(self, fw_spec, data_len_error=True):
        """Set up task parameters from the Fireworks spec.

        Args:
            fw_spec (dict): Fireworks spec that contains task parameters.
            data_len_error (bool): Flag to raise a warning if no collection data is found. Default is True.
        """
        self.metadata = fw_spec.get("metadata", {})
        self.collection_data = fw_spec.get("collection_data") or []
        self.processing_data = fw_spec.get("processing_data") or {}
        self.processed_locs = self.processing_data.get("processed_locs") or []
        self.mol_id = fw_spec.get("mol_id") or self.get("mol_id")
        self.solv_id = fw_spec.get("solv_id") or self.get("solv_id")
        self.rom_id = fw_spec.get("rom_id") or self.get("rom_id")
        self.elect_id = fw_spec.get("elect_id") or self.get("elect_id")
        self.soln_density = self.metadata.get("soln_density")
        self.name = fw_spec.get("full_name") or self.get("full_name")
        self.processing_id = str(fw_spec.get("fw_id") or self.get("fw_id"))
        self.wflow_name = str(fw_spec.get("wflow_name") or self.get("wflow_name"))

        self.coll_dict = collection_dict(self.collection_data)
        self.collect_tag = self.metadata.get("collect_tag", f"UnknownCycle")
        self.lpad = LaunchPad().from_file(LAUNCHPAD)

        if not self.collection_data and data_len_error:
            warnings.warn("WARNING! No data locations were found, so no file processing occurred.")
            return FWAction(update_spec=self.updated_specs())

        if self.collection_data:
            self.data_path = os.path.join("\\".join(self.collection_data[0].get("data_location").split("\\")[:-1]))

    def updated_specs(self, **kwargs):
        """
        Updates the FireWorks specifications with additional metadata, collection, and processing data.

        Args:
            **kwargs: Additional key-value pairs to update in the specifications.

        Returns:
            dict: A dictionary containing the updated specifications.
        """
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
        """
        Prepares metadata for submission to the database.

        Args:
            file_type (str): The type of the file being processed.

        Returns:
            dict: A dictionary with submission information.
        """
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

    def conc_info(self, vial_contents):
        """
        Generates concentration information based on the vial contents.

        Args:
            vial_contents (dict): The contents of the vial being processed.

        Returns:
            dict: A dictionary with concentration information, including redox molecule and electrolyte concentrations
            and mole fractions.
        """
        return {
            "redox_mol_concentration": get_concentration(vial_contents, solute_id=self.rom_id, solv_id=self.solv_id,
                                                         soln_density=self.soln_density),
            "electrolyte_concentration": get_concentration(vial_contents, self.elect_id, self.solv_id,
                                                           soln_density=self.soln_density),
            "redox_mol_fraction": get_concentration(vial_contents, solute_id=self.rom_id, solv_id=self.solv_id,
                                                    soln_density=self.soln_density, mol_fraction=True),
            "electrolyte_mol_fraction": get_concentration(vial_contents, self.elect_id, self.solv_id,
                                                          soln_density=self.soln_density, mol_fraction=True),
        }

    @staticmethod
    def plot_cv(cv_loc, p_data, plot_name="", title_tag=""):
        """
        Generates and saves a cyclic voltammetry (CV) plot.

        Args:
            cv_loc (str): The file location of the CV data.
            p_data (dict): The processed CV data to be plotted.
            plot_name (str): The name of the plot (default: "").
            title_tag (str): Additional tag to add to the plot title (default: "").
        """
        if 'chi' not in POTENTIOSTAT_A_EXE_PATH:
            image_path = ".".join(cv_loc.split(".")[:-1]) + "_plot.png"
            CVPlotter(connector={"scan_data": "data.scan_data",
                                 "we_surface_area": "data.conditions.working_electrode_surface_area"
                                 }).live_plot(p_data, fig_path=image_path,
                                              title=f"{title_tag} CV Plot for {plot_name}",
                                              xlabel=MULTI_PLOT_XLABEL,
                                              ylabel=MULTI_PLOT_YLABEL,
                                              current_density=PLOT_CURRENT_DENSITY,
                                              a_to_ma=CONVERT_A_TO_MA)

    def process_pot_data(self, file_loc, metadata, insert=True, processing_class=None):
        """
        Processes potentiometric data files.

        Args:
            file_loc (str): The location of the file being processed.
            metadata (dict): Metadata related to the file.
            insert (bool): Whether to insert the processed data into the database (default: True).
            processing_class (class): The processing class used to handle the data (default: None).

        Returns:
            dict: The processed data as a dictionary, or None if the file is not found or already processed.
        """
        print("Data File: ", file_loc)
        if not os.path.isfile(file_loc):
            warnings.warn("WARNING. File {} not found. Processing did not occur.".format(file_loc))
            return None
        if file_loc in self.processed_locs:
            warnings.warn("WARNING. File {} already processed. Further processing did not occur.".format(file_loc))
            return None
        file_type = file_loc.split('.')[-1]
        e_ref = ReagentStatus(_id=self.rom_id).formal_potential
        if self.mol_id and e_ref is None:
            if "calib" not in self.wflow_name.lower():
                raise KeyError(f"No formal potential exists in the reagents database for {self.mol_id}")
        metadata.update({"instrument": f"robotics_{self.metadata.get('potentiostat')}",
                         "e_ref": e_ref})
        p_data = processing_class(file_loc, _id=self.mol_id, submission_info=self.submission_info(file_type),
                                  metadata=metadata, micro_electrodes=MICRO_ELECTRODES).data_dict

        # Insert data into database
        _id = p_data["_id"]
        if self.mol_id and insert:
            MongoDatabase(database="robotics", collection_name="experimentation",
                          instance=p_data, validate_schema=False).insert(_id)
        self.processed_locs.append(file_loc)
        return p_data

    def process_solv_data(self):
        """Process solvent CV data"""
        solv_data = self.coll_dict.get("solv_cv", [])
        for d in solv_data:
            p_data = self.process_pot_data(d.get("data_location"), metadata=self.metadata, insert=False,
                                           processing_class=ProcessChiCV)
            self.plot_cv(d.get("data_location"), p_data, plot_name="Solvent")
            if FIZZLE_DIRTY_ELECTRODE:
                dirty_calc = DirtyElectrodeDetector(connector={"scan_data": "data.scan_data"})
                dirty = dirty_calc.calculate(p_data, max_current_range=DIRTY_ELECTRODE_CURRENT)
                if dirty:
                    raise SystemError("WARNING! Electrode may be dirty!")
            print(f"Solvent {d} processed.")


@explicit_serialize
class ProcessCVBenchmarking(ProcessBase):
    """
    FireTask for processing cyclic voltammetry (CV) benchmarking data and determining voltage ranges.

    This task processes CV data, calculates the appropriate voltage sequence based on benchmarking peaks,
    and updates the FireWorks specifications with this information.
    """
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
            self.metadata.update(self.conc_info(cv_data[0].get("vial_contents")))
            p_data = self.process_pot_data(cv_loc, metadata=self.metadata, insert=False, processing_class=ProcessChiCV)
            self.plot_cv(cv_loc, p_data, plot_name="Benchmark")

            # Calculate old voltage sequence
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
    """
    FireTask for processing calibration jobs related to Conductance and Resistance measurements.

    This task processes Chronoamperometry (CA) calibration data, calculates measured conductance and resistance,
    and updates the calibration database with the processed information.
    """

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)

        # Process CA calibration data
        ca_data = self.coll_dict.get(f"{self.collect_tag.split('_')[0]}_ca", [])
        processed_ca_data = []
        for d in ca_data:
            m_data = self.metadata
            self.metadata.update(self.conc_info(d.get("vial_contents")))
            p_data = self.process_pot_data(d.get("data_location"), metadata=m_data, processing_class=ProcessChiCA)
            if p_data:
                processed_ca_data.append(p_data)

            # Insert CA calibration
            calib_instance = {
                "mol_id": self.mol_id,  # D3TaLES ID
                "date_updated": datetime.now().strftime('%Y_%m_%d'),  # Day
                "cond_measured": p_data.get("data", {}).get("measured_conductance"),
                "res_measured": p_data.get("data", {}).get("measured_resistance"),
                "temperature": self.metadata.get("temperature"),
            }
            if KCL_CALIB:
                calib_instance.update({"cell_constant": kcl_cell_constant(calib_instance.get("cond_measured"),
                                                                          calib_instance.get("temperature"))})
            else:
                cond_true = CA_CALIB_STDS.get(self.mol_id)
                calib_instance.update({
                    "cond_true": cond_true,
                    "res_true": 1 / cond_true if cond_true else None,
                })
            print(calib_instance)
            ChemStandardsDB(standards_type="CACalib", instance=calib_instance)

        self.processing_data.update({'processed_locs': self.processed_locs})
        return FWAction(update_spec=self.updated_specs())


# noinspection PyTypeChecker
@explicit_serialize
class DataProcessor(ProcessBase):
    """
    FireTask for processing cyclic voltammetry (CV) and chronoamperometry (CA) data files.

    This class is responsible for the processing of CV and CA data, performing various calculations, plotting graphs,
    and storing the results in a database. It also calculates metadata and processes potentiometric data.

    Processes:
        1. CV data:
            - Retrieves and processes CV data.
            - Performs meta calculations and records the data.
            - Plots individual and multi-CV graphs.
            - Stores CV metadata in a database.
        2. CA data:
            - Retrieves and processes CA data.
            - Calculates conductivity, resistance, and other properties.
            - Stores CA metadata and data in a database.
    """

    def run_task(self, fw_spec):
        self.setup_task(fw_spec)
        self.process_solv_data()

        cv_data = self.coll_dict.get(f"{self.collect_tag.split('_')[0]}_cv", [])
        ca_data = self.coll_dict.get(f"{self.collect_tag.split('_')[0]}_ca", [])
        metadata_dict = {}

        # Process CV data for cycle
        processed_cv_data, plot_name = [], ""
        for d in cv_data:
            self.metadata.update(self.conc_info(d.get("vial_contents")))
            m_data = self.metadata
            p_data = self.process_pot_data(d.get("data_location"), metadata=m_data, processing_class=ProcessChiCV)
            plot_name = f"{self.name}, {self.metadata['redox_mol_concentration']} redox, " \
                        f"{self.metadata['electrolyte_concentration']} SE"
            self.plot_cv(d.get("data_location"), p_data, plot_name)
            if p_data:
                processed_cv_data.append(p_data)

        # CV Meta Calcs and Data Recording
        if processed_cv_data:
            # Plot all CVs
            multi_path = os.path.join(self.data_path, f"{self.collect_tag}_multi_cv_plot.png")
            CVPlotter(connector={"scan_data": "data.scan_data",
                                 "variable_prop": "data.conditions.scan_rate.value",
                                 "we_surface_area": "data.conditions.working_electrode_surface_area"}).live_plot_multi(
                processed_cv_data, fig_path=multi_path, title=f"Multi CV Plot for {plot_name or self.mol_id}",
                xlabel=MULTI_PLOT_XLABEL,
                ylabel=MULTI_PLOT_YLABEL, legend_title=MULTI_PLOT_LEGEND, current_density=PLOT_CURRENT_DENSITY,
                a_to_ma=CONVERT_A_TO_MA)

            # CV Meta Properties
            print("Calculating metadata...")
            if self.mol_id:
                print(self.mol_id)
                metadata_dict.update(CV2Front(backend_data=processed_cv_data, run_anodic=RUN_ANODIC, insert=False,
                                              micro_electrodes=MICRO_ELECTRODES).meta_dict)

            # Record all data
            with open(self.data_path + f"\\{self.collect_tag.strip('cycle')}_all_data.txt", 'w') as fn:
                fn.write(json.dumps(processed_cv_data))
            with open(self.data_path + f"\\summary_{self.collect_tag.strip('cycle')}.txt", 'w') as fn:
                fn.write(print_cv_analysis(processed_cv_data, metadata_dict, verbose=VERBOSE))

        # Process CA data for cycle
        processed_ca_data = []
        for d in ca_data:
            self.metadata.update(self.conc_info(d.get("vial_contents")))
            self.metadata.update({"cell_constant": get_cell_constant()})
            m_data = self.metadata
            print("METADATA: ", self.metadata)
            p_data = self.process_pot_data(d.get("data_location"), metadata=m_data, processing_class=ProcessChiCA)
            if p_data:
                print("---------- CA CALCULATION RESULTS ----------")
                print("Conductivity: ", p_data.get("data", {}).get("conductivity"))
                processed_ca_data.append(p_data)

        if processed_ca_data:
            # CA Meta Properties
            save_props = ["conductivity", "measured_conductance", "resistance", "measured_resistance"]
            metadata_dict.update({p: processed_ca_data[-1].get(p) for p in save_props})
            # Record all data
            with open(self.data_path + f"\\{self.collect_tag.strip('cycle')}_all_data.txt", 'w') as fn:
                fn.write(json.dumps(processed_ca_data))
            with open(self.data_path + f"\\summary_{self.collect_tag.strip('cycle')}.txt", 'w') as fn:
                fn.write(print_ca_analysis(processed_ca_data, verbose=VERBOSE))

        metadata_id = str(uuid.uuid4())
        MongoDatabase(database="robotics", collection_name="metadata", instance=dict(metadata=metadata_dict),
                      validate_schema=False).insert(metadata_id)
        self.processing_data.update({'processed_data': processed_cv_data, "metadata_id": metadata_id,
                                     'processing_ids': [d.get("_id") for d in processed_cv_data],
                                     'processed_locs': self.processed_locs})
        return FWAction(update_spec=self.updated_specs(), propagate=True)


@explicit_serialize
class SendToStorage(FiretaskBase):
    """
    FireTask for securely transferring a file to a remote storage server using SFTP.

    This task handles the process of transferring a file to a remote storage server, creating the necessary directory structure,
    retrying the transfer in case of failure, and optionally ignoring errors. Once transferred, it updates the Firework
    specification with the stored file's location.
    """
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
    """
    FireTask responsible for ending a workflow by performing final robotic and data management tasks.

    This task checks the current contents of the robot's grip, ensures that the vial (if any) is returned to its home position,
    and triggers the final data snapshots to be moved to their designated locations.
    """
    def run_task(self, fw_spec):
        robot_content = StationStatus('robot_grip').current_content
        if robot_content:
            VialMove(_id=robot_content).place_home()
        success = snapshot_move(SNAPSHOT_HOME)
        success &= snapshot_move(SNAPSHOT_END_HOME)
        return FWAction(update_spec={"success": success})
