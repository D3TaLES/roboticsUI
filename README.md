# roboticsUI
This is the repo for robotics user interface. Uses Tkinter.

For robotics PC, set environment variables: 
```commandline
conda activate d3tales_robotics
set PYTHONPATH=C:\Users\Lab\D3talesRobotics\roboticsUI\
set FW_CONFIG_FILE=C:\Users\Lab\D3talesRobotics\roboticsUI\d3tales_fw\Robotics\config\FW_config.yaml
cd C:\Users\Lab\D3talesRobotics\launch_dir
```

To view jobs: 
```commandline
lpad webgui
```


To run the test job: 
```commandline
lpad rerun_fws -i 223 
rlaunch singleshot
```