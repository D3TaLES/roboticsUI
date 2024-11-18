---
title: Robot Run Checklist
author: Rebekah Duke-Crockett
date: 2024-11-18
description: Checklist for preparing a robot run in the robotics system.
tags:
  - robotics
  - checklist
---

# Robot Run Checklist

## Before Running a Workflow

* Load Robotics Workflow
    ```{checkbox-list}
    - Create Robotics Workflow on [ExpFlow](https://d3tales.as.uky.edu/expflow/)
    - Download Robotics Workflow file
    - Load Robotics Workflow file through `Add Job` on robotics Robotics App (select experiment and reagent locations as prompted)
    ```
       > **Note for Measuring Conductivity**: Be sure to create, load, and run a CA Calibration workflow at least once
     > on a day when you run conductivity experiments.

* Turn on:
  * The robot
  * All Arduino devices
  * Liquid dispensing pumps
  * Instruments
  * Balance
  * Stir plate (turn the rotation rate to desired value)

* Prepare materials:
  * Measure and dispense solids into experiment vials
  * Place stir bars in experiment vials.
  * Bubble argon in solvent
  * Fill rinsing vials
 
* Prepare Stations
  * Flush liquid dispensing tubes with 8 mL solution
  * Set all electrodes
    * Place electrodes in elevator holders
    * Check secure connections for all electrodes
    * **For conductivity probe**, soak in DI water for 15 min.
  * Set temperature probe
  * Place dispensing waste beaker below pipette. 
  * Set all vials (make sure they are uncapped)
  
* Ensure any necessary calibration workflows have been completed. If you need to run a calibration, complete the next several items for the calibrations, then return to this step. 

* Prepare Software
  * Check that the CHI software is set to produce IUPAC convention CV plots. 
  * Check your {ref}`settings:settings` in settings.py!
  * Launch Fireworks WebGUI (through {ref}`command line or Robotics App <desktop_app:monitoring workflows with FireWorks WebGUI>`)
    > If managing workflows through the command line, be sure to {ref}`installation:activate environment` in any new terminal.   

  * Ensure there is *only one* READY firework: the `init_` firework for the workflow you'd like to run.
     >**Important!** *Only one* workflow may be initiated at a time. To ensure no other workflows accidentally
     > run, make sure all other workflows are PAUSED, DEFUSED, or COMPLETED.

* Start Experiment
  * Start instrument jobs. Through the Robotics App, select `Run Instruments` -> `Run Jobs Continuously`
  * Start processing jobs. Through the Robotics App, select `Run Process` -> `Run Jobs Continuously`
  * Start robot jobs. Through the Robotics App, select `Run Robot` -> `Run Jobs Continuously`
  * Initialize workflow. Through the Robotics App, select `Initialize Workflow` -> `Run a Job`
  * Note that all data collected during the workflow will appear in the `DATA_DIR` defined in the {ref}`settings:settings`. 


## After Running a Workflow

 * Ensure workflow is finished.
   * Ensure robot is not active.
   * End all running terminals.
   * Ensure there are no READY fireworks (DEFUSE or Pause any remaining READY fireworks.)
 * Turn off hardware.
   * Move robot to resting END_HOME position. Turn off.
   * Turn off pump.
   * Turn off instruments.
 * Clean up materials.
   * Cap all experiment vials.
   * Place secure cap on liquid dispensing solvent jars.
   * Remove and clean electrodes.
   * Rinse and wipe down temperature probe.
