import sys
import os
import json
import threading
from argparse import Namespace

from kortex_api.autogen.messages import Base_pb2
from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
from robotics_api.workflows.actions import utilities
from robotics_api.workflows.actions.gripper_move import GripperMove
from d3tales_api.Calculators.utils import dict2obj

# Maximum allowed waiting time during actions (in seconds)
TIMEOUT_DURATION = 20
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# Create closure to set an event after an END or an ABORT
def check_for_end_or_abort(e):
    """Return a closure checking for END or ABORT notifications

    Arguments:
    e -- event to signal when the action is completed
        (will be set when an END or ABORT occurs)
    """

    def check(notification, e=e):
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

    def check(notification, e = e):
        event_id = notification.event_identifier
        task_id = notification.task_index
        if event_id == Base_pb2.SEQUENCE_TASK_COMPLETED:
            print("Sequence task {} completed".format(task_id))
        elif event_id == Base_pb2.SEQUENCE_ABORTED:
            print("Sequence aborted with error {}:{}"\
                .format(\
                    notification.abort_details,\
                    Base_pb2.SubErrorCodes.Name(notification.abort_details)))
            e.set()
        elif event_id == Base_pb2.SEQUENCE_COMPLETED:
            print("Sequence completed.")
            e.set()
    return check


def snapshot_move_angular(base, joint_angle_values):
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

    print("Executing action")
    base.ExecuteAction(action)

    print("Waiting for movement to finish ...")
    finished = e.wait(TIMEOUT_DURATION)
    base.Unsubscribe(notification_handle)

    if finished:
        print("Angular movement completed")
    else:
        print("Timeout on action notification wait")
    return finished


def snapshot_move_cartesian(base, coordinate_values):
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

    print("Executing action")
    base.ExecuteAction(action)

    print("Waiting for movement to finish ...")
    finished = e.wait(TIMEOUT_DURATION)
    base.Unsubscribe(notification_handle)

    if finished:
        print("Cartesian movement completed")
    else:
        print("Timeout on action notification wait")
    return finished


def move_gripper(target_position=None):
    # Import the utilities' helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    finished = True

    # Create connection to the device and get the router
    connector = Namespace(ip="192.168.1.10", username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create connection to the device and get therouter
        with utilities.DeviceConnection.createUdpConnection(connector) as router_real_time:
            action = GripperMove(router, router_real_time, 2)

            if target_position == 'open':
                print("Moving gripper open...")
                finished += action.gripper_move(10)
                action.cleanup()
            elif target_position == 'closed':
                print("Moving gripper closed...")
                finished += action.gripper_move(90)
                action.cleanup()
            elif target_position:
                print("Moving gripper to {}...".format(target_position))
                finished += action.gripper_move(target_position)
                action.cleanup()

    print("Gripper movement successfully executed!" if finished else "Error! Gripper was not successfully moved.")
    return finished


def snapshot_move(snapshot_file=None, target_position=None):
    # Import the utilities' helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    finished = True

    # Create connection to the device and get the router
    connector = Namespace(ip="192.168.1.10", username="admin", password="admin")
    with utilities.DeviceConnection.createTcpConnection(connector) as router:
        # Create required services
        base = BaseClient(router)

        if snapshot_file:
            # loads file
            snapshot_file = open(snapshot_file, 'r')

            # converts JSON to nested dictionary
            print(snapshot_file)
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
                finished += snapshot_move_angular(base, joint_angle_values)
            elif move_type == "cartesian":
                finished += snapshot_move_cartesian(base, coordinate_values)
            else:
                finished += True
                print("... and nothing happened")
            snapshot_file.close()

    if target_position:
        finished += move_gripper(target_position)

    print("Snapshot successfully executed!" if finished else "Error! Snapshot was not successfully executed.")
    return finished


def sequence_move(sequence_file):
    # Import the utilities' helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    finished = True

    # Create connection to the device and get the router
    connector = Namespace(ip="192.168.1.10", username="admin", password="admin")
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


if __name__ == "__main__":
    # some commands for demonstration
    sn_file = r"C:\Users\Lab\D3talesRobotics\roboticsUI\robotics_api\workflows\snapshots\Cartesian Example.json"
    snapshot_move(sn_file, False)
