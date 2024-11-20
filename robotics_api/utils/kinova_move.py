import sys
import json
import time
import warnings
import threading
from argparse import Namespace
from kortex_api.autogen.messages import Base_pb2
from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient

from robotics_api.actions.db_manipulations import VialStatus
from robotics_api.utils import kinova_utils as utilities
from robotics_api.utils.kinova_gripper import GripperMove
from robotics_api.settings import *

# Maximum allowed waiting time during actions (in seconds)
TIMEOUT_DURATION = 20
VERBOSE = 1


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


def snapshot_move_angular(base: BaseClient, joint_angle_values):
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


def snapshot_move_cartesian(base: BaseClient, coordinate_values: dict):
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
    finished = True

    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    try:
        with utilities.DeviceConnection.createTcpConnection(connector) as router:
            # Create connection to the device and get the router
            with utilities.DeviceConnection.createUdpConnection(connector) as router_real_time:
                action = GripperMove(router, router_real_time, 2)

                if target_position == 'open':
                    if VERBOSE > 2:
                        print("Moving gripper open...")
                    finished &= action.gripper_move(OPEN_GRIP_TARGET)
                    action.cleanup()
                elif target_position == 'closed':
                    if VERBOSE > 2:
                        print("Moving gripper closed...")
                    finished &= action.gripper_move(90)
                    action.cleanup()
                elif target_position:
                    if VERBOSE > 2:
                        print("Moving gripper to {}...".format(target_position))
                    finished &= action.gripper_move(target_position)
                    action.cleanup()

    except Exception as e:
        raise Exception("Gripper movement failed with exception ", e)

    print("Gripper movement successfully executed!" if finished else "Error! Gripper was not successfully moved.")
    return finished


def move_hand(linear_x: float = 0, linear_y: float = 0, linear_z: float = 0,
              angular_x: float = 0, angular_y: float = 0, angular_z: float = 0):
    """
    Function to move the robotic hand by linear and angular x, y, and z

    Args:
        linear_x (float): increment of linear x movement
        linear_y (float): increment of linear y movement
        linear_z (float): increment of linear z movement
        angular_x (float): increment of angular x movement
        angular_y (float): increment of angular y movement
        angular_z (float): increment of angular z movement

    Returns: boolean indicating success of action

    """
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


def snapshot_move(snapshot_file: str = None, target_position: str = None, raise_error: bool = True,
                  angle_error: float = 0.2, position_error: float = 0.1):
    """

    :param snapshot_file: str, path to snapshot file (JSON)
    :param target_position: target position for the gripper: open, closed, or percentage closed (e.g., 90)
    :param raise_error:
    :param angle_error:
    :param position_error:
    :return: bool, True if movement was a success

    Args:
        angle_error:
        position_error:
    """
    if not RUN_ROBOT:
        warnings.warn("Robot NOT run because RUN_ROBOT is set to False.")
        return True

    finished = True

    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    try:
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
                                raise SystemError(f"Error: Robot did not reach the desired Cartesian pose "
                                                  f"({[coordinate_values.get(k, 0) for k in coordinate_values]}):"
                                                  f" {pose_diffs}")
                            finished = False
                    else:

                        if raise_error:
                            raise SystemError("Error: Unknown move type for confirmation.")
                        finished = False

    except Exception as e:
        raise Exception(e)

    if target_position:
        move_gripper(target_position)
    print("Snapshot successfully executed!" if finished else "Error! Snapshot was not successfully executed.")
    return finished


def perturb_angular(reverse=False, wait_time=None, **joint_deltas):
    """
    Moves a given joint a specified range (in degrees).

    Args:
        reverse : Reverse all joint deltas if True
        wait_time : Wait time after move
        joint_deltas : Key word arguments

    Returns:
        bool: True if the movement completed successfully, False otherwise.
    """
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create required services
        base = BaseClient(router)
        current_joint_angles = base.GetMeasuredJointAngles()  # Assuming this method exists

        def _angle(a):
            return a if a < 360 else a - 360

        joint_angles = []
        for joint in current_joint_angles.joint_angles:
            i = joint.joint_identifier
            delta_value = joint_deltas.get(f"j{i+1}", 0) * (-1 if reverse else 1)
            final_angle = _angle(joint.value + delta_value)
            if delta_value:
                print(f"Moving joint {i+1} {delta_value} degrees to {final_angle}")
            joint_angles.append({"joint_identifier": i, "value": final_angle})

        if wait_time:
            time.sleep(wait_time)

        return snapshot_move_angular(base, joint_angles)


def perturbed_snapshot(snapshot_file, perturb_amount: float = PERTURB_AMOUNT, axis="z"):
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


def get_place_vial(station, action_type="get", go=True, leave=True, release_vial=True, raise_error=True,
                   pre_position_only=False):
    """
    Executes an action to get or place a vial using snapshot movements.

    Args:
        station (StationStatus):
        action_type (str): Action type, either 'get' (to retrieve the vial) or 'place' (to place the vial).
        go (bool): Whether to move to the snapshot file location (default is True).
        leave (bool): Whether to leave the snapshot file location after the action (default is True).
        release_vial (bool): Whether to release the vial after placing (default is True).
        raise_error (bool): Whether to raise an error if movement fails (default is True).
        pre_position_only (bool): Only move to "above" position if True (default is True).
    Returns:
        bool: True if the action was successful, False otherwise.

    Raises:
        Exception: If the movement fails and raise_error is True.
    """
    # Check if robot operation is enabled
    if not RUN_ROBOT:
        warnings.warn("Robot NOT run because RUN_ROBOT is set to False.")
        return True

    raise_amount = station.raise_amount
    if isinstance(station, VialStatus):
        snapshot_file = station.home_snapshot
        pre_position_file = None
    else:
        snapshot_file = station.location_snapshot
        pre_position_file = station.pre_location_snapshot

    snapshot_file_above = perturbed_snapshot(snapshot_file, perturb_amount=raise_amount)

    success = True

    if go:
        # Start open if getting a vial
        success &= snapshot_move(target_position='open') if action_type == "get" else True
        # If pre-position, go there
        if pre_position_file:
            success &= snapshot_move(pre_position_file)
            if (not success) and raise_error:
                raise Exception(f"Failed to move robot arm pre-position snapshot {pre_position_file} before target.")

        # Go to above target position before target
        success &= snapshot_move(snapshot_file_above)
        print("ABOVE: ", snapshot_file_above)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm to {raise_amount} above target before snapshot {snapshot_file}.")

        # Go to target position
        if not pre_position_only:
            target = VIAL_GRIP_TARGET if action_type == "get" else 'open' if release_vial else VIAL_GRIP_TARGET
            success &= snapshot_move(snapshot_file, target_position=target)
            if (not success) and raise_error:
                raise Exception(f"Failed to move robot arm to snapshot {snapshot_file}.")

    if leave:
        # Go to above target position after target
        success &= snapshot_move(snapshot_file_above)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm to {raise_amount} above target after snapshot {snapshot_file}.")

        # If pre-position, go there
        if pre_position_file:
            success &= snapshot_move(pre_position_file)
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
    success &= snapshot_move(snapshot_start)
    success &= snapshot_move(target_position=VIAL_GRIP_TARGET + 4)

    rotation_increment = (angular_z / 20) if screw else (-angular_z / 20)
    raise_height = linear_z if screw else -linear_z
    for _ in range(5):
        success &= move_hand(linear_z=raise_height, angular_z=rotation_increment)

    if screw:
        success = snapshot_move(target_position='open')
    else:
        print("Done unscrewing. ")
        success &= snapshot_move(snapshot_top)

    return success


