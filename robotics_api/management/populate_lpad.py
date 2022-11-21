import os
import json
from sys import argv
from pathlib import Path
from fireworks import LaunchPad
from monty.serialization import loadfn
from robotics_api.workflows.wf_writer import *
from robotics_api.workflows.Robotics_FW import *

BASE_DIR = Path(__file__).resolve().parent.parent

# PARAMETERS TO SET ----------------------------------------------------------------------------------------------------
workflow_function = run_expflow_wf
priority = 2
name_tag = ''
param_tag = ''

# ----------------------------------------------------------------------------------------------------------------------

lpad_file = os.path.join(BASE_DIR, 'management', 'config/robotics_launchpad.yaml')

if __name__ == "__main__":
    try:
        expflow_file = argv[1]
    except IndexError:
        expflow_file = os.path.join(BASE_DIR, 'example_expflows', param_tag + 'example_expflow.json')

    expflow_wf = loadfn(expflow_file)

    # wf = workflow_function(expflow_wf, name_tag=name_tag)
    wf = Workflow([EndWorkflowProcess()])
    lpad = LaunchPad().from_file(lpad_file)
    info = lpad.add_wf(wf)
    fw_id = list(info.values())[0]

    print("Workflow ID: ", ''.join(str(fw_id).split(' ')))
