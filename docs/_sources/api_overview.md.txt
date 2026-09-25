# Overview

> Warning! The following two sections contain very technical information about the code supporting the robotics operations. Read only if you are interested in understanding / modifying this code.

The Robotics API is designed to manage the robotics system. It consists of three modules, each of increasing abstraction:

- ``utils``: Utility functions for robot movements, instrument interactions, processing, database interactions, etc. This module offers the lowest level of abstraction. ()
- ``actions``: Classes for managing status, position, and content for vials, stations, or standards. These data are stored in MongoDB databases.
- ``fireworks``: With the highest level of abstraction, this module contains classes and functions for FireWorks Workflows, FireWorks, and FireTasks.

The RoboticsAPI also contains the following items (for more see {ref}`settings:settings and snapshots`):

- ``settings.py``: A single file with all adjustable settings for robotics operations. **Always review this file before operating the robotic system!**
- ``snapshots``: A directory containing Kinova snapshots (JSON files) for positions
  for the robot.

```{image} media/robotics_api_scheme.png
:alt: Robotics API Schema
```
