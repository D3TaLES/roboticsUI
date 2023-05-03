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


class CVProcessing(Firework):
    def __init__(self, name="process_cv", mol_id=None, priority=None, parents=None, metadata=None, **kwargs):
        spec = {'_category': 'processing', '_priority': priority} if priority else {'_category': 'processing'}
        tasks = [
            CVProcessor(mol_id=mol_id, metadata=metadata, name="{}_{}".format(mol_id, name)),
            # SendToStorage(),
        ]
        super(CVProcessing, self).__init__(tasks, parents=parents, spec=spec, name="{}_{}".format(mol_id, name), **kwargs)


class TestRobot(Firework):
    def __init__(self, priority=None, parents=None, **kwargs):
        spec = {'_category': 'robotics', '_priority': priority} if priority else {'_category': 'robotics'}
        tasks = [
            TestMovement(),
        ]
        super(TestRobot, self).__init__(tasks, parents=parents, spec=spec, name="test_robot", **kwargs)


class TestProcess(Firework):
    def __init__(self, priority=None, parents=None, **kwargs):
        spec = {'_category': 'robotics', '_priority': priority} if priority else {'_category': 'processing'}
        tasks = [ScriptTask.from_str('echo "Processing example..."')]
        super(TestProcess, self).__init__(tasks, parents=parents, spec=spec, name="test_process", **kwargs)


