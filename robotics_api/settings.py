import os
from pathlib import Path

"""
This file contains various settings and configurations for a robotics experiment setup. It includes
operation settings, default conditions, instrument settings, processing settings, station configurations,
file paths, and more. Be sure to review all settings listed here before running a robotic workflow.

Copyright 2024, University of Kentucky
"""


# ---------  TESTING OPERATION SETTINGS -------------
RUN_POTENT = False
DISPENSE = True
STIR = True
WEIGH = True
PIPETTE = True
RUN_ROBOT = True
MOVE_ELEVATORS = True
CALIB_DATE = ''  # '2024_06_25'  The date that should be used to gather calibration data from database (should be blank for a real run)
POT_DELAY = 10  # seconds to delay in place of potentiostat measurement when RUN_POTENT is false.

# ---------  OPERATION SETTING -------------
WEIGH_SOLVENTS = True  # Perform mass measurement of solvent instead of relying on dispense volume estimation
RERUN_FIZZLED_ROBOT = True  # Rerun FIZZLED robot jobs at the end of a robot job.
FIZZLE_CONCENTRATION_FAILURE = False  # FIZZLE a processing job if concentration determination fails
FIZZLE_DIRTY_ELECTRODE = False  # FIZZLE a blank scan instrument job if the blank scan implied the electrode is dirty
EXIT_ZERO_VOLUME = True  # If a liquid dispense job adds 0 mL, exit this experiment by skipping actions for all childeren Fireworks
WAIT_FOR_BALANCE = True  # If balance connection fails, wait and try again

# ---------  DEFAULT CONDITIONS -------------
DEFAULT_TEMPERATURE = None  # "293K"
DEFAULT_CONCENTRATION = 0  # "0.01M"
DEFAULT_WORKING_ELECTRODE_RADIUS = 0.0011 / 2  # radius in cm
MICRO_ELECTRODES = True if DEFAULT_WORKING_ELECTRODE_RADIUS < 0.1 else False
DIRTY_ELECTRODE_CURRENT = 1e-8 if MICRO_ELECTRODES else 1e-5  # max current allowed (A) for a clean electrode

TIME_UNIT = "s"
MASS_UNIT = "g"
VOLUME_UNIT = "mL"
DENSITY_UNIT = "g/L"
POTENTIAL_UNIT = "V"
TEMPERATURE_UNIT = "K"
CONCENTRATION_UNIT = "M"

# ---------  ROBOT SETTINGS -------------
KINOVA_01_IP = "192.168.1.10"
VIAL_GRIP_TARGET = 60
OPEN_GRIP_TARGET = 40
PERTURB_AMOUNT = 0.07
STIR_PERTURB = 0.003

# ---------  POTENTIOSTAT SETTINGS -------------
POTENTIOSTAT_A_ADDRESS = "COM6"
POTENTIOSTAT_A_EXE_PATH = r"C:\Users\Lab\Desktop\chi650e.exe"
POTENTIOSTAT_B_ADDRESS = "COM4"
POTENTIOSTAT_B_EXE_PATH = r"C:\Users\Lab\Desktop\chi620e.exe"

IR_COMP = False  # Perform IR Compensation

# CV Default Settings
CV_SCAN_RATE = 0.01  # V/s
VOLTAGE_SEQUENCE = "0, 0.7, 0V"
CV_SAMPLE_INTERVAL = 0.01  # Volts
CV_SENSITIVITY = 1e-6  # A/V, current sensitivity
CUT_BEGINNING = 0.0  # percentage as decimal of front of CV to cut
CUT_END = 0.0  # percentage as decimal of end of CV to cut
# CA Default Settings
CA_RUN_DELAY = 60  # seconds
CA_SAMPLE_INTERVAL = 1e-6  # seconds
CA_SENSITIVITY = 1e-4  # A/V, current sensitivity
CA_PULSE_WIDTH = 1e-4  # sec, pulse width for CA
CA_STEPS = 200  # number of steps for CA
MAX_CA_VOLT = None  # V, maximum acceptable voltage for CA experiment
MIN_CA_VOLT = None  # V, minimum acceptable voltage for CA experiment

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
AMPLITUDE = 0.01

# ---------  PROCESSING SETTINGS -------------
RUN_ANODIC = False
CONVERT_A_TO_MA = True
PLOT_CURRENT_DENSITY = True
MULTI_PLOT_XLABEL = "Potential (V) vs Ag/$Ag^+$"
MULTI_PLOT_YLABEL = None  # uses default D3TaLES API y label
MULTI_PLOT_LEGEND = "Scan Rate (V/s)"

PEAK_WIDTH = 0.5

# ---------  CALIBRATION SETTINGS -------------
KCL_CALIB = True
DI_WATER_COND = 10
CA_CALIB_STDS = {  # True conductivity (S/m) at 25 C
    "11JNLU": 1.299,  # KCl
    "06IGCB": 0,  # H2O
    "Calib__01": 1,  # CA Calibration 1
    "Calib__02": 5,  # CA Calibration 2
    "Calib__03": 7,  # CA Calibration 3
}
FORMAL_POTENTIALS = {  # Formal potentials
    "CC1(C)CCCC(C)(C)N1[O]": "0.30 V",  # TEMPO, V vs. Ag/Ag+
    "[Cl-].[K+]": "0 V",  # KCl, NOT REAL, just a stand in!
}
SOLVENT_DENSITIES = {  # Formal potentials
    "O": "0.997 g/mL",  # H2O
    "CC#N": "0.786 g/mL",   # ACN
}

# ---------  PORT ADDRESS -------------
ARDUINO_PORT = "COM4"
BALANCE_PORT = "COM5"

# ---------  STATIONS -------------
DISPENSE_STATIONS = ["solvent_01", "solvent_02", "solvent_03", "solvent_04"]
MEASUREMENT_STATIONS = ["cv_potentiostat_A_01", "ca_potentiostat_B_01", "balance_01", "pipette_01"]
ACTION_STATIONS = ["robot_grip", "stir_01"]
STATIONS = DISPENSE_STATIONS + MEASUREMENT_STATIONS + ACTION_STATIONS
VIALS = [
    "S_01", "S_02", "S_03", "S_04",
    "A_01", "A_02", "A_03", "A_04",
    "B_01", "B_02", "B_03", "B_04",
    "C_01", "C_02", "C_03", "C_04",
]
RINSE_VIALS = {"cv_potentiostat_A_01": "S_01", "ca_potentiostat_B_01": "S_02"}
ELEVATOR_DICT = {"A_01": 1, "B_01": 2}

# ---------  PATH VARIABLES -------------
ROBOTICS_API = Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api"
TEST_DATA_DIR = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "test_data")
DATA_DIR = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "data")
SNAPSHOT_DIR = os.path.join(ROBOTICS_API, "snapshots")
SNAPSHOT_HOME = os.path.join(ROBOTICS_API, "snapshots", "home.json")
SNAPSHOT_END_HOME = os.path.join(ROBOTICS_API, "snapshots", "end_home.json")

# ---------  FIREWORKS PATH VARIABLES -------------
HOME_DIR = Path(__file__).resolve().parent.parent
LAUNCH_DIR = os.path.abspath('C:\\Users\\Lab\\D3talesRobotics\\launch_dir')
FW_CONFIG_DIR = ROBOTICS_API / 'fireworks' / 'fw_config'
LAUNCHPAD = ROBOTICS_API / 'fireworks' / 'fw_config' / 'launchpad_robot.yaml'
INIT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_initialize.yaml'
ROBOT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_robot.yaml'
PROCESS_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_process.yaml'
INSTRUMENT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_instrument.yaml'

if __name__ == "__main__":
    import subprocess
    # Activate the conda environment (note: this may require special handling in Python)
    subprocess.call("conda activate d3tales_robotics", shell=True)

    # Set environment variables with HOME_DIR
    os.environ[
        'PYTHONPATH'] = f'{HOME_DIR}:{HOME_DIR.parent}Packages/d3tales_api:{HOME_DIR.parent}Packages/hardpotato/src'
    os.environ['FW_CONFIG_FILE'] = f'{FW_CONFIG_DIR}/FW_config.yaml'
    os.environ['DB_INFO_FILE'] = f'{HOME_DIR}/db_infos.json'
    os.chdir(f'{HOME_DIR.parent}/launch_dir')