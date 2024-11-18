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
