# RoboticsUI
This repo contains a user interface for the D3TaLES robotics system at the University of Kentucky
and the Center for Applied Energy Research

Full Documentation for the RoboticsUI repository including the 
Robotics API can be found [HERE]().  

## RoboticsUI Contents

This repository contains several directories:

* `_kbio`: Python API for the Kinova robot. These files are taken directly from the commercial 
[Kinova Python API](https://github.com/Kinovarobotics/Kinova-kortex2_Gen3_G3L). They should not be edited.
* `GUI`: Code for the robotics desktop app. Used Tkinter.
* `robotics_api``: Robotics API that manages robotic workflows. (More discussion below.)
* `test_data`: Example, standard, and test experimental data.
* `docs`: Documentation files for the Robotics API
* `docs_src`: Sphinx source documentation files for the Robotics API 