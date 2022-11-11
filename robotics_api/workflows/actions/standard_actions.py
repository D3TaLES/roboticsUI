from pathlib import Path
from robotics_api.workflows.actions.snapshot_move import *
from robotics_api.workflows.actions.example_actions import *
from robotics_api.workflows.actions.standard_variables import *


def vial_home(row, column, action_type="get"):
    """
    Function that executes an action getting or placing
    Args:
        row: str or int or float, row of vial home location, e.g., 04
        column: str, column of vial home location, e.g., A
        action_type: str, 'get' if the action is getting a vail, 'place' if action is placing the vial

    Returns: bool, success of action
    """
    snapshot_vial = os.path.join(SNAPSHOT_DIR, "VialHome_{}_{:02}.json".format(column, int(row)))
    snapshot_vial_above = os.path.join(SNAPSHOT_DIR, "VialHome_{}_{:02}_Abv.json".format(column, int(row)))

    # Start open if getting a vial
    success = snapshot_move(target_position='open') if action_type == "get" else True
    # Go to vial home
    success += snapshot_move(snapshot_vial_above)
    target = VIAL_GRIP_TARGET if action_type == "get" else 'open'
    success += snapshot_move(snapshot_vial, target_position=target)
    success += snapshot_move(snapshot_vial_above)

    return success



