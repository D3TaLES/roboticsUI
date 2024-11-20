import winshell
from pathlib import Path

desktop = Path(winshell.desktop())
working_dir = Path(winshell.folder('profile')) / "D3talesRobotics" / "roboticsUI" / "GUI"
icon = str(Path(winshell.folder('profile')) / "D3talesRobotics" / "roboticsUI" / "docs_src" / "media" / "D3TaLES_logo_transparent_robotics.ico")
command = r"conda activate d3tales_robotics && python " + str(working_dir / "main.py")

# Create the shortcut on the desktop
with winshell.shortcut(str(desktop / "RoboticsApp.lnk")) as link:
    link.description = "D3TaLES Robotics"
    link.arguments = f"/K {command}"  # /K keeps the command window open after execution

    link.icon_location = (icon, 0)
    link.working_directory = str(working_dir)
