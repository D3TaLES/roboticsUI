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
DISPENSE = False
STIR = False
WEIGH = True
PIPETTE = False
RUN_ROBOT = False
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
RETURN_EXTRACTED_SOLN = False   # Return solution extracted via pipette after measurement made.

# ---------  DEFAULT CONDITIONS -------------
DEFAULT_TEMPERATURE = None  # "293K"
DEFAULT_CONCENTRATION = 0  # "0.01M"

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
MICRO_ELECTRODES_MAX_RADIUS = 0.1  # max radius of a ultra micro electrode, cm

POTENTIOSTAT_SETTINGS = {
    "cv_potentiostat_A_01": dict(
        address = "COM6",
        exe_path = r"C:\Users\Lab\Desktop\chi650e.exe",

        working_electrode_radius = 0.0011 / 2,  # radius in cm
        dirty_electrode_current = 1e-8,  # max current allowed (A) for a clean electrode

        # CV settings
        scan_rate = 0.01,  # V/s
        voltage_sequence = "0, 0.7, 0V",
        sample_interval = 0.01,  # Volts
        sensitivity = 1e-6,  # A/V, current sensitivity

        # IR Compensation settings
        ir_comp = False,  # Perform IR Compensation
        rcomp_level = 0.85,  # percentage as decimal of solution resistance to use
        low_freq = 10000,
        high_freq = 100000,
        amplitude = 0.01,
        time_after = 5,  # seconds

        # Processing settings
        cut_beginning = 0.0,  # percentage as decimal of front of CV to cut
        cut_end = 0.0,  # percentage as decimal of end of CV to cut
        benchmark_buffer = 0.15,  # volts, additional buffer for setting voltage range from benchmark E1/2 for micro electrodes

    ),
    "cv_potentiostat_A_02": dict(
        address = "COM6",
        exe_path = r"C:\Users\Lab\Desktop\chi650e.exe",

        working_electrode_radius = 0.07,  # radius in cm
        dirty_electrode_current = 1e-8,  # max current allowed (A) for a clean electrode

        # CV settings
        scan_rate = 0.1,  # V/s
        voltage_sequence = "0, 0.7, 0V",
        sample_interval = 0.01,  # Volts
        sensitivity = 1e-6,  # A/V, current sensitivity

        # IR Compensation settings
        ir_comp = False,  # Perform IR Compensation
        rcomp_level = 0.85,  # percentage as decimal of solution resistance to use
        low_freq = 10000,
        high_freq = 100000,
        amplitude = 0.01,
        time_after = 5,  # seconds

        # Processing settings
        cut_beginning = 0.0,  # percentage as decimal of front of CV to cut
        cut_end = 0.0,  # percentage as decimal of end of CV to cut
        benchmark_buffer = 0.25,  # volts, buffer used in setting voltage range from benchmark peaks

    ),
    "ca_potentiostat_B_01": dict(
        address = "COM4",
        exe_path = r"C:\Users\Lab\Desktop\chi620e.exe",

        run_delay = 60,  # seconds
        sample_interval = 1e-6,  # seconds
        sensitivity = 1e-4,  # A/V, current sensitivity
        pulse_width = 1e-4,  # sec, pulse width for CA
        steps = 200,  # number of steps for CA
        volt_min = None,  # V, minimum acceptable voltage for CA experiment
        volt_max = None,  # V, maximum acceptable voltage for CA experiment
        time_after = 5,  # seconds
    ),
}

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
ELEVATOR_DICT = {"A_01": 1, "B_01": 2, "A_02": 3}

# ---------  PATH VARIABLES -------------
HOME_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = HOME_DIR.parent / "data"
LAUNCH_DIR = HOME_DIR.parent / 'launch_dir'
TEST_DATA_DIR = HOME_DIR / "test_data"
ROBOTICS_API = HOME_DIR / "robotics_api"

SNAPSHOT_DIR = ROBOTICS_API /"snapshots"
SNAPSHOT_HOME = SNAPSHOT_DIR / "home.json"
SNAPSHOT_END_HOME = SNAPSHOT_DIR / "end_home.json"

# ---------  FIREWORKS PATH VARIABLES -------------
FW_CONFIG_DIR = ROBOTICS_API / 'fireworks' / 'fw_config'
LAUNCHPAD = ROBOTICS_API / 'fireworks' / 'fw_config' / 'launchpad_robot.yaml'
INIT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_initialize.yaml'
ROBOT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_robot.yaml'
PROCESS_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_process.yaml'
INSTRUMENT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_instrument.yaml'
