import os
import math
from pathlib import Path

RUN_CV = True
DISPENSE = True
CAPPED_DEFAULT = False
CAPPED_ERROR = False

# ---------  ROBOT VARIABLES -------------
KINOVA_01_IP = "192.168.1.10"
VIAL_GRIP_TARGET = 65
OPEN_GRIP_TARGET = 40
RAISE_AMOUNT = 0.07

# ---------  DEFAULT CONDITIONS -------------
DEFAULT_TEMPERATURE = "293K"
DEFAULT_CONCENTRATION = "0.01M"
DEFAULT_WORKING_ELECTRODE_RADIUS = 1  # radius assumed in mm
DEFAULT_WORKING_ELECTRODE_AREA = (math.pi * (DEFAULT_WORKING_ELECTRODE_RADIUS ** 2)) * 0.01  # area given in cm^2

TIME_UNIT = "s"
MASS_UNIT = "mg"
VOLUME_UNIT = "mL"
TEMPERATURE_UNIT = "K"

# ---------  PATH VARIABLES -------------
D3TALES_DIR = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api")
DATA_DIR = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "data")
SNAPSHOT_DIR = os.path.join(D3TALES_DIR, "workflows", "snapshots")
SNAPSHOT_HOME = os.path.join(D3TALES_DIR, "workflows", "snapshots", "home.json")
SNAPSHOT_END_HOME = os.path.join(D3TALES_DIR, "workflows", "snapshots", "end_home.json")

# ---------  POTENTIOSTAT VARIABLES -------------

ECLIB_DLL_PATH = r"C:\EC-Lab Development Package\EC-Lab Development Package\\EClib64.dll"
POTENTIOSTAT_A_ADDRESS = "USB0"
# POTENTIOSTAT_B_ADDRESS = "USB1"

N_CYCLES = 0
SCAN_NUMBER = 1  # Not currently included in CV parameters
AVERAGE_OVER_DE = True
RECORD_EVERY_DE = 0.01  # Volts
CUT_BEGINNING = 0.007  # percentage as decimal of front of CV to cut
CUT_END = 0.0  # percentage as decimal of end of CV to cut
MIN_CV_STEPS = 6  # minimum number of CV steps

RECORD_EVERY_DT = 0.01  # seconds
I_RANGE = 'I_RANGE_10mA'
VS_INITIAL = False
TIME_OUT = 10  # seconds
TIME_AFTER_CV = 5  # seconds
MAX_WAIT_TIME = 300  # seconds

AUTO_VOLT_BUFFER = 0.25  # Volts

# iR Compensation Variables
RCOMP_LEVEL = 85
INITIAL_FREQUENCY = 5
FINAL_FREQUENCY = 60


# ---------  PROCESSING VARIABLES -------------
RUN_ANODIC = False
CONVERT_A_TO_MA = True
PLOT_CURRENT_DENSITY = True
MULTI_PLOT_XLABEL = "Potential (V) vs Ag/$Ag^+$"
MULTI_PLOT_YLABEL = None  # uses default D3TaLES API y label
MULTI_PLOT_LEGEND = "Scan Rate (V/s)"

PEAK_WIDTH = 0.5

# ---------  ARDUINO VARIABLES -------------
ARDUINO_ADDRESS = "COM4"

# ---------  LOCATION VARIABLES -------------
DISPENSE_STATIONS = ["solvent_01"]
MEASUREMENT_STATIONS = ["potentiostat_A_02", "potentiostat_A_03"]
ACTION_STATIONS = ["robot_grip", "stir-heat_01"]
STATIONS = DISPENSE_STATIONS + MEASUREMENT_STATIONS + ACTION_STATIONS
VIALS = [
    "S_01", "S_02", "S_03", "S_04",
    "A_01", "A_02", "A_03", "A_04",
    "B_01", "B_02", "B_03", "B_04",
    "C_01", "C_02", "C_03", "C_04",
]
SOLVENT_VIALS = {"solvent_01": "S_01"}


# ---------  FIREWORKS VARIABLES -------------
HOME_DIR = os.path.dirname(os.path.realpath(__file__))
LAUNCH_DIR = os.path.abspath('C:\\Users\\Lab\\D3talesRobotics\\launch_dir')
LAUNCHPAD = os.path.abspath(
    'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\launchpad_robot.yaml')
ROBOT_FWORKER = os.path.abspath(
    'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\fireworker_robot.yaml')
PROCESS_FWORKER = os.path.abspath(
    'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\fireworker_process.yaml')
PROCESS_INSTRUMENT_FWORKER = os.path.abspath(
    'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\fireworker_process_instrument.yaml')
