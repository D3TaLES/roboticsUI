import os
os.environ['DB_INFO_FILE'] = 'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\db_infos.json'
HOME_DIR = os.path.dirname(os.path.realpath(__file__))
LAUNCH_DIR = os.path.abspath('C:\\Users\\Lab\\D3talesRobotics\\launch_dir')
ROBOT_FWORKER = os.path.abspath('C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\fireworker_robot.yaml')
PROCESS_FWORKER = os.path.abspath('C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\management\\config\\fireworker_process.yaml')
import subprocess
import webbrowser
import tkinter as tk
from PIL import Image, ImageTk
from fireworks import LaunchPad
from tkinter.filedialog import askopenfile
from app_processing import *
from robotics_api.workflows.wf_writer import *


d3orange = "#FF9004"
d3blue = "#4590B8"
d3navy = "#1A3260"

logo = Image.open("images/D3TaLES_logo_transparent_robotics.png")
d3logo = logo.resize([int(0.3 * s) for s in logo.size])
d3logo_small = logo.resize([int(0.1 * s) for s in logo.size])


class AlertDialog(tk.Toplevel):

    def __init__(self, parent, alert_msg="Warning. Something went wrong..."):
        super().__init__(parent)
        self.parent = parent
        self.title('')
        logo = ImageTk.PhotoImage(d3logo)
        self.iconphoto(False, logo)
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


class SetReagents(tk.Toplevel):
    def __init__(self, parent, experiment_data):
        super().__init__(parent)
        self.parent = parent

        self.title('Set Reagent Locations')
        self.experiment_data = experiment_data
        self.molecules = get_exp_reagents(experiment_data)
        self.options = location_options()
        self.results_dict = {}

        self.design_frame()

    def design_frame(self):
        rowspan = len(self.molecules)+2
        frame = tk.Canvas(self, width=400, height=300)
        frame.grid(columnspan=2, rowspan=rowspan)

        logo = ImageTk.PhotoImage(d3logo)
        self.iconphoto(False, logo)

        # Text
        tk.Label(self, text="Set Reagent Locations", font=("Raleway", 36, 'bold'), fg=d3navy).grid(column=0, row=0, columnspan=2)
        tk.Label(self, text="Select the starting vial home position for each reagent. The selected position specifies "
                            "the column then the row (e.g. A, 03).", font=("Raleway", 16, 'bold'), pady=10, wraplength=600, fg=d3navy).grid(column=0, row=1, columnspan=2)

        # Location Dropdowns
        results_dict = {}
        for i, reagent in enumerate(self.molecules):
            tk.Label(self, text="{}\n{}".format(reagent[0], reagent[1]), justify="center", font=("Raleway", 16,), fg=d3navy).grid(column=0, row=i+2)
            dropdown_txt = tk.StringVar()
            dropdown_txt.set(self.options[0])
            dropdown = tk.OptionMenu(self, dropdown_txt, *self.options)
            dropdown.config(font=("Raleway", 14), bg=d3blue, fg='white', height=2, width=30)
            dropdown.grid(column=1, row=i+2)
            self.results_dict[reagent] = dropdown_txt

        # button
        self.run_txt = tk.StringVar()
        self.run_txt.set("Set Locations and Add Workflow")
        tk.Button(self, textvariable=self.run_txt, font=("Raleway", 14), bg=d3orange, command=self.set_parameters,
                  fg='white', height=2, width=30).grid(column=0, row=rowspan, columnspan=2, pady=10)

        tk.Canvas(self, width=400, height=50+10*rowspan).grid(columnspan=2)

    def set_parameters(self):
        self.run_txt.set("adding workflow...")
        exp_params = assign_reagent_locations({r: dt.get() for r, dt in self.results_dict.items()}, self.experiment_data)
        self.parent.EXP_PARAMS = exp_params
        self.destroy()


class AddJob(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title('Add a Workflow')
        self.design_frame()

    def design_frame(self):
        frame = tk.Canvas(self, width=400, height=300)
        frame.grid(columnspan=4, rowspan=6)

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
                  fg='white', height=2, width=45).grid(columnspan=3, column=0, row=5)

        # Selected Workflow
        tk.Label(self, text="\nSelected Workflow: \n", font=("Raleway", 16), fg=d3navy).grid(column=0, row=3,
                                                                                                     pady=30)
        self.selected_txt = tk.StringVar()
        self.selected_txt.set('')
        tk.Label(self, textvariable=self.selected_txt, font=("Raleway", 16, 'bold'), fg=d3navy).grid(column=1, row=3,
                                                                                                     pady=30)
        tk.Label(self, text="", font=("Raleway", 12), fg=d3navy).grid(column=3, row=3, padx=10)

        tk.Canvas(self, width=400, height=50).grid(columnspan=3)

        # Name Tag
        self.name_tag = tk.StringVar()
        self.name_tag.set('')
        tk.Label(self, text="Workflow Name Tag", font=("Raleway", 14), fg=d3navy).grid(column=0, row=4)
        tk.Entry(self, textvariable=self.name_tag, font=("Raleway", 16, 'bold'), width=30, fg=d3navy).grid(column=1, row=4, pady=30)

    @property
    def lpad(self):
        lpad_file = os.path.join(os.getcwd(), 'robotics_api', 'management', 'config', 'launchpad_robot.yaml')
        return LaunchPad().from_file(lpad_file)

    def open_file(self):
        self.selected_txt.set("loading file...")
        file = askopenfile(parent=self, mode='r', title="Chose a workflow file.", filetypes=[('JSON file', "*.json")])
        if file:
            self.json_data = json.load(file)
            self.selected_txt.set(self.json_data.get("name"))

    def add_wf(self):
        self.add_txt.set("adding workflow...")
        window = SetReagents(self, self.json_data)
        self.wait_window(window)
        print(self.EXP_PARAMS)
        self.add_txt.set("adding workflow...")
        wf = run_expflow_wf(self.json_data, name_tag=self.name_tag.get(), exp_params=self.EXP_PARAMS)
        info = self.lpad.add_wf(wf)
        fw_id = list(info.values())[0]

        AlertDialog(self, alert_msg="Your workflow was successfully submitted!\nWorkflow ID: " + str(fw_id))
        self.add_txt.set("Add Selected Workflow")
        self.destroy()

    # @staticmethod
    def build_wf(self):
        webbrowser.open_new(r"https://d3tales.as.uky.edu/expflow/robotics_wfs/")


class RunBase(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.fireworker = None
        self.category = None
        self.run_txt = tk.StringVar()
        self.run_all_txt = tk.StringVar()
        self.run_cont_txt = tk.StringVar()

    @property
    def lpad(self):
        lpad_file = os.path.join(os.getcwd(), 'robotics_api', 'management', 'config', 'launchpad_robot.yaml')
        return LaunchPad().from_file(lpad_file)

    @property
    def next_fw(self):

        m_fw = self.lpad.fireworks.find_one({"state": "READY", "spec._category": self.category}, {"fw_id": 1, "spec": 1},
                                            sort=[("spec._priority", -1)])
        fw = self.lpad.get_fw_by_id(m_fw["fw_id"]) if m_fw else None
        if fw:
            return str(fw.name or fw.fw_id)
        else:
            return "No ready firework found."

    def run_job(self):
        self.run_txt.set("Launching {} Job...".format(self.category.capitalize()))
        os.chdir(LAUNCH_DIR)
        return_code = subprocess.call('rlaunch -w {} singleshot'.format(self.fireworker), )
        os.chdir(HOME_DIR)
        if return_code == 0:
            AlertDialog(self, alert_msg="Firework successfully launched!")
        self.run_txt.set("Run a Job")
        self.destroy()

    def run_job_all(self):
        self.parent.destroy()
        os.chdir(LAUNCH_DIR)
        subprocess.call('cls', shell=True)
        print('LAUNCHING ALL READY {} JOBS...\n\n'.format(self.category.upper()))
        subprocess.call('rlaunch -w {} rapidfire'.format(self.fireworker), )

    def run_job_continuous(self):
        self.parent.destroy()
        os.chdir(LAUNCH_DIR)
        subprocess.call('cls', shell=True)
        print('LAUNCHING {} JOBS CONTINUOUSLY...\n\n'.format(self.category.upper()))
        subprocess.call('rlaunch -w {} rapidfire --nlaunches infinite --sleep 10'.format(self.fireworker), )

    def view_fw_workflows(self):
        lpad_file = os.path.join(os.getcwd(), "robotics_api", "management", "config", "launchpad_robot.yaml")
        self.parent.destroy()
        subprocess.call('lpad -l {} webgui'.format(lpad_file))


class RunRobot(RunBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title('Run Robot')
        self.fireworker = ROBOT_FWORKER
        self.category = "robotics"
        self.design_frame()

    def design_frame(self):
        frame = tk.Canvas(self, width=400, height=400)
        frame.grid(columnspan=1, rowspan=5)

        logo = ImageTk.PhotoImage(d3logo)
        self.iconphoto(False, logo)

        # Text
        tk.Label(self, text="Run the Robot", font=("Raleway", 36, 'bold'), fg=d3navy).grid(column=0, row=0)
        tk.Label(self, text="The Next Job(s):\t" + self.next_fw, font=("Raleway", 16, 'bold'), fg=d3navy).grid(column=0, row=1)

        # buttons
        self.run_txt.set("Run a Job")
        self.run_all_txt.set("Run All Ready Jobs")
        self.run_cont_txt.set("Run Jobs Continuously")
        tk.Button(self, text="View Workflows", command=self.view_fw_workflows, font=("Raleway", 10), bg=d3navy, fg='white', height=1, width=15).grid(column=0, row=2)
        tk.Button(self, textvariable=self.run_txt, font=("Raleway", 14), bg=d3orange, command=self.run_job, fg='white', height=2, width=30).grid(column=0, row=3)
        tk.Button(self, textvariable=self.run_all_txt, font=("Raleway", 14), bg=d3orange, command=self.run_job_all, fg='white', height=2, width=30).grid(column=0, row=4)
        tk.Button(self, textvariable=self.run_cont_txt, font=("Raleway", 14), bg=d3orange, command=self.run_job_continuous, fg='white', height=2, width=30).grid(column=0, row=5)

        tk.Canvas(self, width=400, height=50).grid(columnspan=3)


class RunProcess(RunBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title('Run Processing')
        self.fireworker = PROCESS_FWORKER
        self.category = "processing"
        self.design_frame()

    def design_frame(self):
        frame = tk.Canvas(self, width=400, height=400)
        frame.grid(columnspan=1, rowspan=6)

        logo = ImageTk.PhotoImage(d3logo)
        self.iconphoto(False, logo)

        # Text
        tk.Label(self, text="Run Robotic Processing", font=("Raleway", 36, 'bold'), fg=d3navy).grid(column=0, row=0)
        tk.Label(self, text="The Next Job(s):\t" + self.next_fw, font=("Raleway", 16, 'bold'), fg=d3navy).grid(column=0, row=1)

        # buttons
        self.run_txt.set("Run a Job")
        self.run_all_txt.set("Run All Ready Jobs")
        self.run_cont_txt.set("Run Jobs Continuously")
        tk.Button(self, text="View Workflows", command=self.view_fw_workflows, font=("Raleway", 10), bg=d3navy, fg='white', height=1, width=15).grid(column=0, row=2)
        tk.Button(self, textvariable=self.run_txt, font=("Raleway", 14), bg=d3orange, command=self.run_job, fg='white', height=2, width=30).grid(column=0, row=3)
        tk.Button(self, textvariable=self.run_all_txt, font=("Raleway", 14), bg=d3orange, command=self.run_job_all, fg='white', height=2, width=30).grid(column=0, row=4)
        tk.Button(self, textvariable=self.run_cont_txt, font=("Raleway", 14), bg=d3orange, command=self.run_job_continuous, fg='white', height=2, width=30).grid(column=0, row=5)

        tk.Canvas(self, width=400, height=50).grid(columnspan=3)


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
        run_job = tk.Button(self, text="Run Robot", command=self.open_run, font=("Raleway", 14), bg=d3orange,
                              fg='white', height=2, width=15)
        run_job.grid(column=1, row=2)
        run_process = tk.Button(self, text="Run Processing", command=self.open_run_process, font=("Raleway", 14), bg=d3orange,
                              fg='white', height=2, width=15)
        run_process.grid(column=1, row=3)

        tk.Canvas(self, width=400, height=50).grid(columnspan=2)

        # self.mainloop()

    def open_add(self):
        window = AddJob(self)
        window.grab_set()

    def open_run(self):
        window = RunRobot(self)
        window.grab_set()

    def open_run_process(self):
        window = RunProcess(self)
        window.grab_set()

    def view_fw_workflows(self):
        lpad_file = os.path.join(os.getcwd(), "robotics_api", "management", "config", "launchpad_robot.yaml")
        self.destroy()
        subprocess.call('lpad -l {} webgui'.format(lpad_file))


if __name__ == "__main__":
    app = RoboticsGUI()
    app.mainloop()
