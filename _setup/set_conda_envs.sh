#!/bin/bash

# Define paths for Linux/Mac and Windows
BASE_DIR_LIN="/c/Users/Lab/D3talesRobotics"
BASE_DIR_WIN="C:\\Users\\Lab\\D3talesRobotics"

CONDA_ENV_NAME="d3tales_robotics"  # Name of your Conda environment
CONDA_ENV_PATH="$HOME/miniconda3/envs/$CONDA_ENV_NAME"
echo "Conda environment path: $CONDA_ENV_PATH"

# Create activate.d and deactivate.d directories
mkdir -p "$CONDA_ENV_PATH/etc/conda/activate.d"
mkdir -p "$CONDA_ENV_PATH/etc/conda/deactivate.d"

### LINUX/MAC ACTIVATION SCRIPT
ACTIVATE_SCRIPT_LIN="$CONDA_ENV_PATH/etc/conda/activate.d/set_env_vars.sh"
echo "Creating Linux/Mac activation script: $ACTIVATE_SCRIPT_LIN..."
cat <<EOL > "$ACTIVATE_SCRIPT_LIN"
#!/bin/bash
export FW_CONFIG_FILE=$BASE_DIR_LIN/roboticsUI/robotics_api/fireworks/fw_config/FW_config.yaml
export DB_INFO_FILE=$BASE_DIR_LIN/roboticsUI/db_infos.json
export PYTHONPATH=$BASE_DIR_LIN/roboticsUI:\$BASE_DIR_LIN/Packages/d3tales_api:\$BASE_DIR_LIN/Packages/hardpotato/src
EOL
chmod +x "$ACTIVATE_SCRIPT_LIN"

### LINUX/MAC DEACTIVATION SCRIPT
DEACTIVATE_SCRIPT_LIN="$CONDA_ENV_PATH/etc/conda/deactivate.d/unset_env_vars.sh"
echo "Creating Linux/Mac deactivation script: $DEACTIVATE_SCRIPT_LIN..."
cat <<EOL > "$DEACTIVATE_SCRIPT_LIN"
#!/bin/bash
unset FW_CONFIG_FILE
unset DB_INFO_FILE
unset PYTHONPATH
EOL
chmod +x "$DEACTIVATE_SCRIPT_LIN"

### WINDOWS ACTIVATION SCRIPT
ACTIVATE_SCRIPT_WIN="$CONDA_ENV_PATH/etc/conda/activate.d/set_env_vars.bat"
echo "Creating Windows activation script: $ACTIVATE_SCRIPT_WIN..."
cat <<EOL > "$ACTIVATE_SCRIPT_WIN"
@echo off
set FW_CONFIG_FILE=$BASE_DIR_WIN\\roboticsUI\\robotics_api\\fireworks\\fw_config\\FW_config.yaml
set DB_INFO_FILE=$BASE_DIR_WIN\\roboticsUI\\db_infos.json
set PYTHONPATH=$BASE_DIR_WIN\\roboticsUI;$BASE_DIR_WIN\\Packages\\d3tales_api;$BASE_DIR_WIN\\Packages\\hardpotato\\src;%PYTHONPATH%
EOL

### WINDOWS DEACTIVATION SCRIPT
DEACTIVATE_SCRIPT_WIN="$CONDA_ENV_PATH/etc/conda/deactivate.d/unset_env_vars.bat"
echo "Creating Windows deactivation script: $DEACTIVATE_SCRIPT_WIN..."
cat <<EOL > "$DEACTIVATE_SCRIPT_WIN"
@echo off
set FW_CONFIG_FILE=
set DB_INFO_FILE=
set PYTHONPATH=
EOL

echo "Environment variable setup complete for Linux/Mac and Windows."
