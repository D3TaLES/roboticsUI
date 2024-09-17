# Settings and Snapshots

## Settings

The `settings.py` contains master settings for all robotic system operations. It includes operation settings, default conditions, instrument settings, processing settings, station configurations, file paths, and more. **Be sure to review all settings listed here before running a robotic workflow!**

### TESTING OPERATION SETTINGS
These settings indicate whether or not hardware features should actually be used when jobs are launched. For example, if `RUN_POTENT` is set to `False`, no signal will be sent to the potentiostats and no measurements will actually be gathered; if `RUN_ROBOT` is set to `False`, the robot will not actually move. These exist for testing only. When running a real workflow, these should all be set to `True`. Additionally, this section contains `CALIB_DATE`, the date that should be used to gather calibration data from database (should be blank for a real run), and `POT_DELAY`, the seconds to delay in place of potentiostat measurement when `RUN_POTENT` is `False`.

### OPERATION SETTING
Setting for system operations including `RERUN_FIZZLED_ROBOT`, `FIZZLE_CONCENTRATION_FAILURE`, `FIZZLE_DIRTY_ELECTRODE`,
`EXIT_ZERO_VOLUME`, and `WAIT_FOR_BALANCE`. More explination for each setting exists in the `settings.py` file.

### DEFAULT CONDITIONS
Default values for several condition parameters including temperature, concentration, and working electrode radius. This section also contains the setting for default units of measurements.

### ROBOT SETTINGS
Robot settings including the robot IP address, the grip target values for open and close, and perturbation amounts.

### POTENTIOSTAT SETTINGS
Comp ports and executions files for the instrumnets.

### MEASUREMENT DEFAULT SETTINGS (CA, CV, iR Comp, etc. )
Default instrument measurement settings such as sample interval, sensitivity, pulse width, wait times, etc. These are used when the ExpFlow Robotic Workflow action parameters were left blank.

### PROCESSING SETTINGS
Processing settings such as processing procedures and plotting settings.

### CALIBRATION SETTINGS
Setting for calibration jobs such as whether to perform a KCl CA calibration and the conductivity of DI water. This section also contains dictionaries of FORMAL_POTENTIALS and SOLVENT_DENSITIES that are used in generating the reagents database collection. 

### PORT ADDRESS
COM ports for Arduino, balance, etc.

### STATIONS
List of all hardware stations. These include `DISPENSE_STATIONS`, `MEASUREMENT_STATIONS`, `ACTION_STATIONS`, and `VIALS`. If a station or vial is listed here, the robot will think it is an option for executing jobs. This section also contains the `RINSE_VIALS` setting which matches each measurement station with the vial home position that should be used to rinse it. There should be one rinse vial per measurementstation. The `ELEVATOR_DICT` setting pairs the elevator name (e.g., "A_01") with its Aurdino identifier (e.g., 1).

### PATH VARIABLES (and FIREWORKS PATH VARIABLES)
Paths for key directories and files such as the data storage directory, key snapshots, and FireWorks configuration files.


## Snapshots

The snapshots directory contains JSON snapshots for each station and vial home location. Files named ``<station_name>.json`` give the position of the robot where the vial sits directly in the station. Files named ``pre_<station_name>.json`` give the position the robot should be before/after moving to the station. Note that some snapshots give Cartesian coordinates while others give actuator angles. Snapshots for stations and home positions where the robot needs to move above/below the final location before and after going there (`raies_amount` in `standard_action` classes) must be Cartesian.

The snapshots are generated and adjusted through the Kinova Web Application (http://192.168.1.10/, when the robot is turned on). They are then downloaded to the snapshots directory and given the appropriate name.
