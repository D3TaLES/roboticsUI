import os
from pathlib import Path
from fireworks import LaunchPad, FWorker
from fireworks.core.rocket_launcher import rapidfire
from fireworks.core.rocket_launcher import launch_rocket

# set up the LaunchPad
BASE_DIR = Path(__file__).resolve().parent.parent
lpad_file = os.path.join(BASE_DIR, 'management', 'config/robotics_launchpad.yaml')
launchpad = LaunchPad().from_file(lpad_file)

launch_rocket(launchpad)
# rapidfire(launchpad, FWorker())
