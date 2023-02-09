import os
import json
from sys import argv
from pathlib import Path
from fireworks import LaunchPad
from monty.serialization import loadfn
from robotics_api.workflows.wf_writer import *
from robotics_api.workflows.Robotics_FW import *

BASE_DIR = Path(__file__).resolve().parent.parent
END_WF_JOB = True  # If True, this script will add a job to end the workflow by moving the robotic arm to home.

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
        expflow_file = os.path.join(BASE_DIR, 'management', 'example_expflows', param_tag + 'cv_robot_diffusion_2_workflow.json')

    if END_WF_JOB:
        wf = Workflow([EndWorkflowProcess()])
    else:
        expflow_wf = loadfn(expflow_file)
        wf = workflow_function(expflow_wf, name_tag=name_tag)

    lpad = LaunchPad().from_file(lpad_file)
    info = lpad.add_wf(wf)
    fw_id = list(info.values())[0]

    print("Workflow ID: ", ''.join(str(fw_id).split(' ')))
