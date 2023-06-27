import serial
import warnings
from serial.tools.list_ports import comports
from robotics_api.standard_variables import *
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


def get_place_vial(snapshot_file, action_type="get", pre_position_file=None, raise_amount=RAISE_AMOUNT):
    """
    Function that executes an action getting or placing
    Args:
        snapshot_file: str, path to snapshot file
        action_type: str, 'get' if the action is getting a vail, 'place' if action is placing the vial
        pre_position_file: str, path to snapshot file for teh position that should be touched before and after
            placing/retrieving the vial

    Returns: bool, success of action
    """
    print(snapshot_file)
    snapshot_file_above = generate_abv_position(snapshot_file, raise_amount=raise_amount)

    # Start open if getting a vial
    success = snapshot_move(target_position='open') if action_type == "get" else True

    # If pre-position, go there
    if pre_position_file:
        success += snapshot_move(pre_position_file)
    # Go to vial position
    success += snapshot_move(snapshot_file_above)
    target = VIAL_GRIP_TARGET if action_type == "get" else 'open'
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
    success += snapshot_move(target_position=VIAL_GRIP_TARGET+4)

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


def cv_elevator(endpoint="down"):
    """
    Operate CV elevator
    :param endpoint: endpoint for elevator; must be 1 (up) or 0 (down), OR it must be 'up' or 'down'.
    :return: bool, True if elevator action was a success
    """
    endpoint = 0 if endpoint == "down" or str(endpoint) == "0" else endpoint
    endpoint = 1 if endpoint == "up" or str(endpoint) == "1" else endpoint
    if endpoint not in [0, 1]:
        raise TypeError("Arg 'endpoint' must be 1 or 0, OR it must be 'up' or 'down'.")

    return send_arduino_cmd(endpoint, ELEVATOR_ADDRESS)


def stir_plate(stir_time=None, temperature=None, stir_cmd="off"):
    """
    Operate CV elevator
    :param stir_time: int, time (seconds) for stir plate to be on
    :param temperature: float; degree (Kelvin) for stir plate heating during stirring     
    :param stir_cmd: command for stir plate; ONLY USED IF STIR_TIME IS NONE; must be 1 (on) or 0 (off), OR it must be 'on' or 'off'.
    
    :return: bool, True if stir action was a success
    """
    if stir_time:
        success = False
        if temperature:
            success += True  # TODO implement heating
        success += send_arduino_cmd(4, STIR_PLATE_ADDRESS)
        time.sleep(stir_time)
        success += send_arduino_cmd(3, STIR_PLATE_ADDRESS)
        return success

    # If stir_time not provided, default to implementing stir_cmd
    stir_cmd = 3 if stir_cmd == "off" or str(stir_cmd) == "3" else stir_cmd
    stir_cmd = 4 if stir_cmd == "on" or str(stir_cmd) == "4" else stir_cmd
    if stir_cmd not in [3, 4]:
        raise TypeError("Arg 'stir' must be 11 or 10, OR it must be 'up' or 'down'.")
    return send_arduino_cmd(stir_cmd, STIR_PLATE_ADDRESS)


def move_vial_to_potentiostat(potentiostat: str):
    # Move vial to potentiostat elevator
    success = True
    # TODO enable multiple potentiostats
    pot_location = os.path.join(SNAPSHOT_DIR, "Potentiostat.json")
    pre_pot_location = os.path.join(SNAPSHOT_DIR, "Pre_potentiostat.json")
    success += snapshot_move(SNAPSHOT_HOME)
    success += get_place_vial(pot_location, action_type="place", pre_position_file=pre_pot_location, raise_amount=0.028)
    success += snapshot_move(SNAPSHOT_HOME)
    success += cv_elevator(endpoint="up")
    time.sleep(5)
    return success


def retrieve_vial_from_potentiostat(potentiostat: str):
    # Move vial to potentiostat elevator
    success = True
    # TODO enable multiple potentiostats
    pot_location = os.path.join(SNAPSHOT_DIR, "Potentiostat.json")
    pre_pot_location = os.path.join(SNAPSHOT_DIR, "Pre_potentiostat.json")
    success += cv_elevator(endpoint="down")
    success += get_place_vial(pot_location, action_type="get", pre_position_file=pre_pot_location, raise_amount=0.028)
    success += snapshot_move(SNAPSHOT_HOME)
    return success


def check_robot():
    return StationStatus("robot_grip").available


class VialMove(VialStatus):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            raise Exception("To move a vial, a vial ID or reagent UUID or experiment name must be provided.")

    def retrieve(self, throw_error=False):
        success = False
        if self.current_location == "robot_grip":
            if StationStatus("robot_grip").current_content == self.id:
                return True
            warnings.warn(f"Vial {self.id} location is listed as robot_grip, but robot grip current_content is "
                          f"listed as {StationStatus('robot_grip').current_content}.")
        elif "potentiostat" in self.current_location:
            if check_robot():
                success = snapshot_move(SNAPSHOT_HOME)  # Start at home
                success += retrieve_vial_from_potentiostat(self.current_location)
                self.update_position("robot_grip")
        else:
            if check_robot():
                success = snapshot_move(SNAPSHOT_HOME)  # Start at home
                success += get_place_vial(self.current_location, action_type='place')
                self.update_position("robot_grip")
        if throw_error and not success:
            raise Exception(f"Vial {self.id} was not successfully retrieved.")
        return success

    def place(self, target_location, throw_error=False):
        success = False
        target_location = self.home_snapshot if target_location == "home" else target_location
        if not self.current_location == "robot_grip":
            self.retrieve(throw_error=True)
        if "potentiostat" in target_location:
            if check_robot():
                success = snapshot_move(SNAPSHOT_HOME)  # Start at home
                success += move_vial_to_potentiostat(target_location)
                self.update_position(target_location)
        else:
            if check_robot():
                success = snapshot_move(SNAPSHOT_HOME)  # Start at home
                success += get_place_vial(target_location, action_type='get')
                self.update_position(target_location)
        if throw_error and not success:
            raise Exception(f"Vial {self.id} was not successfully moved to {target_location}.")

        return success

    def cap(self):
        if self.capped:
            return True
        else:
            success = False  # TODO cap vial
            if success:
                self.update_capped(True)
                return True

    def uncap(self):
        if not self.capped:
            return True
        else:
            success = False  # TODO cap vial
            if success:
                self.update_capped(False)
                return True

    def update_position(self, position):
        self.update_location(position)
        StationStatus(position).update_content(self.id)


if __name__ == "__main__":

    # list connection ports
    for port, desc, hwid in sorted(comports()):
        print("{}: {} [{}]".format(port, desc, hwid))

    # stir_plate(stir_time=10)

    # screw_lid(screw=False)
    # screw_lid(screw=True)
    # snapshot_move(os.path.join(SNAPSHOT_DIR, "Pre_potentiostat.json"), target_position=VIAL_GRIP_TARGET)
    # snapshot_move(os.path.join(SNAPSHOT_DIR, "Potentiostat.json"), target_position='open')
    # snapshot_move(os.path.join(SNAPSHOT_DIR, "Pre_potentiostat.json"), target_position=VIAL_GRIP_TARGET)
    #
    # snapshot_move(SNAPSHOT_HOME)
    # vial_home("4", "C", action_type='get')
    # snapshot_move(SNAPSHOT_HOME)
    #
    # pot_location = os.path.join(SNAPSHOT_DIR, "Potentiostat.json")
    # pre_pot_location = os.path.join(SNAPSHOT_DIR, "Pre_potentiostat.json")
    # get_place_vial(pot_location, action_type="place", pre_position_file=pre_pot_location, raise_amount=0.028)
    # snapshot_move(SNAPSHOT_HOME)
    #
    cv_elevator(endpoint="up")
    cv_elevator(endpoint="down")
    #
    # get_place_vial(pot_location, action_type="get", pre_position_file=pre_pot_location, raise_amount=0.028)
    # snapshot_move(SNAPSHOT_HOME)
    # vial_home("4", "C", action_type='place')
    # snapshot_move(SNAPSHOT_HOME)


    # snapshot_move(SNAPSHOT_END_HOME)
