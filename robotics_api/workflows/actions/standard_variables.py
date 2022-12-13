import os
from pathlib import Path

VIAL_GRIP_TARGET = 60
RAISE_AMOUNT = 0.05
RUN_CV = True

# ---------  DEFAULT CONDITIONS -------------
DEFAULT_NUM_ELECTRONS = 1
DEFAULT_TEMPERATURE = 293
DEFAULT_CONCENTRATION = 0.10
DEFAULT_WORKING_ELECTRODE_AREA = 0.070685835

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
SCAN_NUMBER = 2  # Not currently included in CV parameters
AVERAGE_OVER_DE = True
RECORD_EVERY_DE = 0.01  # Volts
CUT_ENDS = 0.1  # percentage of front and end of CV to cut

RECORD_EVERY_DT = 0.01  # seconds
I_RANGE = 'I_RANGE_10mA'
VS_INITIAL = False
TIME_OUT = 10  # seconds
TIME_AFTER_CV = 5  # seconds


# ---------  ARDUINO VARIABLES -------------
ELEVATOR_ADDRESS = "COM4"

