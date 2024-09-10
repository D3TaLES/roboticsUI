
Welcome to the |D3TaLES| Robotics User Interface and API documentation!
===========================================

.. |D3TaLES| replace:: D\ :sup:`3`\ TaLES
.. image:: media/D3TalES_logo_transparent_robotics.png
   :target: D3TaLES_api_logo.png
   :alt: D3TaLES Robotics logo


API designed to manage the D\ :sup:`3`\ TaLES robotics system.

RoboticsUI Contents
==================

This repository contains several directories:

- ``_kbio``: Python API for the Kinova robot. These files are taken directly from the commercial
   `Kinova Python API <https://github.com/Kinovarobotics/Kinova-kortex2_Gen3_G3L>`_. They should not be edited.
- ``GUI``: Code for the robotics desktop app. Used Tkinter.
- ``robotics_api``: Robotics API that manages robotic workflows. (More discussion below.)
- ``test_data``: Example, standard, and test experimental data.

Robotics API
============

The RoboticsAPI consists of three modules, each of increasing abstraction:

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

.. image:: docs/media/robotics_api_scheme.png


.. toctree::
   :maxdepth: 1
   :caption: Overview

   Installation
   Quickstart
   Robot Run Checklist
   Common Errors

.. toctree::
   :maxdepth: 1
   :caption: Robotics API

   Settings
   Fireworks
   Actions
   Databases
   Utils and Snapshots



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

