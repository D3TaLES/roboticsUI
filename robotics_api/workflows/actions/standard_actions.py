import time
import serial
from serial.tools.list_ports import comports
from robotics_api.workflows.actions.snapshot_move import *
from robotics_api.workflows.actions.standard_variables import *


def vial_home(row, column, action_type="get"):
    """
    Function that executes an action getting or placing
    Args:
        row: str or int or float, row of vial home location, e.g., 04
        column: str, column of vial home location, e.g., A
        action_type: str, 'get' if the action is getting a vail, 'place' if action is placing the vial

    Returns: bool, success of action
    """
    snapshot_vial = os.path.join(SNAPSHOT_DIR, "VialHome_{}_{:02}.json".format(column, int(row)))
    snapshot_vial_above = os.path.join(SNAPSHOT_DIR, "VialHome_{}_{:02}_Abv.json".format(column, int(row)))

    # Start open if getting a vial
    success = snapshot_move(target_position='open') if action_type == "get" else True
    # Go to vial home
    success += snapshot_move(snapshot_vial_above)
    target = VIAL_GRIP_TARGET if action_type == "get" else 'open'
    success += snapshot_move(snapshot_vial, target_position=target)
    success += snapshot_move(snapshot_vial_above)

    return success


def cv_elevator(endpoint="down"):
    """
    Operate CV elevator
    :param endpoint: endpoint for elevator; must be 1 (up) or 0 (down), OR it must be 'up' or 'down'.
    :return: bool, True if elevator action was a success
    """
    endpoint = 0 if endpoint == "down" or str(endpoint) == "0" else endpoint
    endpoint = 1 if endpoint == "up" or str(endpoint) == "1" else endpoint
    if endpoint not in [0, 1]:
        raise TypeError("Arg 'direction' must be 1 or 0, OR it must be 'up' or 'down'.")

    arduino = serial.Serial(ELEVATOR_ADDRESS, 115200, timeout=.1)
    time.sleep(1)  # give the connection a second to settle
    arduino.write(bytes(str(endpoint), encoding='utf-8'))
    while True:
        data = arduino.readline()
        print("waiting for data...")
        if data:
            result_txt = str(data.rstrip(b'\n'))  # strip out the new lines for now\
            print("CV Elevator Result: ", result_txt)
            return True if "success" in result_txt else False
        time.sleep(1)


if __name__ == "__main__":

    # list connection ports
    for port, desc, hwid in sorted(comports()):
        print("{}: {} [{}]".format(port, desc, hwid))

    cv_elevator(endpoint="up")
