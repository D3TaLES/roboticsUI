# Module - Fireworks


## Overview
This module is the highest level of abstraction in the Robotics API and FireWorks-based classes relevant for managing robotic workflows. he primary purpose of this module is to translate experimental protocols, defined in ExpFlow Robotic Workflow JSON files, into executable workflows on a robotic system and to serve as the source code for the launched Fireworks. For more information about the structure of a robotic workflow and its experiments, see {ref}`terminology_setup:experiments and workflows`. For even more information about the distinction between Workflows, Fireworks, and Firetasks and their base classes, see the [original FireWorks documentation](https://materialsproject.github.io/fireworks/#designing-workflows).

## Workflows (`Workflow_Writer.py`)

The `fireworks` module in the Robotics API serves as the highest abstraction layer for managing robotic workflows. It integrates with **FireWorks**, a dynamic workflow management system, to coordinate complex experimental tasks in a robotic setup. A key component of this module is the `Workflow_Writer.py` script, which provides functionality to convert experimental workflows into Fireworks workflows. This allows for the execution of experiments using robots.

### Purpose and High-Level Overview

The **Workflow_Writer** focuses on converting experimental flow objects (`ExpFlow`) into Fireworks workflows. These workflows are sequences of tasks that define experiments to be run on robotic systems. This module automates how experiments are designed, executed, and processed, enabling researchers to manage repetitive tasks efficiently.

Key components:

1. **EF2Experiment Class**:
   - Converts an `ExpFlow` object into a Fireworks workflow.
   - Takes details from the experiment, including molecules, solvents, and electrolytes, and generates a series of tasks for execution.
   - Supports task dependencies, clustering, and prioritization.

2. **Task Management**:
   - Handles different types of tasks like data collection (e.g., **CV** and **CA** data), instrument setup, and data processing.
   - Capable of dealing with multitask scenarios (e.g., collecting data for multiple scan rates).
   - Dynamically generates tasks like setup and finish operations for instruments.

3. **Firetasks Generation**:
   - The module generates Firetasks for a variety of operations (e.g., transferring liquids, stirring, measuring density).
   - It ensures tasks are correctly sequenced based on dependencies and workflow progress.

4. **run_expflow_wf Function**:
   - Automates the creation of workflows for running multiple iterations of the same experiment using different molecules.
   - Manages task execution and transitions from one experimental phase to the next.

5. **run_ex_processing Function** (For Testing):
   - A simplified function for testing basic processing jobs (e.g., CV processing).

### Workflow Lifecycle

The `EF2Experiment` class parses the experimental flow and generates tasks that a robot will execute, ensuring proper sequencing. It handles multiple steps like preparation, data collection, and data processing, creating Firetasks that robots can process. For each task, specifications (e.g., molecule ID, solvent type) are passed down, ensuring that experiments follow predefined parameters.

This module is crucial in automating robotic workflows in labs, providing scalability and reliability in handling repetitive experiments.

## Fireworks (`Fireworks.py`)

### Categories

## Firetasks (`Firetasks_Actions.py` and `Firetasks_Processing.py`)

*!! This page is in still in development*
