# FireWorks for an experiment type
# Copyright 2022, University of Kentucky

from fireworks import Firework, ScriptTask
from robotics_api.workflows.Processing import *
from robotics_api.workflows.ExperimentActions import *


class InitializeExperiment(Firework):
    def __init__(self, name='', parents=None, **kwargs):
        spec = {'_category': 'processing'}
        tasks = [
            InitializeRobot()
        ]
        super(InitializeExperiment, self).__init__(tasks, parents=parents, spec=spec, name="init_"+name, **kwargs)


class EndWorkflowProcess(Firework):
    def __init__(self, name='', parents=None, **kwargs):
        spec = {'_category': 'robotics'}
        tasks = [
            EndWorkflow()
        ]
        super(EndWorkflowProcess, self).__init__(tasks, parents=parents, spec=spec, name="end_workflow"+name, **kwargs)


class ExpFirework(Firework):
    def __init__(self, f_tasks, name="", wflow_name="", priority=None, parents=None, exp_params=None, **kwargs):
        spec = {'_category': 'robotics', "wflow_name": wflow_name}
        spec.update({'_priority': priority}) if priority else None
        spec.update(exp_params) if exp_params else None
        spec.update({name: name.strip("_")})
        super(ExpFirework, self).__init__(f_tasks, parents=parents, spec=spec, name=name.strip("_"), **kwargs)


class CVProcessing(Firework):
    def __init__(self, f_tasks, name="cv_process", mol_id=None, priority=None, parents=None, metadata=None, exp_params=None, **kwargs):
        spec = {'_category': 'processing'}
        spec.update({'priority': priority}) if priority else None
        spec.update(exp_params) if exp_params else None
        tasks = f_tasks or [
            CVProcessor(mol_id=mol_id, metadata=metadata, name=name),
            # SendToStorage(),
        ]
        super(CVProcessing, self).__init__(tasks, parents=parents, spec=spec, name=name, **kwargs)


class TestRobot(Firework):
    def __init__(self, priority=None, parents=None, **kwargs):
        spec = {'_category': 'robotics', '_priority': priority} if priority else {'_category': 'robotics'}
        tasks = [
            TestMovement(),
        ]
        super(TestRobot, self).__init__(tasks, parents=parents, spec=spec, name="test_robot", **kwargs)


class TestProcess(Firework):
    def __init__(self, priority=None, parents=None, **kwargs):
        spec = {'_category': 'processing', '_priority': priority} if priority else {'_category': 'processing'}
        tasks = [ScriptTask.from_str('echo "Processing example..."')]
        super(TestProcess, self).__init__(tasks, parents=parents, spec=spec, name="test_process", **kwargs)


