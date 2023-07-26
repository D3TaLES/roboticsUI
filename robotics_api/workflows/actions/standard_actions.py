import serial
import warnings
from serial.tools.list_ports import comports
from d3tales_api.Calculators.utils import unit_conversion
from robotics_api.workflows.actions.kinova_move import *
from robotics_api.workflows.actions.status_db_manipulations import *


def generate_abv_position(snapshot_file, raise_amount=RAISE_AMOUNT):
    with open(snapshot_file, 'r') as fn:
        master_data = json.load(fn)

    # Generate VialHomeAbv files
    new_height = master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["z"] + raise_amount
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"]["z"] = new_height
    with open(os.path.join(SNAPSHOT_DIR, "temp_abv.json"), "w+") as fn:
        json.dump(master_data, fn, indent=2)
    return os.path.join(SNAPSHOT_DIR, "temp_abv.json")


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
    snapshot_file_above = generate_abv_position(snapshot_file, raise_amount=raise_amount)

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
    snapshot_top = generate_abv_position(snapshot_start, raise_amount=0.02)
    if screw:
        success = snapshot_move(snapshot_top)
        snapshot_start = generate_abv_position(snapshot_start, raise_amount=0.0005)
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


def send_arduino_cmd(station, command, address=ARDUINO_ADDRESS):
    try:
        arduino = serial.Serial(address, 115200, timeout=.1)
    except:
        raise Exception("Warning! {} is not connected".format(address))
    time.sleep(1)  # give the connection a second to settle
    arduino.write(bytes(f"{station}_{command}", encoding='utf-8'))
    print("Command {} given to station {} at {} via Arduino.".format(command, station, address))
    while True:
        print("trying to read...")
        data = arduino.readline()
        print("waiting for {} arduino results...".format(station))
        if data:
            result_txt = str(data.rstrip(b'\n'))  # strip out the new lines for now\
            print("Arduino Result: ", result_txt)
            if "success" in result_txt:
                return True
        time.sleep(1)


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
            warnings.warn(f"Vial {self.id} location is listed as robot_grip, but robot grip current_content is "
                          f"listed as {StationStatus('robot_grip').current_content}.")
        elif self.robot_available():
            print("Robot is available")
            success = snapshot_move(SNAPSHOT_HOME)  # Start at home
            if self.current_location == "home":
                print("Retrieving vial from home...")
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
                success += get_place_vial(self.current_location, action_type='get', raise_error=raise_error, **move_kwargs)
            success += snapshot_move(SNAPSHOT_HOME)
            self.update_position("robot_grip")
        else:
            warnings.warn(f"Robot cannot retrieve {self.id} vial because robot is unavailable. The robot currently "
                          f"contains {StationStatus('robot_grip').current_content}.")
        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully retrieved. Vial {self.id} is located "
                            f"at {self.current_location}. ")
        return success

    def go_to_snapshot(self, target_location: str, raise_error=True, **move_kwargs):
        self.retrieve(raise_error=True)
        success = snapshot_move(SNAPSHOT_HOME)  # Start at home
        success += get_place_vial(target_location, action_type='place', release_vial=False,
                                  raise_error=raise_error, **move_kwargs)

        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully moved to {target_location}.")

        return success

    def place_snapshot(self, target_location: str, raise_error=True, **move_kwargs):
        self.retrieve(raise_error=True)
        success = snapshot_move(SNAPSHOT_HOME)  # Start at home
        success += get_place_vial(target_location, action_type='place',
                                  raise_error=raise_error, **move_kwargs)
        success += snapshot_move(SNAPSHOT_HOME)
        self.update_position(target_location)

        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully moved to {target_location}.")

        StationStatus("robot_grip").empty() if success else None
        return success

    def go_to_station(self, station: StationStatus, raise_error=True):
        self.retrieve(raise_error=True)

        success = False
        if station.available:
            success = snapshot_move(SNAPSHOT_HOME)  # Start at home
            success += get_place_vial(station.location_snapshot, action_type='place', release_vial=False,
                                      raise_error=raise_error, leave=False)
            station.update_available(False)

        if raise_error and not success:
            raise Exception(f"Vial {self} was not successfully moved to {station}.")

        return success

    def place_station(self, station: StationStatus, raise_error=True):
        return station.place_vial(self, raise_error=raise_error)

    @staticmethod
    def leave_station(station: StationStatus, raise_error=True):
        success = get_place_vial(station.location_snapshot, action_type='place', release_vial=False,
                                 raise_error=raise_error, go=False)
        station.update_available(True)
        return success

    def place_home(self, **kwargs):
        if self.current_location == "home":
            print(f"Vial {self} is already at home.")
            return True
        success = self.place_snapshot(self.home_snapshot, **kwargs)
        self.update_position("home")
        return success

    def cap(self, raise_error=CAPPED_ERROR):
        if self.capped:
            return True
        else:
            success = False  # TODO cap vial
            if success:
                self.update_capped(True)
                return True
        if raise_error:
            raise Exception(f"Vial {self.id} is not capped!")
        return success

    def uncap(self, raise_error=CAPPED_ERROR):
        if not self.capped:
            return True
        else:
            success = False  # TODO cap vial
            if success:
                self.update_capped(False)
                return True
        if raise_error:
            raise Exception(f"Vial {self.id} is still capped!")
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
    def __init__(self, _id, raise_amount=-0.03, **kwargs):
        super().__init__(_id=_id, **kwargs)
        if not self.id:
            raise Exception("To operate a solvent station, a solvent name must be provided.")
        if self.type != "solvent":
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.raise_amount = raise_amount
        self.blank_vial = SOLVENT_VIALS.get(self.id)
        self.pre_location_snapshot = None
        self.arduino_name = "L_{:02d}".format(int(self.id.split("_")[-1]))

    def place_vial(self, vial: VialMove, raise_error=True):
        return vial.go_to_station(self, raise_error=raise_error)

    def dispense(self, vial: VialMove, volume, raise_error=True):
        self.place_vial(vial, raise_error=raise_error)
        arduino_vol = unit_conversion(volume, default_unit="mL") * 1000  # send volume in micro liter
        send_arduino_cmd(self.arduino_name, arduino_vol)
        actual_volume = volume  # TODO get actual volume
        vial.leave_station(self, raise_error=raise_error)
        return actual_volume


class StirHeatStation(StationStatus):
    def __init__(self, _id, **kwargs):
        super().__init__(_id=_id, **kwargs)
        if not self.id:
            raise Exception("To operate the Stir-Heat station, a Stir-Heat name must be provided.")
        if self.type != "stir-heat":
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.pre_location_snapshot = None
        self.arduino_name = "S_{:02d}".format(int(self.id.split("_")[-1]))
        self.raise_amount = 0

    def place_vial(self, vial: VialMove, raise_error=True):
        return vial.go_to_station(self, raise_error=raise_error)

    def heat(self, temperature=None, temp_time=None, heat_cmd="off"):
        """
        Operate CV elevator
        Args:
            temperature: float; degree (Kelvin) for stir plate heating during stirring
            temp_time: float; duration (seconds) of heat
            heat_cmd: str; command for stir plate heating; ONLY USED IF STIR_TIME IS NONE; must be 1 (on) or 0 (off),
                OR it must be 'on' or 'off'.

        Returns: bool, True if stir action was a success
        """
        if temperature and temp_time:
            success = True  # TODO implement heating
            success = self.arduino_name
            return success
        elif temperature:
            heat_cmd = 3 if heat_cmd == "off" or str(heat_cmd) == "3" else heat_cmd
            heat_cmd = 4 if heat_cmd == "on" or str(heat_cmd) == "4" else heat_cmd
            return True
        return False

    def stir(self, stir_time=None, temperature=None, stir_cmd="off"):
        """
        Operate CV elevator
        Args:
            stir_time: int, time (seconds) for stir plate to be on
            temperature: float; degree (Kelvin) for stir plate heating during stirring
            stir_cmd: command for stir plate; ONLY USED IF STIR_TIME IS NONE; must be 1 (on) or 0 (off), OR it must be
                'on' or 'off'.

        Returns: bool, True if stir action was a success
        """
        if stir_time:
            seconds = unit_conversion(stir_time, default_unit='s')
            success = False
            success += self.heat(temperature, heat_cmd="on")
            success += send_arduino_cmd(self.arduino_name, 1)
            time.sleep(seconds)
            success += send_arduino_cmd(self.arduino_name, 0)
            success += self.heat(temperature, heat_cmd="off")
            return success

        # If stir_time not provided, default to implementing stir_cmd
        stir_cmd = 0 if stir_cmd == "off" or str(stir_cmd) == "0" else stir_cmd
        stir_cmd = 1 if stir_cmd == "on" or str(stir_cmd) == "1" else stir_cmd
        if stir_cmd not in [0, 1]:
            raise TypeError("Arg 'stir' must be 11 or 10, OR it must be 'up' or 'down'.")
        return send_arduino_cmd(self.arduino_name, stir_cmd)

    def perform_stir_heat(self, vial: VialMove, stir_time=None, temperature=None, temp_time=None, **kwargs):
        success = vial.go_to_station(self, **kwargs)
        if stir_time:
            success += self.stir(stir_time=stir_time, temperature=temperature)
        elif temp_time:
            success += self.heat(temperature=temperature, temp_time=temp_time)
        success += vial.leave_station(self)
        return success


class PotentiostatStation(StationStatus):
    def __init__(self, _id, raise_amount=0.028, **kwargs):
        super().__init__(_id=_id, **kwargs)
        if not self.id:
            raise Exception("To operate a potentiostat, a potentiostat name must be provided.")
        if "potentiostat" not in self.id:
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.potentiostat = self.id.split("_")[-2]
        self.p_channel = int(self.id.split("_")[-1])
        self.p_address = eval(f"POTENTIOSTAT_{self.potentiostat}_ADDRESS")
        self.arduino_name = f"E_{self.potentiostat}{self.p_channel:02d}"
        self.raise_amount = raise_amount

    def initiate_cv(self, vial: VialMove = None):
        if vial:
            if not vial.current_location == self.id:
                raise Exception(f"Vial {vial.id} is not currently located in potentiostat {self.id}.")
            if not self.current_content == vial.id:
                raise Exception(f"Potentiostat {self.id} does not currently contain vial {vial.id}.")

        if self.state == "up":
            return True
        elif self.state == "down":
            if self.move_elevator(endpoint="up"):
                time.sleep(5)
                return True

    def end_cv(self):
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
        success = self.end_cv()
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
            success = snapshot_move(SNAPSHOT_HOME)  # Start at home
            success += get_place_vial(self.location_snapshot, action_type='place',
                                      pre_position_file=self.pre_location_snapshot,
                                      raise_amount=self.raise_amount, raise_error=raise_error, **move_kwargs)
            success += snapshot_move(SNAPSHOT_HOME)
            vial.update_position(self.id)

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
        endpoint = 0 if endpoint == "down" or str(endpoint) == "0" else endpoint
        endpoint = 1 if endpoint == "up" or str(endpoint) == "1" else endpoint
        if endpoint not in [0, 1]:
            raise TypeError("Arg 'endpoint' must be 1 or 0, OR it must be 'up' or 'down'.")

        success = send_arduino_cmd(self.arduino_name, endpoint)
        if success:
            self.update_state("up") if endpoint == 1 else self.update_state("down")
        if not success and raise_error:
            raise Exception(f"Potentiostat {self} elevator not successfully raised")
        return success


def vial_col_test(col):
    snapshot_move(snapshot_file=SNAPSHOT_HOME)
    get_place_vial(VialMove(_id=col+"_04").home_snapshot, action_type='get', raise_error=True)
    get_place_vial(VialMove(_id=col+"_03").home_snapshot, action_type='place', raise_error=True)
    get_place_vial(VialMove(_id=col+"_03").home_snapshot, action_type='get', raise_error=True)
    get_place_vial(VialMove(_id=col+"_02").home_snapshot, action_type='place', raise_error=True)
    get_place_vial(VialMove(_id=col+"_02").home_snapshot, action_type='get', raise_error=True)
    get_place_vial(VialMove(_id=col+"_01").home_snapshot, action_type='place', raise_error=True)
    snapshot_move(snapshot_file=SNAPSHOT_HOME)


if __name__ == "__main__":

    # list connection ports
    for port, desc, hwid in sorted(comports()):
        print("{}: {} [{}]".format(port, desc, hwid))

    # VialMove(_id="A_04").place_station(PotentiostatStation("potentiostat_A_01"))
    # VialMove(_id="A_04").place_home()

    # PotentiostatStation("potentiostat_A_02").move_elevator(endpoint="up")
    # PotentiostatStation("potentiostat_A_02").move_elevator(endpoint="down")
    #
    snapshot_move(snapshot_file=SNAPSHOT_HOME)
    snapshot_move(snapshot_file=SNAPSHOT_END_HOME)
    # get_place_vial(VialMove(_id="A_02").home_snapshot, action_type='get', raise_error=True)
    # vial_col_test("C")
    # solv_station = LiquidStation(_id="solvent_01")
    # VialMove(_id="A_02").place_station(solv_station)
    # actual_volume = solv_station.dispense(2)
    # snapshot_move(os.path.join(SNAPSHOT_DIR, f"solvent_01.json"))

    # r = ReagentStatus(r_name="Acetonitrile")
    # VialMove(_id="B_04").add_reagent(r, amount="5cL", default_unit=VOLUME_UNIT)

    # snapshot_move(target_position=70)
    # snapshot_move(target_position=60)

    # send_arduino_cmd("E_A02", "0")

