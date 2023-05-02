import os
import math
from pathlib import Path

VIAL_GRIP_TARGET = 60
OPEN_GRIP_TARGET = 30
RAISE_AMOUNT = 0.05
RUN_CV = True

# ---------  DEFAULT CONDITIONS -------------
DEFAULT_NUM_ELECTRONS = 1
DEFAULT_TEMPERATURE = "293K"
DEFAULT_CONCENTRATION = "0.01M"
DEFAULT_WORKING_ELECTRODE_RADIUS = 1  # radius assumed in mm
DEFAULT_WORKING_ELECTRODE_AREA = (math.pi * (DEFAULT_WORKING_ELECTRODE_RADIUS ** 2)) * 0.01  # area given in cm^2

# ---------  PATH VARIABLES -------------
D3TALES_DIR = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api")
SNAPSHOT_DIR = os.path.join(D3TALES_DIR, "workflows", "snapshots")
SNAPSHOT_HOME = os.path.join(D3TALES_DIR, "workflows", "snapshots", "Home.json")
SNAPSHOT_END_HOME = os.path.join(D3TALES_DIR, "workflows", "snapshots", "EndHome.json")

# ---------  POTENTIOSTAT VARIABLES -------------

ECLIB_DLL_PATH = r"C:\EC-Lab Development Package\EC-Lab Development Package\\EClib64.dll"
POTENTIOSTAT_ADDRESS = "USB0"
POTENTIOSTAT_CHANNEL = 1

N_CYCLES = 0
SCAN_NUMBER = 1  # Not currently included in CV parameters
AVERAGE_OVER_DE = True
RECORD_EVERY_DE = 0.01  # Volts
CUT_BEGINNING = 0.0  # percentage of front of CV to cut
CUT_END = 0.0  # percentage of end of CV to cut
MIN_CV_STEPS = 6  # minimum number of CV steps

RECORD_EVERY_DT = 0.01  # seconds
I_RANGE = 'I_RANGE_10mA'
VS_INITIAL = False
TIME_OUT = 10  # seconds
TIME_AFTER_CV = 5  # seconds

# ---------  PLOTTING VARIABLES -------------
MULTI_PLOT_XLABEL = "Potential (V)"
MULTI_PLOT_YLABEL = "Current (A)"
MULTI_PLOT_LEGEND = "Scan Rate (V/s)"

# ---------  ARDUINO VARIABLES -------------
ARDUINO_DEFAULT_ADDRESS = "COM4"
ELEVATOR_ADDRESS = "COM4"
STIR_PLATE_ADDRESS = "COM4"