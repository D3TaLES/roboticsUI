import cv2
import numpy as np
import warnings
from pyzbar import pyzbar
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


def calculate_robot_movement(qr_code: pyzbar.Decoded, vision_frame: np.ndarray, qr_size_ratio: float = 0.2,
                             movement_scale_factor: float = 0.001) -> object:
    """
    Calculates the movement needed for the robot to align with the QR code and adjust to the target size.

    Args:
        qr_code (pyzbar.Decoded): The selected QR code.
        vision_frame (numpy.ndarray): The frame in which the QR code was detected.
        qr_size_ratio (float, optional): The target QR code size as a percentage of the frame width. Default is 0.2 (20%).
        movement_scale_factor (float, optional): Scaling factor for movement calculations. Default is 0.001.

    Returns:
        tuple: A tuple containing:
            - move_x (float): The movement in the x-axis to center the QR code.
            - move_y (float): The movement in the y-axis to center the QR code.
            - move_z (float): The movement in the z-axis to adjust the size of the QR code.
    """
    # Frame size
    height, width, _ = vision_frame.shape

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

    # Target QR code width based on frame size and percentage
    target_qr_size = width * qr_size_ratio

    # Calculate movement commands (example: adjust by ratio)
    move_x = -offset_x * movement_scale_factor
    move_y = -offset_y * movement_scale_factor
    move_z = (target_qr_size - w) * movement_scale_factor

    return move_x, move_y, move_z


# def move_robot_to_qr(base, move_x, move_y, move_z):
#     """
#     Moves the Kinova robot based on the calculated movement to align with the QR code.
#
#     Args:
#         base (BaseClient): The base client for controlling the Kinova robot.
#         move_x (float): The movement in the x-axis to center the QR code.
#         move_y (float): The movement in the y-axis to center the QR code.
#         move_z (float): The movement in the z-axis to adjust the size of the QR code.
#     """
#     # Create a move command
#     move_command = Base_pb2.TwistCommand()
#     move_command.twist.linear_x = move_x
#     move_command.twist.linear_y = move_y
#     move_command.twist.linear_z = move_z
#
#     # Send the command to the robot
#     base.SendTwistCommand(move_command)
#     return True  # TODO add success validation


if __name__ == "__main__":
    qr_codes, frame = get_qr_codes_from_camera(camera_ip=KINOVA_01_IP)
    print(qr_codes)
    selected_qr = select_qr_code(qr_codes, "Vial_A_01")
    print(selected_qr)
    move_x, move_y, move_z = calculate_robot_movement(selected_qr, frame)
    print(move_x, move_y, move_z)
    pass
