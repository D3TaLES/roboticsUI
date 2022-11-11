# FireTasks for individual experiment processing
# Copyright 2022, University of Kentucky

import traceback
import itertools
from pathlib import Path
from argparse import Namespace
from robotics_api.workflows.actions.snapshot_move import *
from robotics_api.workflows.actions.utilities import DeviceConnection
from robotics_api.workflows.actions.example_actions import *
from robotics_api.workflows.actions.standard_actions import *
from fireworks import FiretaskBase, explicit_serialize, FWAction

# Copyright 2021, University of Kentucky
TESTING = False


@explicit_serialize
class Practice(FiretaskBase):
    # FireTask for initializing robot and testing connection

    def run_task(self, fw_spec):
        print("Ian Test")

        # Start open and at home
        success = snapshot_move(SNAPSHOT_HOME)

        # Get vial
        success += vial_home(4, "A", action_type='get')
        # Return vial to starting position
        for column, row in itertools.product(["B", "C"], [3]):
            print(column, row)
            if column == "A" and row == 4:
                continue
            success += vial_home(row, column, action_type='place')
            success += vial_home(row, column, action_type='get')
        success += vial_home(4, "A", action_type='place')

        # Return home
        success += snapshot_move(SNAPSHOT_HOME)

        return FWAction(update_spec={"success": success})
