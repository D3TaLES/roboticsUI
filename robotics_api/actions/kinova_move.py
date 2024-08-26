import sys
import json
import time
import warnings
import threading
from argparse import Namespace

from kortex_api.autogen.messages import Base_pb2
from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
from robotics_api.actions import kinova_utils as utilities
from robotics_api.actions.kinova_gripper import GripperMove
from d3tales_api.Calculators.utils import dict2obj
from robotics_api.settings import *

# Maximum allowed waiting time during actions (in seconds)
TIMEOUT_DURATION = 20
VERBOSE = 1
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../workflows"))


# Create closure to set an event after an END or an ABORT
def check_for_end_or_abort(e):
    """Return a closure checking for END or ABORT notifications

    Arguments:
    e -- event to signal when the action is completed
        (will be set when an END or ABORT occurs)
    """

    def check(notification, e=e):
        if VERBOSE > 3:
            print("EVENT : " + \
                  Base_pb2.ActionEvent.Name(notification.action_event))
        if notification.action_event == Base_pb2.ACTION_END \
                or notification.action_event == Base_pb2.ACTION_ABORT:
            e.set()

    return check


def check_for_sequence_end_or_abort(e):
    """Return a closure checking for END or ABORT notifications on a sequence

    Arguments:
    e -- event to signal when the action is completed
        (will be set when an END or ABORT occurs)
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
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../workflows"))
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
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../workflows"))
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
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../workflows"))
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
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../workflows"))
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


if __name__ == "__main__":
    # some commands for demonstration
    sn_file = r"C:\Users\Lab\D3talesRobotics\roboticsUI\robotics_api\snapshots\Cartesian Example.json"
    # snapshot_move(sn_file, False)
    twist_hand(angular_z=30)
