import time

import pint
import serial
from serial.tools.list_ports import comports
from d3tales_api.Processors.parser_cv import *
from robotics_api.actions.kinova_move import *
from robotics_api.actions.db_manipulations import *


def perturbed_snapshot(snapshot_file, perturb_amount=RAISE_AMOUNT, axis="z"):
    with open(snapshot_file, 'r') as fn:
        master_data = json.load(fn)

    # Generate temporary perturbed file
    new_height = master_data["poses"]["pose"][0]["reachPose"]["targetPose"][axis] + perturb_amount
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"][axis] = new_height
    with open(os.path.join(SNAPSHOT_DIR, "_temp_perturbed.json"), "w+") as fn:
        json.dump(master_data, fn, indent=2)
    return os.path.join(SNAPSHOT_DIR, "_temp_perturbed.json")


def get_place_vial(snapshot_file, action_type="get", pre_position_file=None, raise_amount=RAISE_AMOUNT,
                   release_vial=True, raise_error=False, go=True, leave=True):
    """
    Function that executes an action getting or placing
    Args:
        snapshot_file: str, path to snapshot file
        action_type: str, 'get' if the action is getting a vail, 'place' if action is placing the vial
        pre_position_file: str, path to snapshot file for teh position that should be touched before and after
            placing/retrieving the vial
        raise_amount: float,
        release_vial: bool,
        raise_error: bool,
        go: bool, go to snapshot file location if True
        leave: bool, leave from snapshot file location if True
    Returns: bool, success of action
    """
    snapshot_file_above = perturbed_snapshot(snapshot_file, perturb_amount=raise_amount)

    # Start open if getting a vial
    success = snapshot_move(target_position='open') if action_type == "get" else True

    if go:
        # If pre-position, go there
        if pre_position_file:
            success += snapshot_move(pre_position_file)
            if not success and raise_error:
                raise Exception(f"Failed to move robot arm pre-position snapshot {pre_position_file} before target.")

        # Go to above target position before target
        success += snapshot_move(snapshot_file_above)
        if not success and raise_error:
            raise Exception(f"Failed to move robot arm to {raise_amount} above target before snapshot {snapshot_file}.")

        # Go to target position
        target = VIAL_GRIP_TARGET if action_type == "get" else 'open' if release_vial else VIAL_GRIP_TARGET
        success += snapshot_move(snapshot_file, target_position=target)
        if not success and raise_error:
            raise Exception(f"Failed to move robot arm to snapshot {snapshot_file}.")

    if leave:
        # Go to above target position after target
        success += snapshot_move(snapshot_file_above)
        if not success and raise_error:
            raise Exception(f"Failed to move robot arm to {raise_amount} above target after snapshot {snapshot_file}.")

        # If pre-position, go there
        if pre_position_file:
            success += snapshot_move(pre_position_file)
            if not success and raise_error:
                raise Exception(f"Failed to move robot arm pre-position snapshot {pre_position_file} after target.")

    return success


def screw_lid(screw=True, starting_position="vial-screw_test.json", linear_z=0.00003, angular_z=120):
    """
    Function that executes an action getting or placing
    Args:
        screw: bool, screw lid if True, unscrew if false
        starting_position: str, filepath to snapshot of starting location
        linear_z: float,
        angular_z: float, rotation increment in degree

    Returns: bool, success of action
    """
    snapshot_start = os.path.join(SNAPSHOT_DIR, starting_position)
    snapshot_top = perturbed_snapshot(snapshot_start, perturb_amount=0.02)
    if screw:
        success = snapshot_move(snapshot_top)
        snapshot_start = perturbed_snapshot(snapshot_start, perturb_amount=0.0005)
    else:
        success = snapshot_move(target_position='open')
    success += snapshot_move(snapshot_start)
    success += snapshot_move(target_position=VIAL_GRIP_TARGET + 4)

    rotation_increment = (angular_z / 20) if screw else (-angular_z / 20)
    raise_height = linear_z if screw else -linear_z
    for _ in range(5):
        success += twist_hand(linear_z=raise_height, angular_z=rotation_increment)

    if screw:
        success = snapshot_move(target_position='open')
    else:
        print("Done unscrewing. ")
        success += snapshot_move(snapshot_top)

    return success


def send_arduino_cmd(station, command, address=ARDUINO_ADDRESS, return_txt=False):
    try:
        arduino = serial.Serial(address, 115200, timeout=.1)
    except:
        try:
            time.sleep(20)
            arduino = serial.Serial(address, 115200, timeout=.1)
        except:
            raise Exception("Warning! {} is not connected".format(address))
    time.sleep(1)  # give the connection a second to settle
    arduino.write(bytes(f"{station}_{command}", encoding='utf-8'))
    print("Command {} given to station {} at {} via Arduino.".format(command, station, address))
    start_time = time.time()
    try:
        while True:
            print("trying to read...")
            data = arduino.readline()
            print("waiting for {} arduino results for {:.1f} seconds...".format(station, time.time() - start_time))
            if data:
                result_txt = data.decode().strip()  # strip out the new lines
                print("ARDUINO RESULT: ", result_txt)
                if "success" in result_txt:
                    return result_txt if return_txt else True
                elif "failure" in result_txt:
                    return False
            time.sleep(1)
    except KeyboardInterrupt:
        arduino.write(bytes(f"ABORT_{station}", encoding='utf-8'))
        while True:
            print("Aborted arduino. Trying to read abort message...")
            data = arduino.readline()
            if data:
                print("ARDUINO ABORT MESSAGE: ", data.decode().strip())  # strip out the new lines
                raise KeyboardInterrupt
            time.sleep(1)


def write_test(file_path, test_type=""):
    test_files = {
        "cv": os.path.join(ROBOTICS_API, "actions", "standard_data", "CV.txt"),
        "ca": os.path.join(ROBOTICS_API, "actions", "standard_data", "CA.txt"),
        "ircomp": os.path.join(ROBOTICS_API, "actions", "standard_data", "iRComp.txt"),
    }
    test_fn = test_files.get(test_type.lower())
    if os.path.isfile(test_fn):
        with open(test_fn, 'r') as fn:
            test_text = fn.read()
    else:
        test_text = "test"
    with open(file_path, 'w+') as fn:
        fn.write(test_text)


class VialMove(VialStatus):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            raise Exception("To move a vial, a vial ID or reagent UUID or experiment name must be provided.")

    def retrieve(self, raise_error=True, **move_kwargs):
        success = False
        if self.current_location == "robot_grip":
            if StationStatus("robot_grip").current_content == self.id:
                return True
            if raise_error:
                raise Exception(f"Vial {self.id} location is listed as robot_grip, but robot grip current_content is "
                                f"listed as {StationStatus('robot_grip').current_content}.")
        elif not self.robot_available():
            robot_content = StationStatus('robot_grip').current_content
            try:
                print(f"Trying to place {robot_content} home. ")
                VialMove(_id=robot_content).place_home()
            except Exception as e:
                if raise_error:
                    raise Exception(f"Robot cannot retrieve {self.id} vial because robot is unavailable. The robot "
                                    f"currently contains {robot_content}. Tried to Place {robot_content} home. "
                                    f"Failed with exception {e}")
        if self.robot_available():
            print("Robot is available")
            if self.current_location == "home":
                print("Retrieving vial from home...")
                success = snapshot_move(SNAPSHOT_HOME)  # Start at home
                success += get_place_vial(self.home_snapshot, action_type='get', raise_error=raise_error, **move_kwargs)
            elif "potentiostat" in self.current_location:
                print(f"Retrieving vial from potentiostat station {self.current_location}...")
                station = PotentiostatStation(self.current_location)
                success += station.retrieve_vial(self)
            elif "solvent" in self.current_location:
                print(f"Retrieving vial from solvent station {self.current_location}...")
                station = LiquidStation(self.current_location)
                success += station.retrieve_vial(self)
            else:
                success += get_place_vial(self.current_location, action_type='get', raise_error=raise_error,
                                          **move_kwargs)
            # success += snapshot_move(SNAPSHOT_HOME)
            if success:
                self.update_position("robot_grip")

        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully retrieved. Vial {self.id} is located "
                            f"at {self.current_location}. ")
        return success

    def go_to_snapshot(self, target_location: str, raise_error=True, **move_kwargs):
        self.retrieve(raise_error=True)
        # success = snapshot_move(SNAPSHOT_HOME)  # Start at home
        success = get_place_vial(target_location, action_type='place', release_vial=False,
                                 raise_error=raise_error, **move_kwargs)

        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully moved to {target_location}.")

        return success

    def place_snapshot(self, target_location: str, raise_error=True, **move_kwargs):
        self.retrieve(raise_error=True)
        success = snapshot_move(SNAPSHOT_HOME)  # Start at home
        success += get_place_vial(target_location, action_type='place',
                                  raise_error=raise_error, **move_kwargs)
        # success += snapshot_move(SNAPSHOT_HOME)
        self.update_position(target_location)

        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully moved to {target_location}.")

        StationStatus("robot_grip").empty() if success else None
        return success

    def go_to_station(self, station: StationStatus, raise_error=True):
        self.retrieve(raise_error=True)

        print("TEST ", self.current_location, station)
        success = True if station.current_content == self.id else False
        if station.available:
            # success = snapshot_move(SNAPSHOT_HOME)  # Start at home
            print("LOCATION: ", station.location_snapshot)
            success += get_place_vial(station.location_snapshot, action_type='place', release_vial=False,
                                      raise_error=raise_error, leave=False, raise_amount=station.raise_amount)
            station.update_available(False)
            station.update_content(self.id)

        if raise_error and not success:
            raise Exception(f"Vial {self} was not successfully moved to {station}.")

        return success

    def place_station(self, station: StationStatus, raise_error=True):
        return station.place_vial(self, raise_error=raise_error)

    @staticmethod
    def leave_station(station: StationStatus, raise_error=True):
        success = get_place_vial(station.location_snapshot, action_type='place', release_vial=False,
                                 raise_error=raise_error, go=False, raise_amount=station.raise_amount)
        station.empty()
        return success

    def place_home(self, **kwargs):
        if self.current_location == "home":
            print(f"Vial {self} is already at home.")
            return True
        success = self.place_snapshot(self.home_snapshot, **kwargs)
        self.update_position("home")
        return success

    def update_position(self, position):
        self.update_location(position)
        station = StationStatus(position)
        if station.exists:
            station.update_content(self.id)
            station.update_available(False)
        print(f"Successfully updated vial {self} to position {position}")

    @staticmethod
    def robot_available():
        return StationStatus("robot_grip").available


class LiquidStation(StationStatus):
    def __init__(self, _id, raise_amount=-0.04, **kwargs):
        super().__init__(_id=_id, **kwargs)
        if not self.id:
            raise Exception("To operate a solvent station, a solvent name must be provided.")
        if self.type != "solvent":
            raise Exception(f"Station {self.id} is not a liquid.")
        self.raise_amount = raise_amount
        self.pre_location_snapshot = None
        self.arduino_name = "L{:01d}".format(int(self.id.split("_")[-1]))

    def place_vial(self, vial: VialMove, raise_error=True):
        return vial.go_to_station(self, raise_error=raise_error)

    def dispense(self, vial: VialMove, volume, raise_error=True):
        self.place_vial(vial, raise_error=raise_error)
        actual_volume = self.dispense_only(volume)
        vial.leave_station(self, raise_error=raise_error)
        return actual_volume

    def dispense_only(self, volume, dispense=DISPENSE):
        arduino_vol = unit_conversion(volume, default_unit="mL") * 1000  # send volume in micro liter
        if dispense:
            send_arduino_cmd(self.arduino_name, arduino_vol)
        actual_volume = volume  # TODO get actual volume
        return actual_volume


class StirStation(StationStatus):
    def __init__(self, _id, **kwargs):
        super().__init__(_id=_id, **kwargs)
        if not self.id:
            raise Exception("To operate the Stir-Heat station, a Stir-Heat name must be provided.")
        if self.type != "stir":
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.pre_location_snapshot = None
        self.arduino_name = "S{:1d}".format(int(self.id.split("_")[-1]))
        self.raise_amount = 0

    def place_vial(self, vial: VialMove, raise_error=True):
        return vial.go_to_station(self, raise_error=raise_error)

    def stir(self, stir_time=None, stir_cmd="off", perturb_amount=STIR_PERTURB, move_sleep=3):
        """
        Operate CV elevator
        Args:
            stir_time: int, time (seconds) for stir plate to be on
            stir_cmd: command for stir plate; ONLY USED IF STIR_TIME IS NONE; must be 1 (on) or 0 (off), OR it must be
                'on' or 'off'.
            perturb_amount: float, amount to perturb vial during stirring
            move_sleep: float, time (seconds) for robot to sleep between stirring moves

        Returns: bool, True if stir action was a success
        """
        if stir_time:
            seconds = unit_conversion(stir_time, default_unit='s') if STIR else 5
            success = False
            success += send_arduino_cmd(self.arduino_name, 1) if STIR else True
            print(f"Stirring for {seconds} seconds...")
            start_time, end_time = time.time(), time.time()
            time.sleep(10)
            while (end_time - start_time) < seconds:
                # Move vial around stir plate center
                snapshot_move(perturbed_snapshot(self.location_snapshot, perturb_amount=perturb_amount, axis="x"))
                time.sleep(move_sleep)
                snapshot_move(perturbed_snapshot(self.location_snapshot, perturb_amount=perturb_amount, axis="y"))
                time.sleep(move_sleep)
                snapshot_move(perturbed_snapshot(self.location_snapshot, perturb_amount=-perturb_amount, axis="x"))
                time.sleep(move_sleep)
                snapshot_move(perturbed_snapshot(self.location_snapshot, perturb_amount=-perturb_amount, axis="y"))
                time.sleep(move_sleep)
                end_time = time.time()
            success += send_arduino_cmd(self.arduino_name, 0) if STIR else True
            return success

        # If stir_time not provided, default to implementing stir_cmd
        stir_cmd = 0 if stir_cmd == "off" or str(stir_cmd) == "0" else stir_cmd
        stir_cmd = 1 if stir_cmd == "on" or str(stir_cmd) == "1" else stir_cmd
        if stir_cmd not in [0, 1]:
            raise TypeError("Arg 'stir' must be 11 or 10, OR it must be 'up' or 'down'.")
        return send_arduino_cmd(self.arduino_name, stir_cmd)

    def perform_stir(self, vial: VialMove, stir_time=None, **kwargs):
        success = vial.go_to_station(self, **kwargs)
        success += self.stir(stir_time=stir_time)
        success += vial.leave_station(self)
        return success


class PotentiostatStation(StationStatus):
    def __init__(self, _id, raise_amount=0.028, **kwargs):
        super().__init__(_id=_id, **kwargs)
        self.current_experiment = self.get_prop("current_experiment") or None
        if not self.id:
            raise Exception("To operate a potentiostat, a potentiostat name must be provided.")
        if "potentiostat" not in self.id:
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.method, _, self.pot, self.p_channel = self.id.split("_")
        self.p_address = eval(f"POTENTIOSTAT_{self.pot}_ADDRESS")
        self.p_exe_path = eval(f"POTENTIOSTAT_{self.pot}_EXE_PATH")
        self.pot_model = self.p_exe_path.split("\\")[-1].split(".")[0]

        elevator = ELEVATOR_DICT.get(f"{self.pot}_{self.p_channel}")
        self.arduino_name = f"E{elevator:1d}"
        self.temp_arduino_name = f"T{elevator:1d}"
        self.raise_amount = raise_amount

    def update_experiment(self, experiment: str or None):
        """
        Get current experiment for instance with _id
        :param experiment: str or None, current experiment
        :return: experiment name
        """
        return self.coll.update_one({"_id": self.id}, {"$set": {"current_experiment": experiment}})

    def initiate_pot(self, vial: VialMove or str = None):
        if vial:
            vial = VialMove(_id=vial) if isinstance(vial, str) else vial
            if not vial.current_location == self.id:
                raise Exception(f"Vial {vial.id} is not currently located in potentiostat {self.id}. "
                                f"It is located at {vial.current_location}")
            if not self.current_content == vial.id:
                raise Exception(f"Potentiostat {self.id} does not currently contain vial {vial.id}. "
                                f"It contains {self.current_content}")

        if self.state == "up":
            return True
        elif self.state == "down":
            if self.move_elevator(endpoint="up"):
                time.sleep(5)
                return True

    def end_pot(self):
        if self.state == "down":
            return True
        elif self.state == "up":
            if self.move_elevator(endpoint="down"):
                return True

    def retrieve_vial(self, vial: VialMove, **move_kwargs):
        vial_id = vial if isinstance(vial, str) else vial.id
        if self.current_content != vial_id:
            raise Exception(f"Cannot retrieve vial {vial_id} from potentiostat {self.id}"
                            f"because vial {vial_id} is not located in this potentiostat")
        success = self.end_pot()
        success += get_place_vial(self.location_snapshot, action_type='get',
                                  pre_position_file=self.pre_location_snapshot,
                                  raise_amount=self.raise_amount, **move_kwargs)
        self.empty()
        return success

    def place_vial(self, vial: VialMove, raise_error=True, **move_kwargs):
        vial_id = vial if isinstance(vial, str) else vial.id
        if self.current_content == vial_id and vial.current_location == self.id:
            return True

        success = False
        if not vial.current_location == "robot_grip":
            success = vial.retrieve(raise_error=True)

        if self.available:
            # success = snapshot_move(SNAPSHOT_HOME)  # Start at home
            success += get_place_vial(self.location_snapshot, action_type='place',
                                      pre_position_file=self.pre_location_snapshot,
                                      raise_amount=self.raise_amount, raise_error=raise_error, **move_kwargs)
            # success += snapshot_move(SNAPSHOT_HOME)
            vial.update_position(self.id)
        else:
            success += False
            print(f"Station {self} not available.")

        if raise_error and not success:
            raise Exception(f"Vial {vial} was not successfully moved to {self}.")

        StationStatus("robot_grip").empty() if success else None
        return success

    def move_elevator(self, endpoint="down", raise_error=True):
        """
        Operate CV elevator
        Args:
            endpoint: endpoint for elevator; must be 1 (up) or 0 (down), OR it must be 'up' or 'down'.
            raise_error: bool, raise error if not successful and True

        Returns: bool, True if elevator action was a success
        """
        if MOVE_ELEVATORS:
            endpoint = 0 if endpoint == "down" or str(endpoint) == "0" else endpoint
            endpoint = 1 if endpoint == "up" or str(endpoint) == "1" else endpoint
            if endpoint not in [0, 1]:
                raise TypeError("Arg 'endpoint' must be 1 or 0, OR it must be 'up' or 'down'.")

            success = send_arduino_cmd(self.arduino_name, endpoint)
        else:
            success = True
            warnings.warn("Elevators NOT moving because MOVE_ELEVATORS is False")

        if success:
            self.update_state("up") if endpoint == 1 else self.update_state("down")
        if not success and raise_error:
            raise Exception(f"Potentiostat {self} elevator not successfully raised")
        return success

    def get_temperature(self):
        """
        Get temperature associated with this potentiostat station

        Returns: float, temperature (K)
        """

        arduino_result = send_arduino_cmd(self.temp_arduino_name, "", return_txt=True)
        if arduino_result:
            return {"value": float(arduino_result.split(":")[1].strip()) + 273.15, "unit": "K"}

    @staticmethod
    def generate_volts(voltage_sequence: str, volt_unit="V"):
        # Get voltages with appropriate units
        ureg = pint.UnitRegistry()
        voltages = voltage_sequence.split(',')
        voltage_units = ureg(voltages[-1]).units
        for i, v in enumerate(voltages):
            v_unit = "{}{}".format(v, voltage_units) if v.replace(".", "").replace("-", "").strip(
                " ").isnumeric() else v
            v_unit = ureg(v_unit)
            voltages[i] = v_unit.to(volt_unit).magnitude

        return voltages

    def generate_col_params(self, voltage_sequence: str, scan_rate: str, volt_unit="V", scan_unit="V/s"):
        # Get voltages with appropriate units
        voltages = self.generate_volts(voltage_sequence=voltage_sequence, volt_unit=volt_unit)

        # Get scan rate with appropriate units
        ureg = pint.UnitRegistry()
        scan_rate = ureg(scan_rate).to(scan_unit).magnitude
        return [dict(voltage=v, scan_rate=scan_rate) for v in voltages]


class CVPotentiostatStation(PotentiostatStation):
    def __init__(self, _id, raise_amount=0.028, **kwargs):
        super().__init__(_id=_id, raise_amount=raise_amount, **kwargs)

    def run_cv(self, data_path, voltage_sequence=None, scan_rate=None, resistance=0,
               sample_interval=None, sens=None, **kwargs):
        """
        Run CV experiment with potentiostat. Needs either collect_params arg OR voltage_sequence and scan_rage args.
        Args:
            data_path: str, output data file path
            voltage_sequence: str, comma-seperated list of voltage points
            scan_rate: str, scan rate
            resistance: float, solution resistance for iR compensation (A)
            sample_interval: float, potential increment (V)
            sens: float, current sensitivity (A/V)

        Returns: bool, success
        """
        sample_interval = unit_conversion(sample_interval or CV_SAMPLE_INTERVAL, default_unit="V")
        sens = unit_conversion(sens or CV_SENSITIVITY, default_unit="A/V")
        if not RUN_POTENT:
            print(
                f"CV is NOT running because RUN_POTENT is set to False. Observing the {POT_DELAY * 5} second CV_DELAY.")
            write_test(data_path, test_type="cv")
            time.sleep(POT_DELAY * 5)
            return True
        # Benchmark CV for voltage range
        print(f"RUN CV WITH {voltage_sequence} VOLTAGES AT {scan_rate} SCAN RATE WITH {resistance} SOLN RESISTANCE")
        if "EC" in self.pot_model:
            from potentiostat_kbio import CvExperiment, voltage_step
            # Set up CV parameters and KBIO CVExperiment object
            collect_params = self.generate_col_params(voltage_sequence, scan_rate)
            expt = CvExperiment([voltage_step(**p) for p in collect_params], record_every_de=sample_interval,
                                potentiostat_address=self.p_address, potentiostat_channel=int(self.p_channel),
                                exe_path=self.p_exe_path, run_iR=True, **kwargs)
            # Run CV and save data
            expt.run_experiment()
            time.sleep(TIME_AFTER_CV)
            expt.to_txt(data_path)
        elif "chi" in self.pot_model:
            if not resistance:
                warnings.warn("Warning. Resistance is 0 so IR compensation is not in use.")
            import hardpotato as hp
            # Set CV parameters
            out_folder = "/".join(data_path.split("\\")[:-1])
            f_name = data_path.split("\\")[-1].split(".")[0]
            volts = self.generate_volts(voltage_sequence=voltage_sequence, volt_unit="V")
            nSweeps = math.ceil((len(volts) - 2) / 2)
            print("N_SWEEPS: ", nSweeps)
            sr = unit_conversion(scan_rate, default_unit="V/s")

            # Install potentiostat and run CV
            hp.potentiostat.Setup(self.pot_model, self.p_exe_path, out_folder, port=self.p_address)
            cv = hp.potentiostat.CV(Eini=volts[0], Ev1=max(volts), Ev2=min(volts), Efin=volts[-1], sr=sr,
                                    nSweeps=nSweeps, dE=sample_interval, sens=sens,
                                    fileName=f_name, header="CV " + f_name, resistance=resistance * RCOMP_LEVEL)
            cv.run()
            time.sleep(TIME_AFTER_CV)
        else:
            raise Exception(f"CV not performed. No procedure for running a CV on {self.pot_model} model.")
        return True

    def run_ircomp_test(self, data_path, e_ini=0, low_freq=None, high_freq=None,
                        amplitude=None, sens=None):
        """
        Run iR comp test to determine resistance
        Args:
            data_path: str, output data file path
            e_ini: float, V, initial voltage
            low_freq: float, Hz, low frequency
            high_freq: float, Hz, high frequency
            amplitude: float, V, ac amplitude (half peak-to-peak)
            sens: float, current sensitivity (A/V)

        Returns: bool, success
        """
        if not RUN_POTENT:
            print(f"iR Comp Test is NOT running because RUN_POTENT is set to False. "
                  f"Observing the {POT_DELAY} second CV_DELAY.")
            write_test(data_path, test_type="iRComp")
            time.sleep(POT_DELAY)
            return True
        # Benchmark CV for voltage range
        print(f"RUN IR COMP TEST")
        if "chi" in self.pot_model:
            import hardpotato as hp
            # Set CV parameters
            out_folder = "/".join(data_path.split("\\")[:-1])
            f_name = data_path.split("\\")[-1].split(".")[0]

            # Install potentiostat and run CV
            hp.potentiostat.Setup(self.pot_model, self.p_exe_path, out_folder, port=self.p_address)
            eis = hp.potentiostat.EIS(Eini=e_ini, low_freq=low_freq or INITIAL_FREQUENCY,
                                      high_freq=high_freq or FINAL_FREQUENCY, amplitude=amplitude or AMPLITUDE,
                                      sens=sens or CV_SENSITIVITY, fileName=f_name, header="iRComp " + f_name)
            eis.run()

            # Load recently acquired data
            data = ParseChiESI(os.path.join(out_folder, f_name + ".txt"))
            time.sleep(TIME_AFTER_CV)

            print(data.resistance)
            return data.resistance


class CAPotentiostatStation(PotentiostatStation):
    def __init__(self, _id, raise_amount=0.028, **kwargs):
        super().__init__(_id=_id, raise_amount=raise_amount, **kwargs)

    def run_ca(self, data_path, voltage_sequence=None, si=None, pw=None, sens=None,
               steps=None, volt_min=MIN_CA_VOLT, volt_max=MAX_CA_VOLT, run_delay=CA_RUN_DELAY):
        """
        Run CA experiment with potentiostat. Needs either collect_params arg OR voltage_sequence arg.
        Args:
            data_path: str, output data file path
            voltage_sequence: str, comma-seperated list of voltage points
            si: float, sample interval (sec)
            pw: float, pulse width (sec)
            sens: float, current sensitivity (A/V)
            steps: float, number of steps
            volt_min: float, minimum acceptable voltage for CA experiment
            volt_max: float, maximum acceptable voltage for CA experiment
            run_delay: float, time to wait before running CA experiment (s)

        Returns: bool, success
        """
        si = unit_conversion(si or CA_SAMPLE_INTERVAL, default_unit="s")
        sens = unit_conversion(sens or CA_SENSITIVITY, default_unit="A/V")
        pw = unit_conversion(pw or CA_PULSE_WIDTH, default_unit="s")
        steps = steps or CA_STEPS

        if not RUN_POTENT:
            print(f"CV is NOT running because RUN_POTENT is set to False. Observing the {POT_DELAY} second CV_DELAY.")
            write_test(data_path, test_type="ca")
            time.sleep(POT_DELAY)
            return True
        # Benchmark CV for voltage range
        print(f"RUN CA WITH {voltage_sequence} VOLTAGES. Waiting {run_delay} sec before performing experiment...")
        time.sleep(run_delay)
        if "chi" in self.pot_model:
            import hardpotato as hp
            # Set CV parameters
            f_name = data_path.split("\\")[-1].split(".")[0]
            out_folder = "/".join(data_path.split("\\")[:-1])
            volts = self.generate_volts(voltage_sequence=voltage_sequence, volt_unit="V")
            max_volt = min((max(volts), volt_max)) if volt_max else max(volts)
            min_volt = max((min(volts), volt_min)) if volt_min else min(volts)

            # Install potentiostat and run CA
            hp.potentiostat.Setup(self.pot_model, self.p_exe_path, out_folder, port=self.p_address)
            ca = hp.potentiostat.CA(Eini=0, Ev1=max_volt, Ev2=min_volt, dE=si, nSweeps=steps, pw=pw,
                                    sens=sens, fileName=f_name, header="CA " + f_name)
            ca.run()
            time.sleep(TIME_AFTER_CV)
        else:
            raise Exception(f"CV not performed. No procedure for running a CV on {self.pot_model} model.")
        return True


def check_usb():
    # list connection ports
    for port, desc, hw_id in sorted(comports()):
        print("{}: {} [{}]".format(port, desc, hw_id))


def vial_col_test(col):
    snapshot_move(snapshot_file=SNAPSHOT_HOME)
    get_place_vial(VialMove(_id=col + "_04").home_snapshot, action_type='get', raise_error=True)
    get_place_vial(VialMove(_id=col + "_03").home_snapshot, action_type='place', raise_error=True)
    get_place_vial(VialMove(_id=col + "_03").home_snapshot, action_type='get', raise_error=True)
    get_place_vial(VialMove(_id=col + "_02").home_snapshot, action_type='place', raise_error=True)
    get_place_vial(VialMove(_id=col + "_02").home_snapshot, action_type='get', raise_error=True)
    get_place_vial(VialMove(_id=col + "_01").home_snapshot, action_type='place', raise_error=True)
    snapshot_move(snapshot_file=SNAPSHOT_HOME)


def reset_stations(end_home=False):
    snapshot_move(snapshot_file=SNAPSHOT_HOME)
    PotentiostatStation("cv_potentiostat_A_01").move_elevator(endpoint="down")
    PotentiostatStation("ca_potentiostat_B_01").move_elevator(endpoint="down")
    if end_home:
        snapshot_move(target_position=10)
        snapshot_move(snapshot_file=SNAPSHOT_END_HOME, target_position=10)


def flush_solvent(volume, vial_id="S_01", solv_id="solvent_01", go_home=True):
    vial = VialMove(_id=vial_id)
    solv_stat = LiquidStation(_id=solv_id)

    solv_stat.place_vial(vial)
    print("Actual Volume:  ", solv_stat.dispense_only(volume, dispense=True))

    if go_home:
        vial.leave_station(solv_stat)
        vial.place_home()


if __name__ == "__main__":
    test_vial = VialMove(_id="A_04")
    test_potent = PotentiostatStation("ca_potentiostat_B_01")  # cv_potentiostat_A_01, ca_potentiostat_B_01
    d_path = os.path.join(TEST_DATA_DIR, "PotentiostatStation_Test.csv")

    # vial_col_test("B")

    # test_potent.run_cv(d_path, voltage_sequence="0, 0.5, 0V", scan_rate=0.1)

    # reset_test_db()
    # reset_stations(end_home=False)
    # print(PotentiostatStation("ca_potentiostat_B_01").get_temperature())
    # snapshot_move(SNAPSHOT_END_HOME)

    # test_vial.retrieve()
    # test_vial.place_station(test_potent)
    # test_potent.move_elevator(endpoint="down")
    # test_potent.move_elevator(endpoint="up")
    # test_vial.place_home()

    # print(test_potent.get_temperature())

    # LiquidStation(_id="solvent_01").dispense_only(8)
    # flush_solvent(8, vial_id="S_04", solv_id="solvent_01", go_home=True)

    snapshot_move(SNAPSHOT_HOME)
    snapshot_move(SNAPSHOT_END_HOME)

    # StirHeatStation("stir_01").perform_stir(test_vial, stir_time=30)
