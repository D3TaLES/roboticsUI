
D\ :sup:`3`\ TaLES Robotics User Interface and API Documentation!
=================================================================

.. |D3TaLES| replace:: D\ :sup:`3`\ TaLES

Here you will find complete documentation for the |D3TaLES| robotics Python software
hosted in the `roboticsUI repository <https://github.com/D3TaLES/roboticsUI>` GitHub
repository. This includes documentation ExpFlow and Robotics Desktop App user
interfaces as well as the Robotics API for interacting with the robotics
hardware directly.


RoboticsUI Contents
===================

The `roboticsUI repository <https://github.com/D3TaLES/roboticsUI>` contains several directories:

- ``_kbio``: Python API for the Kinova robot. These files are taken directly from the commercial
   `Kinova Python API <https://github.com/Kinovarobotics/Kinova-kortex2_Gen3_G3L>`_. They should not be edited.
- ``GUI``: Code for the robotics desktop app. Used Tkinter.
- ``robotics_api``: Robotics API that manages robotic workflows. (More discussion below.)
- ``test_data``: Example, standard, and test experimental data.


Robotics API
============

The Robotics API is designed to manage the D\ :sup:`3`\ TaLES robotics system. It consists of three modules, each of increasing abstraction:

- ``utils``: Utility functions for robot movements, instrument interactions, processing, database interactions, etc. This module offers the lowest level of abstraction.
- ``actions``: Classes for managing status, position, and content for vials, stations, or standards. These data are stored in MongoDB databases.
- ``fireworks``: With the highest level of abstraction, this module contains classes and functions for FireWorks Workflows, FireWorks, and FireTasks.

The RoboticsAPI also contains the following items:

- ``settings.py``: A single file with all adjustable settings for robotics operations. **Always review this file before operating the robotic system!**
- ``snapshots``: A directory containing Kinova snapshots (JSON files) for positions
  for the robot. Files named ``<station_name>.json`` give the position of the robot where
  the vial sits directly in the station. Files named ``pre_<station_name>.json`` give the position
  the robot should be before/after moving to the station. Note that some snapshots give Cartesian
  coordinates while others give actuator angles.

.. image:: media/robotics_api_scheme.png




.. toctree::
   :maxdepth: 3
   :caption: Overview

   Installation
   TeminologySetup
   Quickstart
   RobotRunChecklist
   CommonErrors

.. toctree::
   :maxdepth: 3
   :caption: User Interfaces

   ExpFlow
   DesktopApp

.. toctree::
   :maxdepth: 3
   :caption: API Modules and More

   Settings
   Fireworks
   Actions
   Databases
   UtilsSnapshots

.. toctree::
   :maxdepth: 1
   :caption: Detailed Code Docs

   robotics_api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
