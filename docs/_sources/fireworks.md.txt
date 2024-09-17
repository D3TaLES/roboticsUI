# Module - Fireworks

This module is the highest level of abstraction in the Robotics API and FireWorks-based classes relevant for managing robotic workflows. he primary purpose of this module is to translate experimental protocols, defined in ExpFlow Robotic Workflow JSON files, into executable workflows on a robotic system and to serve as the source code for the launched Fireworks. For more information about the structure of a robotic workflow and its experiments, see {ref}`terminology_setup:experiments and workflows`. For even more information about the distinction between Workflows, Fireworks, and Firetasks and their base classes, see the [original FireWorks documentation](https://materialsproject.github.io/fireworks/#designing-workflows).

## Workflows 
(`Workflow_Writer.py`)

The **Workflow_Writer** focuses on converting ExpFlow Robotic Workflow JSON files into Fireworks workflows. These workflows are sequences of tasks that define experiments to be run on robotic systems. This module automates how experiments are designed, executed, and processed, enabling researchers to manage repetitive tasks efficiently.

Key components:

* **EF2Experiment Class**:
   - Converts an ExpFlow object into a Fireworks workflow.
   - `task_dictionary` pairs each ExpFlow action to a Firetask from `Firetasks_Actions`.
   - The `task_clusters` method clusters similar actions/firetasks into a single Firework
   - Takes details from the experiment, including molecules, solvents, and electrolytes, and generates a series of tasks for execution.
   - Handles different types of tasks like data collection (e.g., **CV** and **CA** data), instrument setup, and data processing. Capable of dealing with multitask scenarios (e.g., collecting data for multiple scan rates).

* **run_expflow_wf Function**:
   - Automates the creation of FireWorks Workflows for running multiple iterations of the same experiment using different molecules.
   - Manages task execution and transitions from one experimental phase to the next.

## Fireworks 
(`Fireworks.py`)

The `Fireworks.py` file hosts all the Fireworks objects. Fireworks are groupings of Firetasks actions. To better faciclitate multitasking, all Fireworks fall into one of four categories. These categories by the native FireWorks attribute `_category`, so when launching firework jobs, one can specify which categories to launch. (For more on launching jobs, see {ref}`desktop_app:launching jobs!`.)

Categories:

* **initialize**`InitializeWorkflow`:
   - Handles the initial setup of the workflow, including robot initialization and status database setup
   - As noted {ref}`elsewhere <robot_run_checklist:Robot Run Checklist>`, *only one* workflow may be initiated at a time. To run any job in a given workflow, the `InitializeWorkflow` firework from that workflow must be the most recent initialize job completed.

* **robotics** (`RobotFirework`, `InstrumentPrepFirework`, and `EndWorkflowProcess`):
   - Contins all tasks that send commands to the robotic arm.
   - Can be run simultaneously with instrument and processing tasks, but **cannot** be run simultaneously with other robotics tasks

* **instrument** (`AnalysisFirework`):
   - Contins tasks that directly operates the potentiostats and potentiostat elevators.
   - Can be run simultaneously both with robotics and processing tasks and with other instrument tasks.

* **processing** (`ProcessingFirework`):
   - Contins tasks for processing experimental data
   - Can be run simultaneously both with robotics and instrument tasks and with other processing tasks.


## Firetasks 
(`Firetasks_Actions.py` and `Firetasks_Processing.py`)


The `Firetasks_Action.py` and `Firetasks_Processing.py` files define a series of FireTasks, each responsible for executing specific actions in the robotics laboratory environment. The tasks leverage the robotics API to interface with different devices, such as potentiostats, stir stations, and liquid dispensers. Additionally, procesing FireTasks parse experimental data files and calculate relevant parameters.


Key Components:

1. Actions (`Firetask_Actions.py`)

  * **RoboticsBase**:
     - This is the base class for all FireTasks in this module. It provides setup methods, handles workflow and experiment metadata, and ensures proper integration with robotic devices. Subclasses inherit core methods.
     - The `setup_task` method handles common task setup steps such as loading experimental metadata, managing workflow states, and ensuring tasks are only executed under valid conditions. This should be run at the beginning of every Firetask.
     - The `updated_specs` method updates the Firework specs with newly generated data and should be run at the end of every Firetask

  * **DispenseLiquid**, **Stir**, **MeasureDensity**, etc.: These tasks handle the robotic vial maniputation actions. They not only execute the action but also use classes from `actions:standard actions` to update station and vial statuses.

  * **Electrode Handling Tasks**: This includes tasks like `RecordWorkingElectrodeArea`, `SetupRinsePotentiostat`, `RinseElectrode`, and `CleanElectrode`, all of which focus on preparing and maintaining electrodes for electrochemical experiments. These tasks manage interactions with potentiostat stations and ensure proper rinsing and cleaning of electrodes.

  * **Potentiostat Setup and Benchmarking**: The `SetupPotentiostat`, `SetupCVPotentiostat`, `SetupCAPotentiostat`, and `FinishPotentiostat` classes are responsible for moving the correct vial to the correct potentiostat and controling the elevator position. They must be performed before/after any measurement task (though they are added to workflows automatically in `Workflow_Writer.py`).

  * **RunCV** and **RunCA**: These tasks handle the execution of cyclic voltammetry (CV) and chronoamperometry (CA) experiments, respectively. They control the potentiostats.



2. Processing (`Firetasks_Processing.py`)

  * **Initializing Tasks**: `InitializeRobot` and `InitializeStatusDB` initailize the robot and databases respectivly by checking connections and establishing communication. For the database initialization, initial values are inserted for reagents and station/vial statuses. (For more information about the database structure, see {ref}`databases:Robotics Databases`.)

  * **ProcessBase**: An abstract base class providing core functionality for processing experimental data, managing metadata, and database integration. It contains common methods for file handling, metadata processing, and error handling.

  * **DataProcessor**: Tasks like `DataProcessor` are responsible for all types of data processing, including both CV and Chronoamperometry (CA) data. It processes, analyzes, and stores experimental data, generates plots, and updates metadata.

  * **EndWorkflow**: Concludes a workflow by finalizing robot actions (e.g., returning a vial to its home position) and creating final system snapshots to ensure a clean end state.


**Note**: This is not an exhaustive list of Firetask Actions, just a sampling of the most prominant actions.
