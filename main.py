
import os
import json
import subprocess
import webbrowser
import tkinter as tk
from PIL import Image, ImageTk
from fireworks import LaunchPad
from tkinter.filedialog import askopenfile
from d3tales_fw.Robotics.workflows.wf_writer import *
from d3tales_fw.Calculators.generate_class import dict2obj

d3orange = "#FF9004"
d3blue = "#4590B8"
d3navy = "#1A3260"

logo = Image.open("images/D3TaLES_logo_transparent_robotics.png")
d3logo = logo.resize([int(0.3 * s) for s in logo.size])
d3logo_small = logo.resize([int(0.1 * s) for s in logo.size])


class AlertDialog(tk.Toplevel):

    def __init__(self, parent, alert_msg="Warning"):
        super().__init__(parent)
        self.parent = parent
        self.title('')
        frame = tk.Canvas(self, width=300, height=100)
        frame.grid(columnspan=4, rowspan=5)
        tk.Label(master=self, text=alert_msg, font=("Raleway", 14, 'bold'), fg=d3navy).grid(row=1, column=1, padx=20,
                                                                                            pady=2)
        tk.Button(master=self, text='Close', command=self.destroy).grid(row=2, column=1, padx=20, pady=2)

    def quitALL(self):
        self.destroy()
        self.parent.destroy()


class QuitDialog(tk.Toplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        frame = tk.Canvas(self, width=200, height=100)
        frame.grid(columnspan=4, rowspan=5)
        # warnMessage
        tk.Label(master=self, text='Are you sure that you want to quit? ', font=("Raleway", 14, 'bold')).grid(row=1,
                                                                                                              column=1,
                                                                                                              columnspan=2,
                                                                                                              padx=20,
                                                                                                              pady=20)
        # quitButton
        tk.Button(master=self, text='Yes', command=self.quitALL, font=("Raleway", 14, 'bold')).grid(row=2, column=1,
                                                                                                    padx=20, pady=2)
        # cancelButton
        tk.Button(master=self, text='No', command=lambda: self.destroy(), font=("Raleway", 14, 'bold')).grid(row=2,
                                                                                                             column=2,
                                                                                                             padx=20,
                                                                                                             pady=2)

    def quitALL(self):
        self.destroy()
        self.parent.destroy()


class AddJob(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title('Add a Workflow')
        self.design_frame()

    def design_frame(self):
        frame = tk.Canvas(self, width=400, height=300)
        frame.grid(columnspan=4, rowspan=5)

        logo = ImageTk.PhotoImage(d3logo)
        self.iconphoto(False, logo)

        # Text
        tk.Label(self, text="Add a Workflow", font=("Raleway", 26, 'bold'), fg=d3navy).grid(column=1, row=0)
        tk.Label(self, text="Select a workflow file: ", font=("Raleway", 14), fg=d3navy).grid(column=0, row=1)

        # buttons
        tk.Button(self, text="Select a Workflow", command=self.open_file, font=("Raleway", 14), bg=d3blue,
                  fg='white', height=2, width=30).grid(columnspan=2, column=0, row=2)
        tk.Button(self, text="Build a Workflow\non ExpFlow", command=self.build_wf, font=("Raleway", 14),
                  bg=d3navy, fg='white', height=4, width=20).grid(column=2, row=2, padx=10)
        self.add_txt = tk.StringVar()
        self.add_txt.set("Add Selected Workflow")
        tk.Button(self, textvariable=self.add_txt, command=self.add_wf, font=("Raleway", 16), bg=d3orange,
                  fg='white', height=2, width=45).grid(columnspan=3, column=0, row=4)

        # Selected Workflow
        tk.Label(self, text="\nSelected Workflow: \n", font=("Raleway", 16), fg=d3navy).grid(column=0, row=3,
                                                                                                     pady=30)
        self.selected_txt = tk.StringVar()
        self.selected_txt.set('')
        tk.Label(self, textvariable=self.selected_txt, font=("Raleway", 16, 'bold'), fg=d3navy).grid(column=1, row=3,
                                                                                                     pady=30)
        tk.Label(self, text="", font=("Raleway", 12), fg=d3navy).grid(column=3, row=3, padx=10)

        tk.Canvas(self, width=400, height=50).grid(columnspan=3)

    @property
    def lpad(self):
        lpad_file = os.path.join(os.getcwd(), 'd3tales_fw', 'Robotics', 'config', 'robotics_launchpad.yaml')
        return LaunchPad().from_file(lpad_file)

    def open_file(self):
        self.selected_txt.set("loading file...")
        file = askopenfile(parent=self, mode='r', title="Chose a workflow file.", filetypes=[('JSON file', "*.json")])
        if file:
            self.json_data = json.load(file)
            self.selected_txt.set(self.json_data.get("name"))

    def add_wf(self):
        self.selected_txt.set("adding workflow...")
        expflow_wf = dict2obj(self.json_data)
        wf = run_expflow_wf(expflow_wf)
        info = self.lpad.add_wf(wf)
        fw_id = list(info.values())[0]

        AlertDialog(self, alert_msg="Your workflow was successfully submitted!\nWorkflow ID: " + str(fw_id))
        self.add_txt.set("Add Selected Workflow")

    # @staticmethod
    def build_wf(self):
        webbrowser.open_new(r"https://d3tales.as.uky.edu/expflow/robotics_wfs/")


class RunRobot(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title('Run Robot')
        self.design_frame()

    def design_frame(self):
        frame = tk.Canvas(self, width=400, height=300)
        frame.grid(columnspan=1, rowspan=4)

        logo = ImageTk.PhotoImage(d3logo)
        self.iconphoto(False, logo)

        # Text
        tk.Label(self, text="Run the Robot", font=("Raleway", 36, 'bold'), fg=d3navy).grid(column=0, row=0)
        tk.Label(self, text="The Next Job:\t" + self.next_fw, font=("Raleway", 16, 'bold'), fg=d3navy).grid(column=0, row=1)

        # buttons
        self.run_txt = tk.StringVar()
        self.run_txt.set("Run Job")
        tk.Button(self, text="View Workflows", command=self.view_fw_workflows, font=("Raleway", 10), bg=d3navy, fg='white', height=1, width=15).grid(column=0, row=2)
        tk.Button(self, textvariable=self.run_txt, font=("Raleway", 14), bg=d3orange, command=self.run_robot, fg='white', height=2, width=30).grid(column=0, row=3)

        tk.Canvas(self, width=400, height=50).grid(columnspan=3)

    @property
    def lpad(self):
        lpad_file = os.path.join(os.getcwd(), 'd3tales_fw', 'Robotics', 'config', 'robotics_launchpad.yaml')
        return LaunchPad().from_file(lpad_file)

    @property
    def next_fw(self):
        fw = self.lpad._get_a_fw_to_run(checkout=False)
        if fw:
            return str(fw.name or fw.fw_id)
        else:
            return "No ready firework found."

    def run_robot(self):
        self.run_txt.set("Launching Job...")
        return_code = subprocess.call('rlaunch singleshot', )
        if return_code == 0:
            AlertDialog(self, alert_msg="Firework successfully launched!")
        self.run_txt.set("Run Job")

    def view_fw_workflows(self):
        lpad_file = os.path.join(os.getcwd(), "d3tales_fw", "Robotics", "config", "robotics_launchpad.yaml")
        self.parent.destroy()
        subprocess.call('lpad -l {} webgui'.format(lpad_file))


class RoboticsGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title('D3TaLES Robotics')
        self.design_frame()

    def design_frame(self):
        info_frame = tk.Canvas(self, width=500, height=300)
        info_frame.grid(columnspan=2, rowspan=4)

        # logo
        logo = ImageTk.PhotoImage(d3logo)
        logo_label = tk.Label(image=logo)
        logo_label.image = logo
        logo_label.grid(columnspan=2, column=0, row=0)
        self.iconphoto(False, logo)

        # buttons
        view_workflows = tk.Button(self, text="View Workflows", command=self.view_fw_workflows, font=("Raleway", 14),
                                   bg=d3navy,
                                   fg='white', height=2, width=15)
        view_workflows.grid(column=0, row=2)
        add_job = tk.Button(self, text="Add Job", command=self.open_add, font=("Raleway", 14), bg=d3navy, fg='white',
                            height=2, width=15)
        add_job.grid(column=0, row=3, pady=10)
        run_robot = tk.Button(self, text="Run\nRobot", command=self.open_run, font=("Raleway", 14), bg=d3orange,
                              fg='white', height=4, width=15)
        run_robot.grid(column=1, row=2, rowspan=2)

        tk.Canvas(self, width=400, height=50).grid(columnspan=2)

        # self.mainloop()

    def open_add(self):
        window = AddJob(self)
        window.grab_set()

    def open_run(self):
        window = RunRobot(self)
        window.grab_set()

    def view_fw_workflows(self):
        lpad_file = os.path.join(os.getcwd(), "d3tales_fw", "Robotics", "config", "robotics_launchpad.yaml")
        self.destroy()
        subprocess.call('lpad -l {} webgui'.format(lpad_file))


if __name__ == "__main__":
    # subprocess.call("conda activate d3tales_robotics")
    subprocess.call("set PYTHONPATH=C:\\Users\Lab\\D3talesRobotics\\roboticsUI\\", shell=True)
    app = RoboticsGUI()
    app.mainloop()
