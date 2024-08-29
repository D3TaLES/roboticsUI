# FireWorks for an experiment type
# Copyright 2024, University of Kentucky

# Import necessary modules
from fireworks import Firework, ScriptTask
from robotics_api.workflows.Firetasks_Processing import *


class InitializeExperiment(Firework):
    """
    Represents a Firework responsible for initializing an experiment workflow.

    Args:
        wflow_name (str): Name of the workflow.
        parents (list): List of parent Fireworks.
        fw_specs (dict): Specifications for the Firework.
        **kwargs: Additional keyword arguments.
    """

    def __init__(self, wflow_name='', parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'initialize'}
        spec.update(fw_specs) if fw_specs else None
        tasks = [
            InitializeRobot(),  # Initialize the robot
            InitializeStatusDB(wflow_name=wflow_name)  # Initialize status database
        ]
        super(InitializeExperiment, self).__init__(tasks, parents=parents, spec=spec, name="init_" + wflow_name,
                                                   **kwargs)


class EndWorkflowProcess(Firework):
    """
    Represents a Firework responsible for ending an experimental workflow.

    Args:
        name (str): Name of the Firework.
        parents (list): List of parent Fireworks.
        **kwargs: Additional keyword arguments.
    """

    def __init__(self, name='', parents=None, **kwargs):
        spec = {'_category': 'robotics'}
        tasks = [
            EndWorkflow()  # Task to end the workflow
        ]
        super(EndWorkflowProcess, self).__init__(tasks, parents=parents, spec=spec, name="end_workflow" + name,
                                                 **kwargs)


class RobotFirework(Firework):
    """
    Represents a Firework related to robotics tasks.

    Args:
        f_tasks (list): List of tasks for the Firework.
        name (str): Name of the Firework.
        wflow_name (str): Name of the workflow.
        priority (int): Priority of the Firework.
        parents (list): List of parent Fireworks.
        fw_specs (dict): Specifications for the Firework.
        **kwargs: Additional keyword arguments.
    """

    def __init__(self, f_tasks, name="", wflow_name="", priority=None, parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'robotics', '_priority': priority, "wflow_name": wflow_name, "name": name.strip("_")}
        spec.update(fw_specs or {})
        super(RobotFirework, self).__init__(f_tasks, parents=parents, spec=spec, name=name.strip("_"), **kwargs)


class InstrumentPrepFirework(Firework):
    """
    Represents a Firework related to instrument preparation tasks.

    Args:
        f_tasks (list): List of tasks for the Firework.
        analysis (str): Analysis type.
        name (str): Name of the Firework.
        wflow_name (str): Name of the workflow.
        priority (int): Priority of the Firework.
        parents (list): List of parent Fireworks.
        fw_specs (dict): Specifications for the Firework.
        **kwargs: Additional keyword arguments.
    """

    def __init__(self, f_tasks, analysis="", name="", wflow_name="", priority=None, parents=None, fw_specs=None,
                 **kwargs):
        spec = {'_category': 'robotics', '_priority': priority, "analysis": analysis,
                "wflow_name": wflow_name, "name": name.strip("_")}
        spec.update(fw_specs or {})
        super(InstrumentPrepFirework, self).__init__(f_tasks, parents=parents, spec=spec, name=name.strip("_"),
                                                     **kwargs)


class AnalysisFirework(Firework):
    """
    Represents a Firework related to analysis tasks.

    Args:
        f_tasks (list): List of tasks for the Firework.
        name (str): Name of the Firework.
        wflow_name (str): Name of the workflow.
        priority (int): Priority of the Firework.
        parents (list): List of parent Fireworks.
        fw_specs (dict): Specifications for the Firework.
        **kwargs: Additional keyword arguments.
    """

    def __init__(self, f_tasks, name="", wflow_name="", priority=None, parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'instrument', '_priority': priority, "wflow_name": wflow_name, "name": name.strip("_")}
        spec.update(fw_specs or {})
        super(AnalysisFirework, self).__init__(f_tasks, parents=parents, spec=spec, name=name.strip("_"), **kwargs)


class CVProcessing(Firework):
    """
    Represents a Firework for CV processing.

    Args:
        f_tasks (list): List of tasks for the Firework.
        name (str): Name of the Firework.
        mol_id: Identifier for the molecule.
        priority (int): Priority of the Firework.
        parents (list): List of parent Fireworks.
        fw_specs (dict): Specifications for the Firework.
        **kwargs: Additional keyword arguments.
    """

    def __init__(self, f_tasks, name="cv_process", mol_id=None, priority=None, parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'processing', '_priority': priority}
        spec.update(fw_specs or {})
        tasks = f_tasks or [
            DataProcessor(mol_id=mol_id, name=name),  # Data processing task
            # SendToStorage(),  # Task to send data to storage TODO implement
        ]
        super(CVProcessing, self).__init__(tasks, parents=parents, spec=spec, name=name, **kwargs)
