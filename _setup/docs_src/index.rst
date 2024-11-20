
D\ :sup:`3`\ TaLES Robotics UI and API Documentation!
=================================================================

.. |D3TaLES| replace:: D\ :sup:`3`\ TaLES

Here you will find complete documentation for the |D3TaLES| robotics Python software
hosted in the `roboticsUI repository <https://github.com/D3TaLES/roboticsUI>`_ GitHub
repository. This includes documentation ExpFlow and Robotics Robotics App user
interfaces as well as the Robotics API for interacting with the robotics
hardware directly.


RoboticsUI Contents
===================

The `roboticsUI repository <https://github.com/D3TaLES/roboticsUI>`_ contains several directories:

- ``_kbio``: Python API for the Kinova robot. These files are taken directly from the commercial `Kinova Python API <https://github.com/Kinovarobotics/Kinova-kortex2_Gen3_G3L>`_. They should not be edited.
- ``GUI``: Code for the robotics Robotics App. Uses Tkinter.
- ``robotics_api``: Robotics API that manages robotic workflows. (More discussion below.)
- ``test_data``: Example, standard, and test experimental data.


.. image:: media/software_setup.png
   :alt: General software setup

.. toctree::
   :maxdepth: 3
   :caption: Overview

   installation
   quickstart
   terminology_setup
   robot_run_checklist
   common_errors

.. toctree::
   :maxdepth: 3
   :caption: User Interfaces

   expflow
   desktop_app

.. toctree::
   :maxdepth: 3
   :caption: Robotics API

   api_overview
   settings
   fireworks
   actions
   utils
   databases

.. toctree::
   :maxdepth: 4
   :caption: Raw API Code Docs

   robotics_api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
