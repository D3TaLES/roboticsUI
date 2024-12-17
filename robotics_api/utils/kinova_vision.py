import cv2
import warnings
from pyzbar import pyzbar
from kortex_api.autogen.messages import Base_pb2
from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
from robotics_api.settings import KINOVA_01_IP


def get_qr_codes_from_camera(camera_ip=KINOVA_01_IP):
    """
    Captures an image from the Kinova robot camera and detects any QR codes present.

    Args:
        camera_ip (str): The IP address of the Kinova robot's camera.

    Returns:
        tuple: A tuple containing:
            - qr_codes (list): A list of detected QR codes.
            - frame (numpy.ndarray): The captured frame from the camera.
    """
    cap = cv2.VideoCapture(f"rtsp://{camera_ip}/color")
    ret, frame = cap.read()

    if not ret:
        warnings.warn("OpenCv failed to capture image through the Kinova robot camera.")
        return [], None

    # Decode QR codes from the captured frame
    qr_codes = pyzbar.decode(frame)

    cap.release()
    return qr_codes, frame


def select_qr_code(qr_codes: list, destination_station):
    """
    Selects the QR code that matches the provided destination station.

    Args:
        qr_codes (list): A list of decoded QR codes.
        destination_station (str): The destination station to match against QR code content.

    Returns:
        pyzbar.Decoded: The matching QR code, or None if no match is found.
    """
    for qr in qr_codes:
        qr_data = qr.data.decode("utf-8")
        if qr_data == destination_station:
            return qr
    return None


def calculate_robot_movement(qr_code: object, frame: object, target_qr_size: object) -> object:
    """
    Calculates the movement needed for the robot to align with the QR code and adjust to the target size.

    Args:
        qr_code (pyzbar.Decoded): The selected QR code.
        frame (numpy.ndarray): The frame in which the QR code was detected.
        target_qr_size (float): The target size for the QR code in pixels.

    Returns:
        tuple: A tuple containing:
            - move_x (float): The movement in the x-axis to center the QR code.
            - move_y (float): The movement in the y-axis to center the QR code.
            - move_z (float): The movement in the z-axis to adjust the size of the QR code.
    """
    # Frame size
    height, width, _ = frame.shape

    # QR code center
    (x, y, w, h) = qr_code.rect
    qr_center_x = x + w / 2
    qr_center_y = y + h / 2

    # Image center
    image_center_x = width / 2
    image_center_y = height / 2

    # Calculate offset from center
    offset_x = qr_center_x - image_center_x
    offset_y = qr_center_y - image_center_y

    # Calculate movement commands (example: adjust by ratio)
    move_x = -offset_x * 0.01  # Scale factor for robot movement
    move_y = -offset_y * 0.01
    move_z = (target_qr_size - w) * 0.01

    return move_x, move_y, move_z


def move_robot_to_qr(base, move_x, move_y, move_z):
    """
    Moves the Kinova robot based on the calculated movement to align with the QR code.

    Args:
        base (BaseClient): The base client for controlling the Kinova robot.
        move_x (float): The movement in the x-axis to center the QR code.
        move_y (float): The movement in the y-axis to center the QR code.
        move_z (float): The movement in the z-axis to adjust the size of the QR code.
    """
    # Create a move command
    move_command = Base_pb2.TwistCommand()
    move_command.twist.linear_x = move_x
    move_command.twist.linear_y = move_y
    move_command.twist.linear_z = move_z

    # Send the command to the robot
    base.SendTwistCommand(move_command)
    return True  # TODO add success validation


if __name__ == "__main__":
    # qr_codes, frame = get_qr_codes_from_camera(camera_ip=KINOVA_01_IP)
    # selected_qr = select_qr_code(qr_codes, "A_04")
    # move_x, move_y, move_z = calculate_robot_movement(selected_qr, frame, 200)
    pass
