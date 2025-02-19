import os
import subprocess
from pathlib import Path

"""
This file contains various settings and configurations for a robotics experiment setup. It includes
operation settings, default conditions, instrument settings, processing settings, station configurations,
file paths, and more. Be sure to review all settings listed here before running a robotic workflow.

Copyright 2024, University of Kentucky, Rebekah Duke-Crockett
"""

# ---------  TESTING OPERATION SETTINGS -------------
RUN_POTENT = False
DISPENSE = False
STIR = False
WEIGH = False
PIPETTE = False
RUN_ROBOT = False
MOVE_ELEVATORS = False
POT_DELAY = 2  # seconds to delay in place of potentiostat measurement when RUN_POTENT is false.

# ---------  OPERATION SETTING -------------
WEIGH_SOLVENTS = True  # Perform mass measurement of solvent instead of relying on dispense volume estimation
RERUN_FIZZLED_ROBOT = True  # Rerun FIZZLED robot jobs at the end of a robot job.
FIZZLE_CONCENTRATION_FAILURE = False  # FIZZLE a processing job if concentration determination fails
CHECK_CLEAN_ELECTRODES = True  # Check stations database for electrode cleanliness
FIZZLE_DIRTY_ELECTRODE = True  # FIZZLE a blank scan instrument job if the blank scan implied the electrode is dirty
EXIT_ZERO_VOLUME = True  # If a liquid dispense job adds 0 mL, exit experiment by skipping all children Fireworks
WAIT_FOR_BALANCE = True  # If balance connection fails, wait and try again
MAX_DB_WAIT_TIME = 10  # Maximum seconds to wait for database response
MAX_BALANCE_READS = 5  # Maximum number of times to attempt to read the balance.
MAX_PIPETTE_VOL = 0.6  # Maximum volume in mL the pipette can extract

# ---------  DEFAULT CONDITIONS -------------
DEFAULT_TEMPERATURE = None  # "293K"
DEFAULT_CONCENTRATION = None  # "0.01M"

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
ZONE_DIVIDERS = [30, 180, 328]

# ---------  INSTRUMENT SETTINGS -------------
ULTRA_MICRO_ELECTRODES_MAX_RADIUS = 0.01  # max radius of a ultra micro electrode, cm

# NOTE: A potentiostat setting cannot be None
POTENTIOSTAT_SETTINGS = {
    "cvUM_potentiostat_A_01": dict(
        address="COM6",
        exe_path=r"C:\Users\Lab\Desktop\chi620e.exe",

        working_electrode_radius=0.0011 / 2,  # radius in cm
        electrode_working="11 micrometer carbon micro electrode",
        electrode_counter="Pt coil counter",
        electrode_reference="Ag/Ag+ reference",
        dirty_electrode_current=1e-8,  # max current allowed (A) for a clean electrode

        # Default CV settings
        scan_rate=0.01,  # V/s
        voltage_sequence="0.5, -0.2, 0V",
        sample_interval=0.01,  # Volts
        sensitivity=1e-4,  # A/V, current sensitivity
        quiet_time=2,  # s

        # IR Compensation settings
        ir_comp=False,  # Perform IR Compensation
        rcomp_level=0.85,  # percentage as decimal of solution resistance to use
        low_freq=10000,
        high_freq=100000,
        amplitude=0.01,
        time_after=5,  # seconds

        # Processing settings
        cut_beginning=0.0,  # percentage as decimal of front of CV to cut
        cut_end=0.0,  # percentage as decimal of end of CV to cut
        benchmark_buffer=0.15,
        # volts, additional buffer for setting voltage range from benchmark E1/2 for micro electrodes

    ),
    "cv_potentiostat_B_01": dict(
        address="COM1",
        exe_path=r"C:\Users\Lab\Desktop\chi650e.exe",

        working_electrode_radius=0.3 / 2,  # radius in cm
        electrode_working="3 mm glassy carbon electrode",
        electrode_counter="Pt coil counter",
        electrode_reference="Ag/Ag+ reference",
        dirty_electrode_current=1e-5,  # max current allowed (A) for a clean electrode

        # Default CV settings
        scan_rate=0.1,  # V/s
        voltage_sequence="0.5, -0.2, 0V",
        sample_interval=0.01,  # Volts
        sensitivity=1e-3,  # A/V, current sensitivity
        quiet_time=2,  # s

        # IR Compensation settings
        ir_comp=True,  # Perform IR Compensation
        rcomp_level=0.85,  # percentage as decimal of solution resistance to use
        low_freq=10000,
        high_freq=100000,
        amplitude=0.01,
        time_after=5,  # seconds

        # Processing settings
        cut_beginning=0.0,  # percentage as decimal of front of CV to cut
        cut_end=0.0,  # percentage as decimal of end of CV to cut
        benchmark_buffer=0.4,  # volts, buffer used in setting voltage range from benchmark peaks

    ),
    "ca_potentiostat_C_01": dict(
        address="COM7",
        exe_path=r"C:\Users\Lab\Desktop\chi604d.exe",

        # Default CA settings
        quiet_time=90,  # s
        sample_interval=1e-6,  # seconds
        sensitivity=1e-4,  # A/V, current sensitivity
        pulse_width=1e-4,  # sec, pulse width for CA
        steps=200,  # number of steps for CA
        volt_min=False,  # V, minimum acceptable voltage for CA experiment
        volt_max=False,  # V, maximum acceptable voltage for CA experiment
        voltage_sequence="0.025, -0.025 V",  # V, maximum acceptable voltage for CA experiment
        time_after=5,  # seconds
    ),
}

# ---------  PROCESSING SETTINGS -------------
RUN_ANODIC = True
CONVERT_A_TO_MA = True
PLOT_CURRENT_DENSITY = True
CV_PLOT_XLABEL = "Potential (V) vs Ag/$Ag^+$"
CV_PLOT_YLABEL = None  # uses default D3TaLES API y label
CV_PLOT_LEGEND = "Scan Rate (V/s)"

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
    "CC1(C)CCCC(C)(C)N1[O]": "0.367 V",  # TEMPO, V vs. Ag/Ag+  TODO Figure out what value to actually use
    "[CH-]1C=CC=C1.[CH-]1C=CC=C1.[Fe+2]": "0 V",  # Fc, NOT REAL, just a stand in!
}
SOLVENT_DENSITIES = {  # Formal potentials
    "O": "0.997 g/mL",  # H2O
    "CC#N": "0.786 g/mL",  # ACN
}

# ---------  PORT ADDRESS -------------
ARDUINO_PORT = "COM4"
BALANCE_PORT = "COM5"

# ---------  STATIONS -------------
DISPENSE_STATIONS = ["solvent_01", "solvent_02", "solvent_03", "solvent_04"]
MEASUREMENT_STATIONS = ["cvUM_potentiostat_A_01", "cv_potentiostat_B_01", "ca_potentiostat_C_01",
                        "balance_01", "pipette_01", "temperature_01"
                        ]
ACTION_STATIONS = ["robot_grip", "stir_01"]
STATIONS = DISPENSE_STATIONS + MEASUREMENT_STATIONS + ACTION_STATIONS
VIALS = [
    "S_01", "S_02", "S_03", "S_04",
    "A_01", "A_02", "A_03", "A_04",
    "B_01", "B_02", "B_03", "B_04",
    "C_01", "C_02", "C_03", "C_04",
]
RINSE_VIALS = {"cvUM_potentiostat_A_01": "S_01", "cv_potentiostat_B_01": "S_02", "ca_potentiostat_C_01": "S_03"}
ELEVATOR_DICT = {"A_01": 1, "B_01": 2, "C_01": 3}

# ---------  PATH VARIABLES -------------
HOME_DIR = Path(__file__).resolve().parent.parent
PARENT_DIR = HOME_DIR.parent
DATA_DIR = PARENT_DIR / "data"
LAUNCH_DIR = PARENT_DIR / 'launch_dir'
TEST_DATA_DIR = HOME_DIR / "test_data"
ROBOTICS_API = HOME_DIR / "robotics_api"
DB_INFO_FILE = HOME_DIR / 'db_infos.json'

SNAPSHOT_DIR = ROBOTICS_API / "snapshots"
SNAPSHOT_HOME = SNAPSHOT_DIR / "home.json"
SNAPSHOT_END_HOME = SNAPSHOT_DIR / "end_home.json"

# ---------  FIREWORKS PATH VARIABLES -------------
FW_CONFIG_DIR = ROBOTICS_API / 'fireworks' / 'fw_config'
LAUNCHPAD = ROBOTICS_API / 'fireworks' / 'fw_config' / 'launchpad_robot.yaml'
INIT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_initialize.yaml'
ROBOT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_robot.yaml'
PROCESS_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_process.yaml'
INSTRUMENT_FWORKER = ROBOTICS_API / 'fireworks' / 'fw_config' / 'fireworker_instrument.yaml'

if __name__ == "__main__":
    # Activate the conda environment (note: this may require special handling in Python)
    subprocess.call("conda activate d3tales_robotics", shell=True)
    os.chdir(f'{PARENT_DIR}/launch_dir')

    # Set environment variables with HOME_DIR
    py_path = f"{HOME_DIR}:{PARENT_DIR/'Packages'/'d3tales_api'}:{PARENT_DIR/'Packages'/'hardpotato'/'src'}"
    os.environ['FW_CONFIG_FILE'] = os.path.abspath(FW_CONFIG_DIR / 'FW_config.yaml')
    os.environ['DB_INFO_FILE'] = os.path.abspath(DB_INFO_FILE)
    os.environ['PYTHONPATH'] = py_path

    # print(os.environ['FW_CONFIG_FILE'])
    # print(os.environ['DB_INFO_FILE'])
    # print(os.environ['PYTHONPATH'])

    print("conda activate d3tales_robotics")
    print(f"export FW_CONFIG_FILE={FW_CONFIG_DIR / 'FW_config.yaml'}".replace('\\', "/").replace("C:", "/c"))
    print(f"export DB_INFO_FILE={HOME_DIR / 'db_infos.json'}".replace('\\', "/").replace("C:", "/c"))
    print(f"export PYTHONPATH={py_path}".replace('\\', "/").replace("C:", "/c"))
