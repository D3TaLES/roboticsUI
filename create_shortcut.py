import winshell
from pathlib import Path

desktop = Path(winshell.desktop())
miniconda_base = Path(winshell.folder('profile')) / "miniconda3"
icon = str(Path(winshell.folder('profile')) / "D3talesRobotics" / "roboticsUI" / "images" / "D3TaLES_logo_transparent_robotics.ico")

working_dir = str(Path(winshell.folder('profile')) / "D3talesRobotics" / "roboticsUI")
link_filepath = str(desktop / "d3tales_robotics.lnk")

arg_str = "/K " + str(miniconda_base / "Scripts" / "activate.bat") + " " + str(miniconda_base / "envs" / "d3tales_robotics")
arg_str += " & python main.py"

# Create the shortcut on the desktop
with winshell.shortcut(link_filepath) as link:
    link.path = "main.py"
    link.description = "D3TaLES Robotics"
    link.arguments = arg_str
    link.icon_location = (icon, 0)
    link.working_directory = working_dir