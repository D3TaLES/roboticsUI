import os
from pathlib import Path

VIAL_GRIP_TARGET = 60

# ---------  PATH VARIABLES -------------
D3TALES_DIR = os.path.join(Path("C:/Users") / "Lab" / "D3talesRobotics" / "roboticsUI" / "robotics_api")
SNAPSHOT_DIR = os.path.join(D3TALES_DIR, "workflows", "snapshots")
SNAPSHOT_HOME = os.path.join(D3TALES_DIR, "workflows", "snapshots", "Home.json")
SNAPSHOT_END_HOME = os.path.join(D3TALES_DIR, "workflows", "snapshots", "EndHome.json")

# ---------  POTENTIOSTAT VARIABLES -------------

ECLIB_DLL_PATH = r"C:\EC-Lab Development Package\EC-Lab Development Package\\EClib64.dll"
POTENTIOSTAT_ADDRESS = "USB0"
POTENTIOSTAT_CHANNEL = 1

VS_INITIAL = False
N_CYCLES = 1
SCAN_NUMBER = 1
RECORD_EVERY_DT = 0.1  # seconds
RECORD_EVERY_DE = 0.01  # Volts
I_RANGE = 'I_RANGE_10mA'
TIME_OUT = 10  # seconds
TIME_AFTER_CV = 5  # seconds
DEFAULT_WORKING_ELECTRODE_AREA = 0.070685835


# ---------  ARDUINO VARIABLES -------------
ELEVATOR_ADDRESS = "COM4"

