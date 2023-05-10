

For robotics PC, set environment variables: 
```bash
conda activate d3tales_robotics
set PYTHONPATH=C:\Users\Lab\D3talesRobotics\roboticsUI\
set FW_CONFIG_FILE=C:\Users\Lab\D3talesRobotics\roboticsUI\robotics_api\config\FW_config.yaml
set DB_INFO_FILE=C:\Users\Lab\D3talesRobotics\roboticsUI\robotics_api\db_infos.json
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

To pause all electrode test jobs: 
```bash
lpad pause_fws -s READY
```