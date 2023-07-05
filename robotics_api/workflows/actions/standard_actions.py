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


def get_place_vial(snapshot_file, action_type="get", pre_position_file=None, raise_amount=RAISE_AMOUNT, release_vial=True):
    """
    Function that executes an action getting or placing
    Args:
        snapshot_file: str, path to snapshot file
        action_type: str, 'get' if the action is getting a vail, 'place' if action is placing the vial
        pre_position_file: str, path to snapshot file for teh position that should be touched before and after
            placing/retrieving the vial
        raise_amount: float,
        release_vial: bool,
    Returns: bool, success of action
    """
    snapshot_file_above = generate_abv_position(snapshot_file, raise_amount=raise_amount)

    # Start open if getting a vial
    success = snapshot_move(target_position='open') if action_type == "get" else True

    # If pre-position, go there
    if pre_position_file:
        success += snapshot_move(pre_position_file)
    # Go to vial position
    success += snapshot_move(snapshot_file_above)
    target = VIAL_GRIP_TARGET if action_type == "get" else 'open' if release_vial else VIAL_GRIP_TARGET
    success += snapshot_move(snapshot_file, target_position=target)
    success += snapshot_move(snapshot_file_above)
    # If pre-position, go there
    if pre_position_file:
        success += snapshot_move(pre_position_file)

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


def send_arduino_cmd(command, address=ARDUINO_DEFAULT_ADDRESS):
    try:
        arduino = serial.Serial(address, 115200, timeout=.1)
    except:
        warnings.warn("Warning! {} is not connected".format(address))
        return False
    time.sleep(1)  # give the connection a second to settle
    arduino.write(bytes(str(command), encoding='utf-8'))
    print("Command {} given to {} via Arduino.".format(command, address))
    while True:
        print("trying to read...")
        data = arduino.readline()
        print("waiting for arduino results...")
        if data:
            result_txt = str(data.rstrip(b'\n'))  # strip out the new lines for now\
            print("Arduino Result: ", result_txt)
            return True if "success" in result_txt else False
        time.sleep(1)


class VialMove(VialStatus):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            raise Exception("To move a vial, a vial ID or reagent UUID or experiment name must be provided.")

    def retrieve(self, raise_error=False):
        success = False
        print("current_location", self.current_location)
        print("robot c", StationStatus("robot_grip").current_content)
        print("vial", self.id)
        if self.current_location == "robot_grip":
            if StationStatus("robot_grip").current_content == self.id:
                return True
            warnings.warn(f"Vial {self.id} location is listed as robot_grip, but robot grip current_content is "
                          f"listed as {StationStatus('robot_grip').current_content}.")
        elif self.robot_available():
            print("Robot is available")
            success = snapshot_move(SNAPSHOT_HOME)  # Start at home
            if self.current_location == "home":
                success += get_place_vial(self.home_snapshot, action_type='get')
            elif "potentiostat" in self.current_location:
                station = PotentiostatStation(self.current_location)
                success += station.retrieve_vial(self)
            elif "solvent" in self.current_location:
                station = SolventStation(self.current_location)
                success += station.retrieve_vial(self)
            else:
                success += get_place_vial(self.current_location, action_type='get')
            success += snapshot_move(SNAPSHOT_HOME)
            print("success: ", success)
            self.update_position("robot_grip")
        else:
            print(self.current_location)
            warnings.warn(f"Robot cannot retrieve {self.id} vial because robot is unavailable. The robot currently "
                          f"contains {StationStatus('robot_grip').current_content}.")
        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully retrieved. Vial {self.id} is located "
                            f"at {self.current_location}. ")
        return success

    def go_to_snapshot(self, target_location: str, raise_error=False, raise_amount=RAISE_AMOUNT):
        if not self.current_location == "robot_grip":
            self.retrieve(raise_error=True)
        success = snapshot_move(SNAPSHOT_HOME)  # Start at home
        success += get_place_vial(target_location, action_type='place', release_vial=False, raise_amount=raise_amount)

        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully moved to {target_location}.")

        return success

    def place_snapshot(self, target_location: str, raise_error=False, raise_amount=RAISE_AMOUNT):
        if not self.current_location == "robot_grip":
            self.retrieve(raise_error=True)
        success = snapshot_move(SNAPSHOT_HOME)  # Start at home
        success += get_place_vial(target_location, action_type='place', raise_amount=raise_amount)
        success += snapshot_move(SNAPSHOT_HOME)
        self.update_position(target_location)

        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully moved to {target_location}.")

        StationStatus("robot_grip").empty() if success else None
        return success

    def go_to_station(self, station: StationStatus, raise_error=False):
        vial_id = self if isinstance(self, str) else self.id
        if station.current_content == vial_id and self.current_location == station.id:
            return True

        success = False
        if not self.current_location == "robot_grip":
            success = self.retrieve(raise_error=True)

        if station.available:
            success = snapshot_move(SNAPSHOT_HOME)  # Start at home
            success += self.go_to_snapshot(station.location_snapshot, raise_amount=station.raise_amount)

        if raise_error and not success:
            raise Exception(f"Vial {self} was not successfully moved to {station}.")

        return success

    def place_station(self, station: StationStatus, raise_error=False):
        return station.place_vial(self, raise_error=raise_error)

    def place_home(self, **kwargs):
        if self.current_location == "home":
            print(f"Vial {self} is already at home.")
            return True
        success = self.place_snapshot(self.home_snapshot, **kwargs)
        self.update_position("home")
        return success

    def cap(self, raise_error=False):
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

    def uncap(self, raise_error=False):
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
        station.update_content(self.id)
        station.update_available(False)
        print(f"Successfully updated vial {self} to position {position}")

    @staticmethod
    def robot_available():
        return StationStatus("robot_grip").available


class SolventStation(StationStatus):
    def __init__(self, _id, raise_amount=-0.03, **kwargs):
        super().__init__(_id=_id, **kwargs)
        if not self.id:
            raise Exception("To operate a solvent station, a solvent name must be provided.")
        if self.type != "solvent":
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.raise_amount = raise_amount
        self.blank_vial = SOLVENT_VIALS.get(self.id)
        self.pre_location_snapshot = None

    def retrieve_vial(self, vial: VialMove, **kwargs):
        vial_id = vial if isinstance(vial, str) else vial.id
        if self.current_content != vial_id:
            raise Exception(f"Cannot retrieve vial {vial_id} from solvent dispenser {self.id}"
                            f"because vial {vial_id} is not located in this solvent dispenser")
        success = get_place_vial(self.location_snapshot, action_type='get',
                                 pre_position_file=self.pre_location_snapshot,
                                 raise_amount=self.raise_amount)
        self.empty()
        return success

    def place_vial(self, vial: VialMove, raise_error=False):
        return vial.go_to_station(self, raise_error=raise_error)

    def dispense(self, volume):
        self.update_available(False)
        # TODO figure out solvent stuff
        actual_volume = volume
        self.update_available(True)
        return actual_volume


class StirHeatStation(StationStatus):
    def __init__(self, _id, **kwargs):
        super().__init__(_id=_id, **kwargs)
        if not self.id:
            raise Exception("To operate the Stir-Heat station, a Stir-Heat name must be provided.")
        if self.type != "stir-heat":
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.pre_location_snapshot = None
        self.plate_address = eval("STIR_PLATE_{:02d}_ADDRESS".format(int(self.id.split("_")[-1])))

    def place_vial(self, vial: VialMove, raise_error=False):
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
            cmd = self.plate_address
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
            success += send_arduino_cmd(4, self.plate_address)
            time.sleep(seconds)
            success += send_arduino_cmd(3, self.plate_address)
            success += self.heat(temperature, heat_cmd="off")
            return success

        # If stir_time not provided, default to implementing stir_cmd
        stir_cmd = 3 if stir_cmd == "off" or str(stir_cmd) == "3" else stir_cmd
        stir_cmd = 4 if stir_cmd == "on" or str(stir_cmd) == "4" else stir_cmd
        if stir_cmd not in [3, 4]:
            raise TypeError("Arg 'stir' must be 11 or 10, OR it must be 'up' or 'down'.")
        return send_arduino_cmd(stir_cmd, self.plate_address)

    def perform_stir_heat(self, vial: VialMove, stir_time=None, temperature=None, temp_time=None, **kwargs):
        self.update_available(False)
        print(self)
        print(self.location_snapshot)
        success = vial.go_to_station(self, **kwargs)
        if stir_time:
            success += self.stir(stir_time=stir_time, temperature=temperature)
        elif temp_time:
            success += self.heat(temperature=temperature, temp_time=temp_time)
        success += snapshot_move(SNAPSHOT_HOME)
        self.update_available(True)
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
        self.elevator_address = eval(f"ELEVATOR_{self.potentiostat}_{self.p_channel:02d}_ADDRESS")
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
                self.update_state("up")
                time.sleep(5)
                return True

    def end_cv(self):
        if self.state == "down":
            return True
        elif self.state == "up":
            if self.move_elevator(endpoint="down"):
                self.update_state("down")
                return True

    def retrieve_vial(self, vial: VialMove, **kwargs):
        vial_id = vial if isinstance(vial, str) else vial.id
        if self.current_content != vial_id:
            raise Exception(f"Cannot retrieve vial {vial_id} from potentiostat {self.id}"
                            f"because vial {vial_id} is not located in this potentiostat")
        success = self.end_cv()
        success += get_place_vial(self.location_snapshot, action_type='get',
                                  pre_position_file=self.pre_location_snapshot,
                                  raise_amount=self.raise_amount)
        self.empty()
        return success

    def place_vial(self, vial: VialMove, raise_error=False):
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
                                      raise_amount=self.raise_amount)
            success += snapshot_move(SNAPSHOT_HOME)
            vial.update_position(self.id)

        if raise_error and not success:
            raise Exception(f"Vial {vial} was not successfully moved to {self}.")

        StationStatus("robot_grip").empty() if success else None
        return success

    def move_elevator(self, endpoint="down"):
        """
        Operate CV elevator
        :param endpoint: endpoint for elevator; must be 1 (up) or 0 (down), OR it must be 'up' or 'down'.
        :return: bool, True if elevator action was a success
        """
        endpoint = 0 if endpoint == "down" or str(endpoint) == "0" else endpoint
        endpoint = 1 if endpoint == "up" or str(endpoint) == "1" else endpoint
        if endpoint not in [0, 1]:
            raise TypeError("Arg 'endpoint' must be 1 or 0, OR it must be 'up' or 'down'.")

        return send_arduino_cmd(endpoint, self.elevator_address)


if __name__ == "__main__":

    # list connection ports
    for port, desc, hwid in sorted(comports()):
        print("{}: {} [{}]".format(port, desc, hwid))

    # VialMove(_id="A_04").place_station(PotentiostatStation("potentiostat_A_01"))

    # PotentiostatStation("potentiostat_A_01").move_elevator(endpoint="up")
    PotentiostatStation("potentiostat_A_01").move_elevator(endpoint="down")
    #
    # snapshot_move(SNAPSHOT_HOME)
    # snapshot_move(SNAPSHOT_END_HOME)
    # snapshot_move(os.path.join(SNAPSHOT_DIR, "pre_potentiostat_A_01.json"))

    # r = ReagentStatus(r_name="Acetonitrile")
    # VialMove(_id="B_04").add_reagent(r, amount="5cL", default_unit=VOLUME_UNIT)

