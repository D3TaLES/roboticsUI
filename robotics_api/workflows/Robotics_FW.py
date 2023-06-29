# FireWorks for an experiment type
# Copyright 2022, University of Kentucky

from fireworks import Firework, ScriptTask
from robotics_api.workflows.Processing import *
from robotics_api.workflows.ExperimentActions import *


class InitializeExperiment(Firework):
    def __init__(self, wflow_name='', parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'processing', }
        spec.update(fw_specs) if fw_specs else None
        tasks = [
            InitializeRobot(),
            InitializeStatusDB(wflow_name=wflow_name)
        ]
        super(InitializeExperiment, self).__init__(tasks, parents=parents, spec=spec, name="init_"+wflow_name, **kwargs)


class EndWorkflowProcess(Firework):
    def __init__(self, name='', parents=None, **kwargs):
        spec = {'_category': 'robotics'}
        tasks = [
            EndWorkflow()
        ]
        super(EndWorkflowProcess, self).__init__(tasks, parents=parents, spec=spec, name="end_workflow"+name, **kwargs)


class RobotFirework(Firework):
    def __init__(self, f_tasks, name="", wflow_name="", priority=None, parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'robotics', '_priority': priority, "wflow_name": wflow_name, "name": name.strip("_")}
        spec.update(fw_specs or {})
        super(RobotFirework, self).__init__(f_tasks, parents=parents, spec=spec, name=name.strip("_"), **kwargs)


class InstrumentPrepFirework(Firework):
    def __init__(self, f_tasks, analysis="", name="", wflow_name="", priority=None, parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'instrument_setup', '_priority': priority, "analysis": analysis,
                "wflow_name": wflow_name, "name": name.strip("_")}
        spec.update(fw_specs or {})
        super(InstrumentPrepFirework, self).__init__(f_tasks, parents=parents, spec=spec, name=name.strip("_"), **kwargs)


class AnalysisFirework(Firework):
    def __init__(self, f_tasks, name="", wflow_name="", priority=None, parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'instrument', '_priority': priority, "wflow_name": wflow_name, "name": name.strip("_")}
        spec.update(fw_specs or {})
        super(AnalysisFirework, self).__init__(f_tasks, parents=parents, spec=spec, name=name.strip("_"), **kwargs)


class CVProcessing(Firework):
    def __init__(self, f_tasks, name="cv_process", mol_id=None, priority=None, parents=None, fw_specs=None, **kwargs):
        spec = {'_category': 'processing', '_priority': priority}
        spec.update(fw_specs or {})
        tasks = f_tasks or [
            CVProcessor(mol_id=mol_id, name=name),
            # SendToStorage(),
        ]
        super(CVProcessing, self).__init__(tasks, parents=parents, spec=spec, name=name, **kwargs)


class TestProcess(Firework):
    def __init__(self, priority=None, parents=None, **kwargs):
        spec = {'_category': 'processing', '_priority': priority} if priority else {'_category': 'processing'}
        tasks = [ScriptTask.from_str('echo "Processing example..."')]
        super(TestProcess, self).__init__(tasks, parents=parents, spec=spec, name="test_process", **kwargs)


