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
```{checkbox-list}
#### Load Robotics Workflow
  * Create Robotics Workflow on [ExpFlow](https://d3tales.as.uky.edu/expflow/)
  * Download Robotics Workflow file
  * Load Robotics Workflow file through `Add Job` on robotics Robotics App (select experiment and reagent locations as prompted)
     > **Note for Measuring Conductivity**: Be sure to create, load, and run a CA Calibration workflow at least once
     > on a day when you run conductivity experiments.

#### Turn on:
  * The robot
  * All Arduino devices
  * Liquid dispensing pumps
  * Instruments
  * Balance
  * Stir plate (turn the rotation rate to desired value)

#### Prepare materials:
  * Measure and dispense solids into experiment vials
  * Place stir bars in experiment vials.
  * Fill rinsing vials (Vials `S1`, `S2`, etc.)
  * Fill solvent jars, bubble argon in solvent, place jars in liquid dispensing stations with the tube cap screwed on. 
    > **Note**: When bubbling argon in the solvent, open the cylinder valve, then adjust the delivery pressure valve so
    > the delivery presure is ~10 psi. Then, slowly open the flow control valve and place the gas flow tube in the 
    > solvent. Adjust the flow control valve so there is steady Argon bubbling in the solvent. Bubble for at least 
    > 10 minutes. To finish, close the cylinder valve, the delivery pressure valve, then the flow valve. Ensure
    > no more bubbles appear in the solvent. 
 
#### Prepare Stations
  * Flush liquid dispensing tubes with 8 mL solution
  * Perform density test with pipette to wet pipette and check pipette calibration. 
  * Place electrodes in elevator holders
  * Be sure the vial does not hit electrodes when risen 
  * Check secure connections for all electrodes
  * **For conductivity probe**, soak in DI water for 15 min. **Be sure there are no bubbles in the electrode.**
  * Set temperature probe (NOT in the vial solution)
  * Place dispensing waste beaker below pipette. 
  * Set all vials (make sure they are uncapped)
  
#### Prepare Software
  * Check that the CHI software is set to produce IUPAC convention CV plots. (`Setup` &#8594; `System` &#8594; `Anodic Positive` and `Positive Right`)
  * Check your settings in settings.py!
  * Launch Fireworks WebGUI (through command line or Robotics App.)
    > **Note**: If managing workflows through the command line, be sure to activate the environment in any new terminal.   

  * Ensure there is *only one* READY firework: the `init_` firework for the workflow you'd like to run.
     >**Important!** *Only one* workflow may be initiated at a time. To ensure no other workflows accidentally
     > run, pause all READY Fireworks (`lpad pause_fws -s READY`). Then, rerun the initialization Firework for the 
     > the workflow you want to run (`lpad rerun_fws -i <init_fw_id>`). 
  
#### Ensure any necessary calibration workflows have been completed. 
  * If you need to run a calibration, complete the next several items for the calibrations, then return to this step. 

#### Start Experiment
  * Start instrument jobs. Through the Robotics App, `Run Instruments` -> `Run Jobs Continuously`
  * Start processing jobs. Through the Robotics App, `Run Process` -> `Run Jobs Continuously`
  * Start robot jobs. Through the Robotics App, `Run Robot` -> `Run Jobs Continuously`
  * Initialize workflow. Through the Robotics App, `Initialize Workflow` -> `Run a Job`
  
    > **Note**: Note that all data collected during the workflow will appear in the `DATA_DIR` defined in the settings. 
```

## After Running a Workflow
```{checkbox-list}
#### Ensure workflow is finished.
   * Ensure robot is not active.
   * End all running terminals.
   * Ensure there are no READY fireworks (DEFUSE or Pause any remaining READY fireworks.)
#### Turn off hardware.
   * Move robot to resting END_HOME position. Turn off.
   * Turn off pump.
   * Turn off instruments.
#### Clean up materials.
   * Cap all experiment vials.
   * Place secure cap on liquid dispensing solvent jars.
   * Remove and clean electrodes.
```