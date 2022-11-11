

For robotics PC, set environment variables: 
```bash
conda activate d3tales_robotics
set PYTHONPATH=C:\Users\Lab\D3talesRobotics\roboticsUI\
set FW_CONFIG_FILE=C:\Users\Lab\D3talesRobotics\roboticsUI\d3tales_fw\Robotics\config\FW_config.yaml
cd C:\Users\Lab\D3talesRobotics\launch_dir
```

To view jobs: 
```bash
lpad webgui
```


To run the test job: 
```bash
lpad rerun_fws -i 223 
rlaunch singleshot
```