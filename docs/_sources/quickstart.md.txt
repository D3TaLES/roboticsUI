#  QuickStart


## Creating Robotic Workflows: ExpFlow
All robotic workflows are created from ExpFlow Robotic Workflows. [ExpFlow](https://d3tales.as.uky.edu/expflow/)
is a D3TaLES tool that allows researchers to systematically encode their
experimental procedures through an intuitive graphical interface. For more information about ExpFlow in general see the
[ExpFlow Documentation](https://d3tales.as.uky.edu/expflow/docs)

A user may create an ExpFlow Template, then use that template to generate an ExpFlow Robotic Workflow. For a tutorial
on creating an ExpFlow Template and Robotic Workflow for the purpose of this robotic system, see {ref}`expflow:expflow robotic workflows`
This Robotic Workflow can then be downloaded as a JSON file to the Robotics Workstation. (It is recommended that you
store downloaded workflows in the `downloaded_wfs` folder.) A downloaded Robotic Workflow JSON file may be loaded
and readied for robotic action through the `D3TaLES Robotics` app. For a tutorial on loading an ExpFlow Robotic Workflow
file with the Desktop App, see {ref}`desktop_app:loading a workflow`.

## Managing Robotic Workflows
Users can monitor loaded Workflows through the FireWorks WebGUI. This can be launched
either through the command line (`lpad webgui`) like noted in the FireWorks docs or
through the Desktop App (see {ref}`desktop_app:monitoring workflows with fireworks webgui`).

The robotic workflows are managed via [FireWorks](https://materialsproject.github.io/fireworks/). If you are not
familiar with Fireworks, it is highly recommended that you review the structure of FireWorks to
better understand this system. Many operations to manage your robotic workflows can be implemented directly
via the FireWorks `lpad` and `rlaunch` commands.

Alternatively, the robotic system can be managed via the `D3TaLES Robotics` app.
This can be launched from the icon Robotics Workstation desktop page.

## Running an Experiment...
Now it's time to run the robotic experiment! Be sure to follow the {ref}`robot_run_checklist:robot run checklist` whenever running the robot!
