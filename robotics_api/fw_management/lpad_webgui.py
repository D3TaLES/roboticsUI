import os
from pathlib import Path
from fireworks import LaunchPad
from fireworks.flask_site.app import app

"""
Launch Fireworks webgui
"""

BASE_DIR = Path(__file__).resolve().parent.parent
lpad_file = os.path.join(BASE_DIR, 'fw_management', 'config/launchpad_robot.yaml')
app.lp = LaunchPad().from_file(lpad_file)
app.run(debug=True)
