# Module - Utils

This module is the lowest level of abstraction and contains many base functions for interacting with the robot and instruments. It should not need to be edited very often. Files include:
* `base_utils`: basic utility functions
* `kinova_gripper`: functions adapted from official Kortex API to operate the robot gripper
* `kinova_move`: functions adapted from official Kortex API to move the robot to snapshots
* `kinova_utils`: basic utility functions adapted from official Kortex API
* `mongo_dbs`: base functions and classes for interacting with MongoDB databases
* `potentiostat_hp`: example functions for using hardpotato software for interacting with CHI potentiostats
* `potentiostat_kbio`: (no longer used!) base functions and classes for interacting with kbio potentiostats
* `processing_utils`: functions for processing

## Note about Robotic Motion 

The robotic workspace is divide into zones. When directing movement about the workspace, the Robot API considers current 
and target zones. In general, when moving to a station, the robot arm is directed to move to the `pre_` snapshot, then 
to the station snapshot (including a `rise_amount` where necessary). However, if the robot arm's existing zone is 
different from its target zone, the arm will move to the exiting zone home position, then the target zone home position. 
Only then will it start the process of moving to the station. This process minimized the risk of the robot arm colliding 
with workspace hardware.

```{image} media/robot_zones.png
:alt: Robot Zones
```
