import sys
import json
import time
import serial
import warnings
import threading
from argparse import Namespace

from d3tales_api.Calculators.utils import dict2obj
from kortex_api.autogen.messages import Base_pb2
from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient

from robotics_api.settings import *
from robotics_api.utils import kinova_utils as utilities
from robotics_api.utils.kinova_gripper import GripperMove

# Maximum allowed waiting time during actions (in seconds)
TIMEOUT_DURATION = 20
VERBOSE = 1
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../fireworks"))


# Create closure to set an event after an END or an ABORT
def check_for_end_or_abort(e):
    """
    Return a closure checking for END or ABORT notifications

    Arguments:
        e: event to signal when the action is completed (will be set when an END or ABORT occurs)

    """

    def check(notification, e=e):
        if VERBOSE > 3:
            print("EVENT : " + Base_pb2.ActionEvent.Name(notification.action_event))
        if notification.action_event == Base_pb2.ACTION_END or notification.action_event == Base_pb2.ACTION_ABORT:
            e.set()

    return check


def check_for_sequence_end_or_abort(e):
    """
    Return a closure checking for END or ABORT notifications on a sequence

    Arguments:
        e:  event to signal when the action is completed (will be set when an END or ABORT occurs)
    """

    def check(notification, e=e):
        event_id = notification.event_identifier
        task_id = notification.task_index
        if event_id == Base_pb2.SEQUENCE_TASK_COMPLETED:
            if VERBOSE > 3:
                print("Sequence task {} completed".format(task_id))
        elif event_id == Base_pb2.SEQUENCE_ABORTED:
            if VERBOSE > 3:
                print("Sequence aborted with error {}:{}".format(
                    notification.abort_details, Base_pb2.SubErrorCodes.Name(notification.abort_details)))
            e.set()
        elif event_id == Base_pb2.SEQUENCE_COMPLETED:
            if VERBOSE > 3:
                print("Sequence completed.")
            e.set()

    return check


def snapshot_move_angular(base, joint_angle_values):
    if VERBOSE > 3:
        print("Starting angular action movement ...")
    action = Base_pb2.Action()
    action.name = "Example angular action movement"
    action.application_data = ""

    # might be better to use this instead of len(joint_angle_values) for following conditional
    actuator_count = base.GetActuatorCount()

    # Place arm according to joint angle values in JSON
    for joint_id in range(len(joint_angle_values)):
        joint_angle = action.reach_joint_angles.joint_angles.joint_angles.add()
        joint_angle.joint_identifier = joint_id
        joint_angle.value = joint_angle_values[joint_id]["value"]

    e = threading.Event()
    notification_handle = base.OnNotificationActionTopic(
        check_for_end_or_abort(e),
        Base_pb2.NotificationOptions()
    )

    if VERBOSE > 3:
        print("Executing action")
    base.ExecuteAction(action)

    if VERBOSE > 3:
        print("Waiting for movement to finish ...")
    finished = e.wait(TIMEOUT_DURATION)
    base.Unsubscribe(notification_handle)

    if finished:
        if VERBOSE > 3:
            print("Angular movement completed")
    else:
        if VERBOSE > 3:
            print("Timeout on action notification wait")
    return finished


def snapshot_move_cartesian(base, coordinate_values):
    if VERBOSE > 3:
        print("Starting Cartesian action movement ...")
    action = Base_pb2.Action()
    action.name = "Example Cartesian action movement"
    action.application_data = ""

    cartesian_pose = action.reach_pose.target_pose
    cartesian_pose.x = coordinate_values["x"]  # (meters)
    cartesian_pose.y = coordinate_values["y"]  # (meters)
    cartesian_pose.z = coordinate_values["z"]  # (meters)
    cartesian_pose.theta_x = coordinate_values["thetaX"]  # (degrees)
    cartesian_pose.theta_y = coordinate_values["thetaY"]  # (degrees)
    cartesian_pose.theta_z = coordinate_values["thetaZ"]  # (degrees)

    e = threading.Event()
    notification_handle = base.OnNotificationActionTopic(
        check_for_end_or_abort(e),
        Base_pb2.NotificationOptions()
    )

    if VERBOSE > 3:
        print("Executing action")
    base.ExecuteAction(action)

    if VERBOSE > 3:
        print("Waiting for movement to finish ...")
    finished = e.wait(TIMEOUT_DURATION)
    base.Unsubscribe(notification_handle)

    if finished:
        if VERBOSE > 1:
            print("Cartesian movement completed")
    else:
        if VERBOSE > 1:
            print("Timeout on action notification wait")
    return finished


def move_gripper(target_position=None):
    """
    Move gripper
    :param target_position: target position for the gripper: open, closed, or percentage closed (e.g., 90)
    :return: bool, True if action a success
    """
    # Import the utilities' helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../fireworks"))
    finished = True

    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create connection to the device and get therouter
        with utilities.DeviceConnection.createUdpConnection(connector) as router_real_time:
            action = GripperMove(router, router_real_time, 2)

            if target_position == 'open':
                if VERBOSE > 2:
                    print("Moving gripper open...")
                finished += action.gripper_move(OPEN_GRIP_TARGET)
                action.cleanup()
            elif target_position == 'closed':
                if VERBOSE > 2:
                    print("Moving gripper closed...")
                finished += action.gripper_move(90)
                action.cleanup()
            elif target_position:
                if VERBOSE > 2:
                    print("Moving gripper to {}...".format(target_position))
                finished += action.gripper_move(target_position)
                action.cleanup()

    print("Gripper movement successfully executed!" if finished else "Error! Gripper was not successfully moved.")
    return finished


def snapshot_move(snapshot_file=None, target_position=None, raise_error=True,
                  angle_error=0.2, position_error=0.1):
    """

    :param snapshot_file: str, path to snapshot file (JSON)
    :param target_position: target position for the gripper: open, closed, or percentage closed (e.g., 90)
    :return: bool, True if movement was a success
    """
    if not RUN_ROBOT:
        warnings.warn("Robot NOT run because RUN_ROBOT is set to False.")
        return True

    # Import the utilities' helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../fireworks"))
    finished = True

    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create required services
        base = BaseClient(router)

        if snapshot_file:
            # loads file
            snapshot_file = open(snapshot_file, 'r')

            # converts JSON to nested dictionary
            snapshot_file.dict = json.load(snapshot_file)

            if "jointAnglesGroup" in snapshot_file.dict:
                # grabs the list of joint angle values
                joint_angle_values = \
                    snapshot_file.dict["jointAnglesGroup"]["jointAngles"][0]["reachJointAngles"]["jointAngles"][
                        "jointAngles"]
                move_type = "angular"
            elif "poses" in snapshot_file.dict:
                # grabs the dictionary of coordinate values
                coordinate_values = snapshot_file.dict["poses"]["pose"][0]["reachPose"]["targetPose"]
                move_type = "cartesian"
            else:
                print("invalid file type")
                move_type = "null"

            # Move Robot
            if move_type == "angular":
                finished = snapshot_move_angular(base, joint_angle_values)
            elif move_type == "cartesian":
                finished = snapshot_move_cartesian(base, coordinate_values)
            else:
                finished = True
                if VERBOSE > 3:
                    print("... and nothing happened")
            snapshot_file.close()

            if finished:
                if move_type == "angular":
                    current_joint_angles_raw = base.GetMeasuredJointAngles()  # Assuming this method exists
                    def _angle(a):
                        return a if a < 360 else a-360
                    current_joint_angles = {i.joint_identifier: _angle(i.value) for i in current_joint_angles_raw.joint_angles}
                    joint_angle_values_dict = {i["jointIdentifier"]: i["value"] for i in joint_angle_values}
                    angle_diffs = [abs(current_joint_angles.get(k, 0) - joint_angle_values_dict.get(k, 0)) for k in joint_angle_values_dict]
                    if not all([d < angle_error for d in angle_diffs]):
                        error_diffs = [d for d in angle_diffs if d > angle_error]
                        if not all([abs(d-360) < angle_error for d in error_diffs]):
                            finished = False
                            if raise_error:
                                raise SystemError("Error: Robot did not reach the desired joint angles: ", angle_diffs)
                elif move_type == "cartesian":
                    current_pose_raw = base.GetMeasuredCartesianPose()  # Assuming this method exists
                    current_pose = {"x": current_pose_raw.x, "y": current_pose_raw.y, "z": current_pose_raw.z,
                                    "thetaX": current_pose_raw.theta_x, "thetaY": current_pose_raw.theta_y, "thetaZ": current_pose_raw.theta_z}
                    pose_diffs = [abs(current_pose.get(k, 0) - coordinate_values.get(k, 0)) for k in coordinate_values]
                    if not all([d < position_error for d in pose_diffs]):
                        if raise_error:
                            raise SystemError("Error: Robot did not reach the desired Cartesian pose: ", pose_diffs)
                        finished = False
                else:

                    if raise_error:
                        raise SystemError("Error: Unknown move type for confirmation.")
                    finished = False

    if target_position:
        move_gripper(target_position)

    print("Snapshot successfully executed!" if finished else "Error! Snapshot was not successfully executed.")
    return finished


def sequence_move(sequence_file):
    # Import the utilities' helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../fireworks"))
    finished = True

    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create required services
        base = BaseClient(router)

        # loads file
        sequence_file = open(sequence_file, 'r')
        # converts JSON to nested dictionary
        sequence_file.dict = json.load(sequence_file)
        sequence = dict2obj(sequence_file.dict["sequences"]["sequence"][0], master_obj=Base_pb2.Sequence)
        print(dir(sequence.tasks))
        sequence_file.close()

        e = threading.Event()
        notification_handle = base.OnNotificationSequenceInfoTopic(
            check_for_sequence_end_or_abort(e),
            Base_pb2.NotificationOptions()
        )

        print("Creating sequence on device and executing it")
        handle_sequence = base.CreateSequence(sequence)
        base.PlaySequence(handle_sequence)

        if VERBOSE > 3:
            print("Waiting for movement to finish ...")
        finished = e.wait(TIMEOUT_DURATION)
        base.Unsubscribe(notification_handle)

    if not finished:
        print("Timeout on action notification wait")
    return finished

    # Iterate through tasks
    # tasks = sequence_file.dict["sequences"]["sequence"][0]["tasks"]
    # print(tasks)
    # for task in tasks:
    #     if "reachJointAngles" in task["action"]:
    #         # grabs the list of joint angle values
    #         joint_angle_values = task["action"]["reachJointAngles"]["jointAngles"]["jointAngles"]
    #         # Move Robot
    #         finished += snapshot_move_angular(base, joint_angle_values)
    #     elif "reachPose" in task["action"]:
    #         # grabs the dictionary of coordinate values
    #         coordinate_values = task["action"]["reachPose"]["targetPose"]
    #         # Move Robot
    #         finished += snapshot_move_cartesian(base, coordinate_values)
    #     elif "sendGripperCommand" in task["action"]:
    #         # grabs the dictionary of coordinate values
    #         gripper_value = task["action"]["sendGripperCommand"]["gripper"]["finger"]["value"]
    #         # Move Robot
    #         finished += move_gripper(gripper_value)
    #     else:
    #         print("invalid action type")
    #
    # sequence_file.close()
    #
    # print("Snapshot successfully executed!" if finished else "Error! Snapshot was not successfully executed.")
    # return finished


def twist_hand(linear_x=0, linear_y=0, linear_z=0,
               angular_x=0, angular_y=0, angular_z=0):
    # Import the utilities' helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../fireworks"))
    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create required services
        base = BaseClient(router)

        command = Base_pb2.TwistCommand()
        command.reference_frame = Base_pb2.CARTESIAN_REFERENCE_FRAME_TOOL
        command.duration = 0

        twist = command.twist
        twist.linear_x = linear_x
        twist.linear_y = linear_y
        twist.linear_z = linear_z
        twist.angular_x = angular_x
        twist.angular_y = angular_y
        twist.angular_z = angular_z

        try:
            e = threading.Event()
            notification_handle = base.OnNotificationActionTopic(
                check_for_end_or_abort(e),
                Base_pb2.NotificationOptions()
            )

            if VERBOSE > 2:
                print("Executing twist action")
            base.SendTwistCommand(command)

            if VERBOSE > 2:
                print("Waiting for twist to finish ...")
            finished = e.wait(TIMEOUT_DURATION)
            base.Unsubscribe(notification_handle)

        except Exception:
            finished = False

        if VERBOSE > 2:
            print("Stopping the robot...")
        base.Stop()
        time.sleep(1)

    return finished


def perturbed_snapshot(snapshot_file, perturb_amount=PERTURB_AMOUNT, axis="z"):
    """
    Creates a perturbed snapshot by modifying the specified axis position in the given snapshot file.

    Args:
        snapshot_file (str): Path to the snapshot JSON file.
        perturb_amount (float): Amount to perturb the position along the specified axis (default is PERTURB_AMOUNT).
        axis (str): Axis to apply the perturbation to, defaults to "z".

    Returns:
        str: Path to the new perturbed snapshot file.
    """
    with open(snapshot_file, 'r') as fn:
        master_data = json.load(fn)

    # Generate temporary perturbed file
    new_height = master_data["poses"]["pose"][0]["reachPose"]["targetPose"][axis] + perturb_amount
    master_data["poses"]["pose"][0]["reachPose"]["targetPose"][axis] = new_height
    with open(os.path.join(SNAPSHOT_DIR, "_temp_perturbed.json"), "w+") as fn:
        json.dump(master_data, fn, indent=2)
    return os.path.join(SNAPSHOT_DIR, "_temp_perturbed.json")


def _try_movement(snapshot_file, target_position=None, raise_error=True, error_msg=None):
    """
    Attempts to move the robot arm to the specified snapshot file. Retries if the initial movement fails.

    Args:
        snapshot_file (str): Path to the snapshot file.
        target_position (str): Target position for the movement, if specified.
        raise_error (bool): Whether to raise an error if the movement fails (default is True).
        error_msg (str): Custom error message in case of failure.

    Returns:
        bool: True if the movement was successful, False otherwise.

    Raises:
        Exception: If the movement fails and raise_error is True.
    """
    success = snapshot_move(snapshot_file, target_position=target_position)
    print("SNAPSHOT: ", snapshot_file)
    if not success:
        # If movement fails the first time, move to home then try again
        print(f"Moving to snapshot {snapshot_file} failed the first time...trying to move to home...")
        snapshot_move(SNAPSHOT_HOME)
        success = snapshot_move(snapshot_file)
        if (not success) and raise_error:
            raise Exception(error_msg or f"Failed to move robot arm to snapshot {snapshot_file}.")
    return success


def get_place_vial(snapshot_file, action_type="get", pre_position_file=None, raise_amount=0.0,
                   release_vial=True, raise_error=True, go=True, leave=True):
    """
    Executes an action to get or place a vial using snapshot movements.

    Args:
        snapshot_file (str): Path to the snapshot file for the target vial position.
        action_type (str): Action type, either 'get' (to retrieve the vial) or 'place' (to place the vial).
        pre_position_file (str): Path to a pre-position snapshot file (optional).
        raise_amount (float): Amount to raise the robot arm above the target position (default is 0.0).
        release_vial (bool): Whether to release the vial after placing (default is True).
        raise_error (bool): Whether to raise an error if movement fails (default is True).
        go (bool): Whether to move to the snapshot file location (default is True).
        leave (bool): Whether to leave the snapshot file location after the action (default is True).

    Returns:
        bool: True if the action was successful, False otherwise.

    Raises:
        Exception: If the movement fails and raise_error is True.
    """
    snapshot_file_above = perturbed_snapshot(snapshot_file, perturb_amount=raise_amount)

    # Start open if getting a vial
    success = snapshot_move(target_position='open') if action_type == "get" else True

    if go:
        # If pre-position, go there
        if pre_position_file:
            success += snapshot_move(pre_position_file)
            if (not success) and raise_error:
                raise Exception(f"Failed to move robot arm pre-position snapshot {pre_position_file} before target.")

        # Go to above target position before target
        success += snapshot_move(snapshot_file_above)
        print("ABOVE: ", snapshot_file_above)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm to {raise_amount} above target before snapshot {snapshot_file}.")

        # Go to target position
        target = VIAL_GRIP_TARGET if action_type == "get" else 'open' if release_vial else VIAL_GRIP_TARGET
        success += snapshot_move(snapshot_file, target_position=target)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm to snapshot {snapshot_file}.")

    if leave:
        # Go to above target position after target
        success += snapshot_move(snapshot_file_above)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm to {raise_amount} above target after snapshot {snapshot_file}.")

        # If pre-position, go there
        if pre_position_file:
            success += snapshot_move(pre_position_file)
            if (not success) and raise_error:
                raise Exception(f"Failed to move robot arm pre-position snapshot {pre_position_file} after target.")

    return success


def screw_lid(screw=True, starting_position="vial-screw_test.json", linear_z=0.00003, angular_z=120):
    """
    Screws or unscrews the vial lid by controlling the robot arm's movement.

    Args:
        screw (bool): True to screw the lid on, False to unscrew it (default is True).
        starting_position (str): Path to the starting snapshot position file.
        linear_z (float): Amount of linear movement along the z-axis per iteration (default is 0.00003).
        angular_z (float): Amount of rotational movement along the z-axis in degrees (default is 120).

    Returns:
        bool: True if the action was successful, False otherwise.
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


def send_arduino_cmd(station, command, address=ARDUINO_PORT, return_txt=False):
    """
    Sends a command to the Arduino controlling a specific station.

    Args:
        station (str): The station identifier (e.g., "E1", "P1").
        command (str): The command to send (e.g., "0", "1", "500").
        address (str): Address of the Arduino port (default is ARDUINO_PORT).
        return_txt (bool): Whether to return the Arduino response text (default is False).

    Returns:
        bool or str: True if the command succeeded, the response text if return_txt is True, otherwise False on failure.

    Raises:
        Exception: If unable to connect to the Arduino.
    """
    try:
        arduino = serial.Serial(address, 115200, timeout=.1)
    except:
        try:
            time.sleep(20)
            arduino = serial.Serial(address, 115200, timeout=.1)
        except:
            raise Exception("Warning! {} is not connected".format(address))
    time.sleep(1)  # give the connection a second to settle
    arduino.write(bytes(f"{station}_{command}", encoding='utf-8'))  # EX: E1_0 or P1_1_500
    print("Command {} given to station {} at {} via Arduino.".format(command, station, address))
    start_time = time.time()
    try:
        while True:
            print("trying to read...")
            data = arduino.readline()
            print("waiting for {} arduino results for {:.1f} seconds...".format(station, time.time() - start_time))
            if data:
                result_txt = data.decode().strip()  # strip out the old lines
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
                print("ARDUINO ABORT MESSAGE: ", data.decode().strip())  # strip out the old lines
                raise KeyboardInterrupt
            time.sleep(1)


def write_test(file_path, test_type=""):
    """
    Writes test data to a file based on the test type.

    Args:
        file_path (str): Path to the output file.
        test_type (str): Type of test data to write. Options are "cv", "ca", or "ircomp".
    """
    test_files = {
        "cv": os.path.join(TEST_DATA_DIR, "standard_data", "CV.txt"),
        "ca": os.path.join(TEST_DATA_DIR, "standard_data", "CA.txt"),
        "ircomp": os.path.join(TEST_DATA_DIR, "standard_data", "iRComp.txt"),
    }
    test_fn = test_files.get(test_type.lower())
    if os.path.isfile(test_fn):
        with open(test_fn, 'r') as fn:
            test_text = fn.read()
    else:
        test_text = "test"
    with open(file_path, 'w+') as fn:
        fn.write(test_text)


if __name__ == "__main__":
    # some commands for demonstration
    sn_file = r"C:\Users\Lab\D3talesRobotics\roboticsUI\robotics_api\snapshots\Cartesian Example.json"
    # snapshot_move(sn_file, False)
    twist_hand(angular_z=30)
