import sys
import json
import time
import warnings
import threading
import numpy as np
from argparse import Namespace
from kortex_api.autogen.messages import Base_pb2
from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient

from robotics_api.actions.db_manipulations import VialStatus
from robotics_api.utils import kinova_utils as utilities
from robotics_api.utils.kinova_gripper import GripperMove
from kortex_api.autogen.client_stubs.VisionConfigClientRpc import VisionConfigClient
from robotics_api.utils.kinova_vision import get_qr_codes_from_camera, calculate_robot_movement, select_qr_code
from robotics_api.settings import *

# Maximum allowed waiting time during actions (in seconds)
TIMEOUT_DURATION = 20
VERBOSE = 4


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


def move_angular(base: BaseClient, joint_angle_values, angle_error: float = 0.2):
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
        current_joint_angles_raw = base.GetMeasuredJointAngles()
        current_joint_angles = {i.joint_identifier: i.value % 360 for i in
                                current_joint_angles_raw.joint_angles}
        joint_angle_values_dict = {i["jointIdentifier"]: i["value"] for i in joint_angle_values}
        angle_diffs = [abs(current_joint_angles.get(k, 0) - joint_angle_values_dict.get(k, 0)) for k
                       in joint_angle_values_dict]
        if not all([d < angle_error for d in angle_diffs]):
            error_diffs = [d for d in angle_diffs if d > angle_error]
            if not all([round(abs(d - 360), 5) < angle_error for d in error_diffs]):
                finished = False
                raise SystemError("Error: Robot did not reach the desired joint angles: ", angle_diffs)
    else:
        if VERBOSE > 3:
            print("Timeout on action notification wait")
    return finished


def move_cartesian(base: BaseClient, coordinate_values: dict, position_error: float = 0.1):
    if VERBOSE > 3:
        print("Starting Cartesian action movement ...")
    action = Base_pb2.Action()
    action.name = "Example Cartesian action movement"
    action.application_data = ""

    print(coordinate_values)
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
        current_pose_raw = base.GetMeasuredCartesianPose()
        current_pose = {"x": current_pose_raw.x, "y": current_pose_raw.y, "z": current_pose_raw.z,
                        "thetaX": current_pose_raw.theta_x, "thetaY": current_pose_raw.theta_y,
                        "thetaZ": current_pose_raw.theta_z}
        pose_diffs = [abs(current_pose.get(k, 0) - coordinate_values.get(k, 0)) for k in
                      coordinate_values]
        if not all([round(d < position_error, 5) for d in pose_diffs]):
            raise SystemError(f"Error: Robot did not reach the desired Cartesian pose "
                              f"({[coordinate_values.get(k, 0) for k in coordinate_values]}): {pose_diffs}")
    else:
        if VERBOSE > 1:
            print("Timeout on action notification wait")
    return finished


def move_gripper(target_position=None, max_gripper_attempts=5):
    """
    Move gripper
    :param target_position: target position for the gripper: open, closed, or percentage closed (e.g., 90)
    :return: bool, True if action a success
    """

    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")

    def _try_gripper(conn=connector, target=target_position):
        finished = True
        with utilities.DeviceConnection.createTcpConnection(conn) as router:
            # Create connection to the device and get the router
            with utilities.DeviceConnection.createUdpConnection(conn) as router_real_time:
                action = GripperMove(router, router_real_time, 2)

                if target == 'open':
                    if VERBOSE > 2:
                        print("Moving gripper open...")
                    finished &= action.gripper_move(OPEN_GRIP_TARGET)
                    action.cleanup()
                elif target == 'closed':
                    if VERBOSE > 2:
                        print("Moving gripper closed...")
                    finished &= action.gripper_move(90)
                    action.cleanup()
                elif target:
                    if VERBOSE > 2:
                        print("Moving gripper to {}...".format(target))
                    finished &= action.gripper_move(target)
                    action.cleanup()
        return finished

    gripper_tries = 0
    while True:
        try:
            finished = _try_gripper()
            break
        except Exception as e:
            if gripper_tries > max_gripper_attempts:
                raise e
            print(f"WARNING. Gripper movement {gripper_tries} ended in error: ", e)
            gripper_tries += 1

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


def get_zone(angle, zone_dividers=ZONE_DIVIDERS):
    """
    Moves a given joint a specified range (in degrees).

    Args:
        angle (float): The angle in degrees.
        zone_dividers (list): A list of zone divider angles in ascending order.
    Returns:
        int: The zone index (starting from 1) that the angle belongs to.
    """

    # Make sure zone_dividers starts with 0
    zone_dividers = list(set([0] + zone_dividers))
    zone_dividers.sort()

    print("ZONES: ", angle, zone_dividers)
    # Check if angle is above the last divider
    if angle > zone_dividers[-1]:
        return 1  # Belongs to Zone 1

    # Find the zone
    for idx in range(len(zone_dividers)):
        if zone_dividers[idx] <= angle < (zone_dividers[(idx + 1) % len(zone_dividers)]):
            return idx + 1  # Zone index starts from 1

    raise ValueError(f"Zone not found for angle {angle} and dividers {zone_dividers}.")


def get_current_zone(zone_dividers=ZONE_DIVIDERS):
    """
    Moves a given joint a specified range (in degrees).

    Args:
        zone_dividers (list): A list of zone divider angles in ascending order.
    Returns:
        int: The zone index (starting from 1) that the angle belongs to.
    """
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create required services
        base = BaseClient(router)

        current_joint_angles = base.GetMeasuredJointAngles()
        joint_1_angle = current_joint_angles.joint_angles[0].value
        return get_zone(joint_1_angle, zone_dividers=zone_dividers)


def snapshot_zone(snapshot_file, zone_dividers=ZONE_DIVIDERS):
    """
    Moves a given joint a specified range (in degrees).

    Args:
        snapshot_file (str): A list of zone divider angles in ascending order.
        zone_dividers (list): A list of zone divider angles in ascending order.
    Returns:
        int: The zone index (starting from 1) that the angle belongs to.
    """
    with open(snapshot_file, 'r') as fn:
        master_data = json.load(fn)

        if "jointAnglesGroup" in master_data.keys():
            joint_angle_values = master_data["jointAnglesGroup"]["jointAngles"][0]["reachJointAngles"]["jointAngles"][
                "jointAngles"]
            theta = joint_angle_values[0]["value"]
        elif "poses" in master_data.keys():
            coordinate_values = master_data["poses"]["pose"][0]["reachPose"]["targetPose"]
            x = coordinate_values["x"]
            y = coordinate_values["y"]
            theta = -np.degrees(np.arctan2(y, x)) % 360
    return get_zone(theta, zone_dividers=zone_dividers)


def snapshot_move(snapshot_file: str = None, target_position: str or int = None, raise_error: bool = True, **kwargs):
    """

    :param snapshot_file: str, path to snapshot file (JSON)
    :param target_position: target position for the gripper: open, closed, or percentage closed (e.g., 90)
    :param raise_error:
    :return: bool, True if movement was a success

    Args:
        angle_error:
        position_error:
    """
    if not RUN_ROBOT:
        warnings.warn("Robot NOT run because RUN_ROBOT is set to False.")
        return True

    finished = False

    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    if snapshot_file:
        try:
            with utilities.DeviceConnection.createTcpConnection(connector) as router:
                # Create required services
                base = BaseClient(router)

                with open(snapshot_file, 'r') as snapshot_file:
                    # converts JSON to nested dictionary
                    snapshot_file.dict = json.load(snapshot_file)

                    if "jointAnglesGroup" in snapshot_file.dict:
                        # grabs the list of joint angle values
                        joint_angle_values = \
                            snapshot_file.dict["jointAnglesGroup"]["jointAngles"][0]["reachJointAngles"]["jointAngles"][
                                "jointAngles"]
                        finished = move_angular(base, joint_angle_values, **kwargs)
                    elif "poses" in snapshot_file.dict:
                        # grabs the dictionary of coordinate values
                        coordinate_values = snapshot_file.dict["poses"]["pose"][0]["reachPose"]["targetPose"]
                        finished = move_cartesian(base, coordinate_values, **kwargs)
                    else:
                        if raise_error:
                            raise SystemError("Snapshot file type not suitable for robot movement")
        except Exception as e:
            raise Exception(e)

    if target_position:
        finished = move_gripper(target_position)
    print("Snapshot successfully executed!" if finished else "Error! Snapshot was not successfully executed.")
    return finished


def perturb_cartesian(wait_time=None, **coordinate_deltas):
    """
    Moves a given coordinate a specified range (in degrees).

    Args:
        wait_time : Wait time after move
        coordinate_deltas : Key word arguments

    Returns:
        bool: True if the movement completed successfully, False otherwise.
    """
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create required services
        base = BaseClient(router)

        current_pose = base.GetMeasuredCartesianPose()
        target_pose = {
            "x": current_pose.x + coordinate_deltas.get("x", 0),
            "y": current_pose.y + coordinate_deltas.get("y", 0),
            "z": current_pose.z + coordinate_deltas.get("z", 0),
            "thetaX": current_pose.theta_x + coordinate_deltas.get("thetaX", 0),
            "thetaY": current_pose.theta_y + coordinate_deltas.get("thetaY", 0),
            "thetaZ": current_pose.theta_z + coordinate_deltas.get("thetaZ", 0)
        }

        if wait_time:
            time.sleep(wait_time)

        return move_cartesian(base, target_pose)


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
        current_joint_angles = base.GetMeasuredJointAngles()

        joint_angles = []
        for joint in current_joint_angles.joint_angles:
            i = joint.joint_identifier
            delta_value = joint_deltas.get(f"j{i + 1}", 0) * (-1 if reverse else 1)
            final_angle = (joint.value + delta_value) % 360
            if delta_value:
                print(f"Moving joint {i + 1} {delta_value} degrees to {final_angle}")
            joint_angles.append({"joint_identifier": i, "value": final_angle})

        if wait_time:
            time.sleep(wait_time)

        return move_angular(base, joint_angles)


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


def move_to_station_qr(destination_station: str, **kwargs):
    """
    Main function that coordinates the process of moving the Kinova robot to align with a QR code.

    Args:
        destination_station (str): The destination station that corresponds to the QR code data.
        target_qr_size (float): The desired size of the QR code in pixels, used to adjust the robot's position.

    Returns:
        bool: Returns True if the robot did not move because RUN_ROBOT is set to False.
    """
    # Check if robot operation is enabled
    if not RUN_ROBOT:
        warnings.warn("Robot NOT run because RUN_ROBOT is set to False.")
        return True

    # Create connection to the device and get the router
    connector = Namespace(ip=KINOVA_01_IP, username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create required services
        base = BaseClient(router)
        vision_config = VisionConfigClient(router)

        # Get QR codes from the camera
        qr_codes, frame = get_qr_codes_from_camera()

        if not qr_codes:
            warnings.warn(f"No QR codes detected. Robot did not move to {destination_station}.")
            return

        # Select the QR code that matches the destination
        selected_qr = select_qr_code(qr_codes, destination_station)

        if selected_qr is None:
            warnings.warn(f"No matching QR code for {destination_station}.")
            return

        # Calculate the robot movement required to align the QR code
        move_x, move_y, move_z = calculate_robot_movement(selected_qr, frame, **kwargs)
        print(move_x, move_y, move_z)

        # Move the robot
    success = perturb_cartesian(x=move_x, y=move_y, z=move_z)
    print("Robot moved to align with QR code.")

    return success


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

    destination_name = station.id
    starting_snapshot = station.pre_location_snapshot
    raise_amount = station.raise_amount

    success = True

    if go:
        # Start open if getting a vial
        success &= snapshot_move(target_position='open') if action_type == "get" else True

        # If move_to_zone, go to the correct zone
        target_zone = snapshot_zone(starting_snapshot)
        current_zone = get_current_zone()
        if current_zone != target_zone:
            print(f"--------- Moving from zone {current_zone} to zone {target_zone} ---------")
            success &= snapshot_move(os.path.join(SNAPSHOT_DIR, f"zone_{current_zone:02d}.json"))
            success &= snapshot_move(os.path.join(SNAPSHOT_DIR, f"zone_{target_zone:02d}.json"))

        # Go to starting_snapshot
        success &= snapshot_move(starting_snapshot)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm pre-position snapshot {starting_snapshot} before {station}.")

        # Go to above target position before target
        success &= move_to_station_qr(destination_name)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm to the QR code for {station}.")

        # Go to target position
        if not pre_position_only:
            target = VIAL_GRIP_TARGET if action_type == "get" else 'open' if release_vial else VIAL_GRIP_TARGET
            success &= move_hand(linear_z=raise_amount)
            success &= snapshot_move(target_position=target)
            if (not success) and raise_error:
                raise Exception(f"Failed to move robot arm to snapshot {station}.")

    if leave:
        # Go to above target position above/below target
        if raise_amount:
            success &= move_hand(linear_z=-raise_amount)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm to {-raise_amount} above {station}.")

        # Go to starting_snapshot
        success &= snapshot_move(starting_snapshot)
        if (not success) and raise_error:
            raise Exception(f"Failed to move robot arm pre-position snapshot {starting_snapshot} for {station}.")

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


if __name__ == "__main__":
    # print(snapshot_zone(SNAPSHOT_DIR / "cv_potentiostat_A_01.json"))
    # print(snapshot_zone(SNAPSHOT_DIR / "ca_potentiostat_B_01.json"))
    # print(snapshot_zone(SNAPSHOT_DIR / "VialHome_A_01.json"))
    # print(snapshot_zone(SNAPSHOT_DIR / "solvent_01.json"))
    # print(snapshot_zone(SNAPSHOT_DIR / "balance_01.json"))
    move_to_station_qr("Vial_A_01")
    # perturb_cartesian(z=0.1)
    # perturb_cartesian(x=0.0185, )
