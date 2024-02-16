import os
import math
from pathlib import Path


# ---------  TESTING OPERATION VARIABLES -------------
RUN_POTENT = False
POT_DELAY = 5  # seconds
STIR = False
DISPENSE = False
RUN_ROBOT = False
MOVE_ELEVATORS = False

# ---------  OPERATION VARIABLES -------------
CAPPED_ERROR = False
CAPPED_DEFAULT = False
RERUN_FIZZLED_ROBOT = True
FIZZLE_CONCENTRATION_FAILURE = False
FIZZLE_DIRTY_ELECTRODE = True
DIRTY_ELECTRODE_CURRENT = 0.00001  # max current allowed (A) for a clean electrode

# ---------  DEFAULT CONDITIONS -------------
DEFAULT_TEMPERATURE = "293K"
DEFAULT_CONCENTRATION = "0.01M"
DEFAULT_WORKING_ELECTRODE_RADIUS = 0.01  # radius assumed in mm
DEFAULT_WORKING_ELECTRODE_AREA = (math.pi * (DEFAULT_WORKING_ELECTRODE_RADIUS ** 2)) * 0.01  # area given in cm^2
MICRO_ELECTRODES = True if DEFAULT_WORKING_ELECTRODE_RADIUS < 0.1 else False  # TODO confirm condition

TIME_UNIT = "s"
MASS_UNIT = "mg"
VOLUME_UNIT = "mL"
TEMPERATURE_UNIT = "K"

# ---------  ROBOT VARIABLES -------------
KINOVA_01_IP = "192.168.1.10"
VIAL_GRIP_TARGET = 70
OPEN_GRIP_TARGET = 40
RAISE_AMOUNT = 0.07

# ---------  PATH VARIABLES -------------
D3TALES_DIR = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api")
DATA_DIR = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "data")
SNAPSHOT_DIR = os.path.join(D3TALES_DIR, "workflows", "snapshots")
SNAPSHOT_HOME = os.path.join(D3TALES_DIR, "workflows", "snapshots", "home.json")
SNAPSHOT_END_HOME = os.path.join(D3TALES_DIR, "workflows", "snapshots", "end_home.json")

# ---------  POTENTIOSTAT VARIABLES -------------
POTENTIOSTAT_A_ADDRESS = "COM6"
POTENTIOSTAT_A_EXE_PATH = r"C:\CH_Instruments\CHI650e\chi650e.exe"
POTENTIOSTAT_B_ADDRESS = "COM4"
POTENTIOSTAT_B_EXE_PATH = r"C:\CH_Instruments\CHI620e\chi620e.exe"

N_CYCLES = 0
SCAN_NUMBER = 1  # Not currently included in CV parameters
AVERAGE_OVER_DE = True
RECORD_EVERY_DE = 0.01  # Volts
SENSITIVITY = 1e-5  # A/V, current sensitivity
PULSE_WIDTH = 0.25  # sec, pulse width for CA
STEPS = 200  # number of steps for CA
CUT_BEGINNING = 0.007  # percentage as decimal of front of CV to cut
CUT_END = 0.0  # percentage as decimal of end of CV to cut
MIN_CV_STEPS = 6  # minimum number of CV steps

RECORD_EVERY_DT = 0.01  # seconds
I_RANGE = 'I_RANGE_10mA'
VS_INITIAL = False
TIME_OUT = 10  # seconds
TIME_AFTER_CV = 5  # seconds
MAX_WAIT_TIME = 4  # seconds, time to wait for station to be available

AUTO_VOLT_BUFFER = 0.25  # volts, buffer used in setting voltage range from benchmark peaks
ADD_MICRO_BUFFER = 0.15  # volts, additional buffer for setting voltage range from benchmark E1/2 for micro electrodes

# iR Compensation Variables
RCOMP_LEVEL = 0.85  # percentage as decimal of solution resistance to use
INITIAL_FREQUENCY = 10000
FINAL_FREQUENCY = 100000


# ---------  PROCESSING VARIABLES -------------
RUN_ANODIC = False
CONVERT_A_TO_MA = True
PLOT_CURRENT_DENSITY = True
MULTI_PLOT_XLABEL = "Potential (V) vs Ag/$Ag^+$"
MULTI_PLOT_YLABEL = None  # uses default D3TaLES API y label
MULTI_PLOT_LEGEND = "Scan Rate (V/s)"

PEAK_WIDTH = 0.5

CA_CALIB_STDS = {"11JNLU": 0.30, "06IGCB": 0.53, "05MYHH": 0}  # True conductivity for KCl and H2O, respectively TODO update
FORMAL_POTENTIALS = {"06TNKR": 0.30, "11DELT": 0.53, "05MYHH": 0}  # Formal potentials in V

# ---------  ARDUINO VARIABLES -------------
ARDUINO_ADDRESS = "COM4"

# ---------  LOCATION VARIABLES -------------
DISPENSE_STATIONS = ["solvent_01"]
MEASUREMENT_STATIONS = ["cv_potentiostat_A_01", "ca_potentiostat_B_01"]
ACTION_STATIONS = ["robot_grip", "stir-heat_01"]
STATIONS = DISPENSE_STATIONS + MEASUREMENT_STATIONS + ACTION_STATIONS
VIALS = [
    "S_01", "S_02", "S_03", "S_04",
    "A_01", "A_02", "A_03", "A_04",
    "B_01", "B_02", "B_03", "B_04",
    "C_01", "C_02", "C_03", "C_04",
]
SOLVENT_VIALS = {"solvent_01": "S_01"}
ELEVATOR_DICT = {"A_01": 1, "B_01": 2}

# ---------  FIREWORKS VARIABLES -------------
HOME_DIR = os.path.dirname(os.path.realpath(__file__))
LAUNCH_DIR = os.path.abspath('C:\\Users\\Lab\\D3talesRobotics\\launch_dir')
LAUNCHPAD = os.path.abspath(
    'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\launchpad_robot.yaml')
ROBOT_FWORKER = os.path.abspath(
    'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\fireworker_robot.yaml')
PROCESS_FWORKER = os.path.abspath(
    'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\fireworker_process.yaml')
INSTRUMENT_FWORKER = os.path.abspath(
    'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\fireworker_instrument.yaml')
