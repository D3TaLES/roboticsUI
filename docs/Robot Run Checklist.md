# Robot Run Checklist
* Load Robotics Workflow
  * Create Robotics Workflow on [ExpFlow](https://d3tales.as.uky.edu/expflow/)
  * Download Robotics Workflow file
  * Load Robotics Workflow file through `Add Job` on robotics desktop app (select experiment and reagent locations as prompted)
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
  * Measure and dispense solids
  * Bubble argon in solvent 
  * Fill rinsing vials
* Prepare Stations
  * Flush liquid dispensing tubes with 8 mL solution 
  * Set all electrodes
  * Set temperature probe
  * Set all vials (make sure they are uncapped)
* Prepare Software
  * Ensure any necessary calibration workflows have been completed. 
  * Check your settings in settings.py!
  * Launch Fireworks WebGUI (through command line or desktop app)
  * Ensure there is *only one* READY firework: the `init_` firework for the workflow you'd like to run. 
     >**Important!** *Only one* workflow may be initiated at a time. To ensure no other workflows accidentally 
     > run, make sure all other workflows are PAUSED, DEFUSED, or COMPLETED. 
* Start Experiment
  * Start instrument jobs. Through the desktop app, select `Run Instruments` -> `Run Jobs Continuously`
  * Start processing jobs. Through the desktop app, select `Run Process` -> `Run Jobs Continuously`
  * Start robot jobs. Through the desktop app, select `Run Robot` -> `Run Jobs Continuously`
  * Initialize workflow. Through the desktop app, select `Initialize Workflow` -> `Run a Job`