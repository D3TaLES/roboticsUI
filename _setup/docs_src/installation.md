# Installation and Setup
The Robotics API is for installation on the workstation controlling a robotic setup.
There should be no need to install this unless setting up a new robotic setup.

## Software Installation

### Clone this GitHub Repository
Clone this repository on the robotics workstation. Ensure you have SSH privileges.
```bash
git clone git@github.com:D3TaLES/roboticsUI.git
````

### Create Environment
The primary package this repo requires is the [D<sup>3</sup>TaLES API](https://github.com/D3TaLES/d3tales_api).
It is recommended that you create an environment to host the required packages.
```bash
conda create --name d3tales_robotics
conda activate d3tales_robotics
conda install -c conda-forge fireworks
pip install git+https://github.com/d3tales/d3tales_api.git
```

#### Get D3TaLES fork of hardpotato
The Robotics API uses a forked version of the [hardpotato](https://github.com/D3TaLES/hardpotato) software for interacting with CHI potentiostats. This must be cloned and added to the PYTHONPATH (see next section). On the current Robotics Workstation, that would look like:

```bash
cd 'C:\Users\Lab\D3talesRobotics\Packages\'
git clone git@github.com:D3TaLES/hardpotato.git
```

### Activate Environment
Note that you must set the `DB_INFO_FILE` environment variable as stipulated in the
[D<sup>3</sup>TaLES API Docs](https://github.com/D3TaLES/d3tales_api).You will also
need to set the fireworks variable `FW_CONFIG_FILE` and a `PYTHONPATH`. For robotics PC (WINDOWS),
set environment variables run the command:

```bash
python robotics_api/settings.py
```
Then, copy the output and run that in your path terminal.

ALTERNATIVELY, set the environment variables manually with the following 
commands, making sure to insert the correct paths. 

```bash
conda activate d3tales_robotics
$env:PYTHONPATH='C:\Users\Lab\D3talesRobotics\roboticsUI;C:\Users\Lab\D3talesRobotics\Packages\d3tales_api;C:\Users\Lab\D3talesRobotics\Packages\hardpotato\src'
$env:FW_CONFIG_FILE='C:\Users\Lab\D3talesRobotics\roboticsUI\robotics_api\management\config\FW_config.yaml'
$env:DB_INFO_FILE='C:\Users\Lab\D3talesRobotics\roboticsUI\db_infos.json'
cd C:\Users\Lab\D3talesRobotics\launch_dir
```


## Hardware Setup

The hardware should be arranged on the table according to the desired layout.

### Robot Setup
* Make a snapshot of where the robot arm should be at each station via the Kinova web interface
(http://192.168.1.10/). This position should be the 
position of the robot arm *when the action happens* (i.e., when the liquid is dispensed or when the
robot releases the vial at its home). The `raise_amount` for each station can be set in the Robotics API
{ref}`standard actions <actions:2. standard actions>`. Previous
snapshots can be found and uploaded at `robotics_api/snapshots/`

 * Set up Kinova protection zones (again, on the Kinova web interface, 
http://192.168.1.10/) for any place you do not want the robot traveling. Previous
protection zones can be found and uploaded at `robotics_api/snapshots/protection_zones/`


### Station Setup 
 
*Documentation in progress*
