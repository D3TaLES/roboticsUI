import webbrowser
import tkinter as tk
from PIL import Image, ImageTk
from fireworks import LaunchPad
from collections import OrderedDict
from tkinter.filedialog import askopenfile
from fireworks.core.fworker import FWorker
from fireworks.core.rocket_launcher import launch_rocket, rapidfire

from GUI.app_processing import *
from d3tales_api.D3database.restapi import RESTAPI
from robotics_api.utils.mongo_dbs import MongoDatabase
from robotics_api.fireworks.Workflow_Writer import run_expflow_wf

theme_color_1 = "#FF9004"
theme_color_2 = "#1A3260"
theme_color_3 = "#4590B8"

logo = Image.open("../_setup/docs_src/media/D3TaLES_logo_transparent_robotics.png")
logo_small = logo.resize([int(0.3 * s) for s in logo.size])

expflow_link = r"https://d3tales.as.uky.edu/expflow/robotics_wfs/"


class AlertDialog(tk.Toplevel):

    def __init__(self, parent, alert_msg="Warning. Something went wrong..."):
        super().__init__(parent)
        self.parent = parent
        self.title('')
        tk_logo = ImageTk.PhotoImage(logo_small)
        self.iconphoto(False, tk_logo)
        frame = tk.Canvas(self, width=300, height=100)
        frame.grid(columnspan=4, rowspan=5)
        tk.Label(master=self, text=alert_msg, font=("Raleway", 14, 'bold'), fg=theme_color_2).grid(row=1, column=1,
                                                                                                   padx=20,
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
        tk.Label(master=self, text='Are you sure that you want to quit? ',
                 font=("Raleway", 14, 'bold')).grid(row=1, column=1, columnspan=2, padx=20, pady=20)
        # quitButton
        tk.Button(master=self, text='Yes', command=self.quitALL,
                  font=("Raleway", 14, 'bold')).grid(row=2, column=1, padx=20, pady=2)
        # cancelButton
        tk.Button(master=self, text='No', command=lambda: self.destroy(),
                  font=("Raleway", 14, 'bold')).grid(row=2, column=2, padx=20, pady=2)

    def quitALL(self):
        self.destroy()
        self.parent.destroy()


class SetLocations(tk.Toplevel):
    def __init__(self, parent, experiment_data):
        super().__init__(parent)
        self.parent = parent

        self.title('Set Locations')
        self.experiment_data = experiment_data
        self.reagents = get_exp_reagents(experiment_data)
        self.experiments = get_exps(experiment_data)
        self.reagent_options = reagent_location_options()
        self.vial_options = vial_location_options()
        self.reagents_dict = {}
        self.exp_dict = {}

        self.design_frame()

    def design_frame(self):
        rowspan = max([len(self.reagents), len(self.experiments)]) + 3
        frame = tk.Canvas(self, width=400, height=300)
        frame.grid(columnspan=4, rowspan=rowspan)

        tk_logo = ImageTk.PhotoImage(logo_small)
        self.iconphoto(False, tk_logo)

        # Text
        tk.Label(self, text="Set Locations", font=("Raleway", 36, 'bold'), fg=theme_color_2).grid(column=0, row=0,
                                                                                                  columnspan=4)
        tk.Label(self, text="Set Reagent Locations", font=("Raleway", 24, 'bold'), fg=theme_color_2).grid(column=0,
                                                                                                          row=2,
                                                                                                          columnspan=2)
        tk.Label(self, text="Select the starting position for each reagent.", font=("Raleway", 16, 'bold'), pady=10,
                 wraplength=600, fg=theme_color_2).grid(column=0, row=2, columnspan=2)
        tk.Label(self, text="Set Experiment Vial Locations", font=("Raleway", 24, 'bold'), fg=theme_color_2).grid(
            column=2,
            row=2,
            columnspan=2)
        tk.Label(self, text="Select the starting vial home position for each experiment. The selected position"
                            "specifies the column then the row (e.g., A_03 is column A, row 03).",
                 font=("Raleway", 16, 'bold'), pady=10, wraplength=600, fg=theme_color_2).grid(column=2, row=2,
                                                                                               columnspan=2)

        # Ragent location Dropdowns
        for i, reagent in enumerate(self.reagents):
            tk.Label(self, text="{}\n{}".format(reagent[0], reagent[1]), justify="center", font=("Raleway", 16,),
                     fg=theme_color_2).grid(column=0, row=i + 3)
            dropdown_txt = tk.StringVar()
            dropdown_txt.set(self.reagent_options[0])
            dropdown = tk.OptionMenu(self, dropdown_txt, *self.reagent_options)
            dropdown.config(font=("Raleway", 14), bg=theme_color_3, fg='white', height=2, width=15)
            dropdown.grid(column=1, row=i + 3)
            self.reagents_dict[reagent[1]] = dropdown_txt

        # Vial location Dropdowns
        for i, exp in enumerate(self.experiments):
            tk.Label(self, text="{}".format(exp), justify="center", font=("Raleway", 16,),
                     fg=theme_color_2).grid(column=2, row=i + 3)
            dropdown_txt = tk.StringVar()
            dropdown_txt.set(self.vial_options[i])
            dropdown = tk.OptionMenu(self, dropdown_txt, *self.vial_options)
            dropdown.config(font=("Raleway", 14), bg=theme_color_3, fg='white', height=2, width=10)
            dropdown.grid(column=3, row=i + 3)
            self.exp_dict[exp] = dropdown_txt

        # button
        self.run_txt = tk.StringVar()
        self.run_txt.set("Set Locations and Add Workflow")
        tk.Button(self, textvariable=self.run_txt, font=("Raleway", 14), bg=theme_color_1, command=self.set_parameters,
                  fg='white', height=2, width=30).grid(column=1, row=rowspan, columnspan=2, pady=10)

        tk.Canvas(self, width=400, height=50 + 10 * rowspan).grid(columnspan=2)

    def set_parameters(self):
        self.run_txt.set("adding workflow...")
        exp_params = assign_locations({r: dt.get() for r, dt in self.reagents_dict.items()},
                                      {r: dt.get() for r, dt in self.exp_dict.items()},
                                      self.experiment_data)
        self.parent.EXP_PARAMS = exp_params
        self.destroy()


class AddJob(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title('Add a Workflow')
        self.design_frame()
        self.EXP_PARAMS = {}

    def design_frame(self):
        frame = tk.Canvas(self, width=400, height=300)
        frame.grid(columnspan=4, rowspan=6)

        tk_logo = ImageTk.PhotoImage(logo_small)
        self.iconphoto(False, tk_logo)

        # Text
        tk.Label(self, text="Add a Workflow", font=("Raleway", 26, 'bold'), fg=theme_color_2).grid(column=1, row=0)
        tk.Label(self, text="Select a workflow file: ", font=("Raleway", 14), fg=theme_color_2).grid(column=0, row=1)

        # buttons
        tk.Button(self, text="Select a Workflow", command=self.open_file, font=("Raleway", 14), bg=theme_color_3,
                  fg='white', height=2, width=30).grid(columnspan=2, column=0, row=2)
        tk.Button(self, text="Build a Workflow\non ExpFlow", command=self.build_wf, font=("Raleway", 14),
                  bg=theme_color_2, fg='white', height=4, width=20).grid(column=2, row=2, padx=10)
        self.add_txt = tk.StringVar()
        self.add_txt.set("Add Selected Workflow")
        tk.Button(self, textvariable=self.add_txt, command=self.add_wf, font=("Raleway", 16), bg=theme_color_1,
                  fg='white', height=2, width=45).grid(columnspan=3, column=0, row=5)

        # Selected Workflow
        tk.Label(self, text="\nSelected Workflow: \n", font=("Raleway", 16), fg=theme_color_2).grid(column=0, row=3,
                                                                                                    pady=30)
        self.selected_txt = tk.StringVar()
        self.selected_txt.set('')
        tk.Label(self, textvariable=self.selected_txt,
                 font=("Raleway", 16, 'bold'), fg=theme_color_2).grid(column=1, row=3, pady=30)
        tk.Label(self, text="", font=("Raleway", 12), fg=theme_color_2).grid(column=3, row=3, padx=10)

        tk.Canvas(self, width=400, height=50).grid(columnspan=3)

        # Name Tag
        self.name_tag = tk.StringVar()
        self.name_tag.set('')
        tk.Label(self, text="Workflow Name Tag", font=("Raleway", 14), fg=theme_color_2).grid(column=0, row=4)
        tk.Entry(self, textvariable=self.name_tag, font=("Raleway", 16, 'bold'), width=30, fg=theme_color_2).grid(
            column=1,
            row=4,
            pady=30)

    @property
    def lpad(self):
        return LaunchPad().from_file(os.path.abspath(LAUNCHPAD.as_posix()))

    def open_file(self):
        self.selected_txt.set("loading file...")
        file = askopenfile(parent=self, mode='r', title="Chose a workflow file.", filetypes=[('JSON file', "*.json")])
        if file:
            self.json_data = json.load(file)
            self.selected_txt.set(self.json_data.get("name"))

    def add_wf(self):
        self.add_txt.set("adding workflow...")
        window = SetLocations(self, self.json_data)
        self.wait_window(window)
        self.add_txt.set("adding workflow...")
        wf = run_expflow_wf(self.json_data, name_tag=self.name_tag.get(), exp_params=self.EXP_PARAMS)
        info = self.lpad.add_wf(wf)
        fw_id = list(info.values())[0]

        # # Pause READY jobs
        # p = subprocess.Popen("lpad pause_fws -s READY", stdout=subprocess.PIPE, shell=True)
        # p.communicate()

        AlertDialog(self, alert_msg="Your workflow was successfully submitted!\nAll READY jobs have "
                                    "been paused. \nWorkflow ID: " + str(fw_id))
        self.add_txt.set("Add Selected Workflow")
        self.destroy()

    # @staticmethod
    def build_wf(self):
        webbrowser.open_new(expflow_link)


class PushToDB(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title('Push data to DB')
        self.workflow = tk.StringVar()
        self.workflow.set("")
        self.lpad = LaunchPad().from_file(os.path.abspath(LAUNCHPAD.as_posix()))

        self.design_frame()

    def design_frame(self):
        frame = tk.Canvas(self, width=100, height=200)
        frame.grid(columnspan=2, rowspan=3)

        tk_logo = ImageTk.PhotoImage(logo_small)
        self.iconphoto(False, tk_logo)

        # Text
        tk.Label(self, text="Push Data From a Workflow to Master Database", font=("Raleway", 26, 'bold'),
                 fg=theme_color_2).grid(column=0, row=0, columnspan=2)
        # Dropdown
        tk.Label(self, text="Select Workflow: ", justify="center", font=("Raleway", 16,), fg=theme_color_2).grid(
            column=0, row=1)
        self.workflow = tk.StringVar()
        self.workflow.set("")
        workflows = self.lpad.workflows.find({}).distinct("name")
        dropdown = tk.OptionMenu(self, self.workflow, *workflows)
        dropdown.config(font=("Raleway", 12), bg=theme_color_3, fg='white', height=1, width=45)
        dropdown.grid(column=1, row=1)

        # Button
        tk.Button(self, text="Push data from workflow", command=self.select_wf,
                  font=("Raleway", 16), bg=theme_color_1, fg='white', height=2,
                  width=45).grid(columnspan=2, column=0, row=2)

    def select_wf(self):
        window = PushToDB_Exp(self, self.workflow.get())
        window.grab_set()


class PushToDB_Exp(tk.Toplevel):
    def __init__(self, parent, wflow_name):
        super().__init__(parent)

        self.title('Push data to DB')
        self.workflow = tk.StringVar()
        self.workflow.set("")
        self.lpad = LaunchPad().from_file(os.path.abspath(LAUNCHPAD.as_posix()))
        workflow_nodes = self.lpad.workflows.find_one({"name": wflow_name}).get("nodes")
        self.processing_fws = self.get_processing_fws(workflow_nodes)

        self.design_frame()

    def design_frame(self):
        rowspan = len(self.processing_fws) + 3
        frame = tk.Canvas(self, width=400, height=600)
        frame.grid(columnspan=2, rowspan=rowspan)

        tk_logo = ImageTk.PhotoImage(logo_small)
        self.iconphoto(False, tk_logo)

        # Text
        tk.Label(self, text="Push Data From a Workflow to Master Database", font=("Raleway", 26, 'bold'),
                 fg=theme_color_2).grid(column=0, row=0, columnspan=2)
        # Dropdown
        tk.Label(self, text="Select Experiment Fireworks to Push: ", justify="center", font=("Raleway", 16,),
                 fg=theme_color_2).grid(column=0, row=1)
        self.push_dict = {}
        for i, fw_id in enumerate(self.processing_fws.keys()):
            push_var = tk.BooleanVar()
            checkbox = tk.Checkbutton(self, text=self.processing_fws[fw_id], variable=push_var, onvalue=True,
                                      offvalue=False, justify="left")
            checkbox.grid(column=0, row=i + 2)
            button = tk.Button(self, text="View Data", fg=theme_color_3, font=("Raleway", 9, "bold"),
                               command=lambda: self.dir_open(fw_id))
            button.grid(column=1, row=i + 2)
            self.push_dict[fw_id] = push_var

        # Button
        tk.Button(self, text="Push selected data to Master DB".format(self.workflow), command=self.push_wf,
                  font=("Raleway", 16), bg=theme_color_1, fg='white', height=2, width=45).grid(columnspan=3, column=0,
                                                                                               row=rowspan - 1)

    def dir_open(self, fw_id):
        query = self.lpad.fireworks.find_one({'fw_id': int(fw_id)}, {"spec.collection_data.data_location": 1})
        exp_dir = "\\".join(
            query.get("spec", {}).get("collection_data", [{}])[0].get("data_location", "").split("\\")[:-1]
        )
        print("Opening directory: ", exp_dir)
        os.system("explorer {}".format(exp_dir))

    def push_wf(self):
        fw_ids = [i for i, b in self.push_dict.items() if b.get()]
        launch_ids = []
        [launch_ids.extend(l.get("launches")) for l in
         self.lpad.fireworks.find({'fw_id': {"$in": fw_ids}}, {"launches": 1})]
        launches = [self.lpad.launches.find_one({'launch_id': l_id}, {"action.update_spec": 1}) for l_id in launch_ids]
        for launch in launches:
            p_ids = launch.get("action", {}).get("update_spec", {}).get("processing_data", {}).get("processing_ids")
            m_id = launch.get("action", {}).get("update_spec", {}).get("processing_data", {}).get("metadata_id")
            meta_dict = MongoDatabase(database="robotics", collection_name="metadata"
                                      ).coll.find_one({"_id": m_id}).get("metadata")
            mol_id = None

            for p_id in p_ids:
                p_data = MongoDatabase(database="robotics", collection_name="experimentation").coll.find_one(
                    {"_id": p_id})
                MongoDatabase(database="robotics_master", collection_name="backend",
                              instance=p_data, validate_schema=False).insert(p_data["_id"])
                mol_id = p_data["mol_id"]  # TODO if > 1 mol id is ever in an experiment, this will need to change

            # Insert frontend data
            frontend_db = MongoDatabase(database="robotics_master", collection_name="frontend", validate_schema=False)
            if not frontend_db.coll.find_one({"_id": mol_id}):
                response = RESTAPI(method='get', endpoint="restapi/molecules/_id={}/mol_info=1".format(mol_id),
                                   url="https://d3tales.as.uky.edu", return_json=True).response
                if not response:
                    raise Exception(f"Error finding D3TaLES database entry for id {mol_id}.")
                mol_info = response[0].get("mol_info", {})
                frontend_db.coll.insert_one({"_id": mol_id, "mol_info": mol_info})
            frontend_db.insert(mol_id, nested=True, instance={
                "mol_characterization": meta_dict,
                "experiment_ids": p_ids
            })

        AlertDialog(self, alert_msg="All data has been pushed for experiments {}!".format(
            ", ".join([self.processing_fws[i] for i in fw_ids])))

    def get_processing_fws(self, workflow_nodes):
        query = self.lpad.fireworks.find({'fw_id': {"$in": workflow_nodes},
                                          'name': {'$regex': '_process_.*data'},
                                          "state": "COMPLETED"}, {"fw_id": 1, "name": 1})
        fw_dict = {q.get("fw_id"): q.get("name") for q in query}
        return OrderedDict(sorted(fw_dict.items(), key=lambda x: x[1]))


class ManageJobs(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title('Manage Jobs')
        self.fw_action = tk.StringVar()
        self.fw_specs = tk.StringVar()
        self.fw_output = tk.Text(self)
        self.return_fw_ids = tk.BooleanVar()
        self.fw_options = ["get_fws", "rerun_fws", "pause_fws", "defuse_fws"]
        self.wflow_action = tk.StringVar()
        self.wflow_specs = tk.StringVar()
        self.wflow_output = tk.Text(self)
        self.return_wflow_ids = tk.BooleanVar()
        self.wflow_options = ["get_wflows", "defuse_wflows", "delete_wflows"]
        self.design_frame()

    def design_frame(self):
        frame = tk.Canvas(self, width=400, height=600)
        frame.grid(columnspan=2, rowspan=10)

        tk_logo = ImageTk.PhotoImage(logo_small)
        self.iconphoto(False, tk_logo)
        
        # Text
        tk.Label(self, text="Manage Fireworks", font=("Raleway", 24, 'bold'), fg=theme_color_2).grid(column=0, row=0,
                                                                                                     columnspan=2,
                                                                                                     pady=10)

        # Dropdown
        tk.Label(self, text="Fireworks Action: ", justify="center", font=("Raleway", 16,), fg=theme_color_2).grid(
            column=0,
            row=1)
        self.fw_action.set("get_fws")
        dropdown = tk.OptionMenu(self, self.fw_action, *self.fw_options)
        dropdown.config(font=("Raleway", 14), bg=theme_color_3, fg='white', height=2, width=30)
        dropdown.grid(column=1, row=1)

        # Specification tags
        self.fw_specs.set('-s FIZZLED')
        tk.Label(self, text="Specifications: ", font=("Raleway", 14), fg=theme_color_2).grid(column=0, row=2)
        tk.Entry(self, textvariable=self.fw_specs, font=("Raleway", 16, 'bold'), width=30, fg=theme_color_2).grid(
            column=1,
            row=2)

        # Return IDs Checkbox
        tk.Checkbutton(self, text='Return list of FW IDs', variable=self.return_fw_ids, onvalue=True,
                       offvalue=False).grid(column=0, row=3)
        # Button
        tk.Button(self, text="Run Fireworks Action", command=self.do_fw_action, font=("Raleway", 10), bg=theme_color_3,
                  fg='white', height=1, width=15).grid(column=1, row=3)

        # Output
        self.fw_output = tk.Text(self, wrap=tk.WORD, font=("Consolas", 10), width=70, height=5)
        self.fw_output.grid(column=0, row=4, columnspan=2)

        tk.Canvas(self, width=400, height=50).grid(columnspan=2)

        # Text
        tk.Label(self, text="Manage Workflows", font=("Raleway", 24, 'bold'), fg=theme_color_2).grid(column=0, row=5,
                                                                                                     columnspan=2,
                                                                                                     pady=10)

        # Dropdown
        tk.Label(self, text="Workflows Action: ", justify="center", font=("Raleway", 16,), fg=theme_color_2).grid(
            column=0,
            row=6)
        self.wflow_action.set("get_wflows")
        dropdown = tk.OptionMenu(self, self.wflow_action, *self.wflow_options)
        dropdown.config(font=("Raleway", 14), bg=theme_color_1, fg='white', height=2, width=30)
        dropdown.grid(column=1, row=6)

        # Specification tags
        self.wflow_specs.set('-s FIZZLED')
        tk.Label(self, text="Specifications: ", font=("Raleway", 14), fg=theme_color_2).grid(column=0, row=7)
        tk.Entry(self, textvariable=self.wflow_specs, font=("Raleway", 16, 'bold'), width=30, fg=theme_color_2).grid(
            column=1,
            row=7)

        # Return IDs Checkbox
        tk.Checkbutton(self, text='Return list of Workflow IDs', variable=self.return_wflow_ids, onvalue=True,
                       offvalue=False).grid(column=0, row=8)
        # Button
        tk.Button(self, text="Run Workflow Action", command=self.do_wflow_action, font=("Raleway", 10),
                  bg=theme_color_1,
                  fg='white', height=1, width=15).grid(column=1, row=8)

        # Output
        self.wflow_output = tk.Text(self, wrap=tk.WORD, font=("Consolas", 10), width=70, height=5)
        self.wflow_output.grid(column=0, row=9, columnspan=2)

    @property
    def lpad(self):
        return LaunchPad().from_file(os.path.abspath(LAUNCHPAD.as_posix()))

    def do_fw_action(self):
        cmd = "lpad {} {}".format(self.fw_action.get(), self.fw_specs.get())
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        output, err = p.communicate()
        output_text = output.decode("utf-8")
        if self.return_fw_ids.get():
            try:
                out_list = eval("[{}]".format(output.decode("utf-8").split("[")[1].split("]")[0]))
                output_text = ",".join([str(f.get("fw_id")) for f in out_list])
            except:
                pass
        self.fw_output.delete("1.0", "end")
        self.fw_output.insert(tk.INSERT, output_text)
        AlertDialog(self, alert_msg="Your action has been completed!")

    def do_wflow_action(self):
        cmd = "lpad {} {}".format(self.wflow_action.get(), self.wflow_specs.get())
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        output, err = p.communicate()
        output_text = output.decode("utf-8")
        if self.return_wflow_ids.get():
            try:
                out_list = eval("[{}]".format(output.decode("utf-8").split("[")[1].split("]")[0]))
                output_text = ",".join([f.get("name").split("--")[-1] for f in out_list])
            except:
                pass
        self.wflow_output.delete("1.0", "end")
        self.wflow_output.insert(tk.INSERT, output_text)
        AlertDialog(self, alert_msg="Your action has been completed!")


class RunBase(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.fireworker = None
        self.category = ""
        self.run_txt = tk.StringVar()
        self.run_all_txt = tk.StringVar()
        self.run_cont_txt = tk.StringVar()

    @property
    def lpad(self):
        return LaunchPad().from_file(os.path.abspath(LAUNCHPAD.as_posix()))

    @property
    def next_fw(self):
        m_fw = self.lpad.fireworks.find_one({"state": "READY", "spec._category": self.category},
                                            {"fw_id": 1, "spec": 1},
                                            sort=[("spec._priority", -1)])
        fw = self.lpad.get_fw_by_id(m_fw["fw_id"]) if m_fw else None
        if fw:
            return str(fw.name or fw.fw_id)
        else:
            return "No ready firework found."

    def design_frame(self):
        frame = tk.Canvas(self, width=400, height=400)
        frame.grid(columnspan=1, rowspan=6)

        tk_logo = ImageTk.PhotoImage(logo_small)
        self.iconphoto(False, tk_logo)

        # Text
        tk.Label(self, text=f"Run {self.category.capitalize()} Jobs", font=("Raleway", 36, 'bold'),
                 fg=theme_color_2).grid(
            column=0, row=0)
        tk.Label(self, text="The Next Job(s):\t" + self.next_fw, font=("Raleway", 16, 'bold'), fg=theme_color_2).grid(
            column=0,
            row=1)

        # buttons
        self.run_txt.set("Run a Job")
        self.run_all_txt.set("Run All Ready Jobs")
        self.run_cont_txt.set("Run Jobs Continuously")
        tk.Button(self, text="View Workflows", command=self.view_fw_workflows, font=("Raleway", 10), bg=theme_color_2,
                  fg='white', height=1, width=15).grid(column=0, row=2)
        tk.Button(self, textvariable=self.run_txt, font=("Raleway", 14), bg=theme_color_1, command=self.run_job,
                  fg='white',
                  height=2, width=30).grid(column=0, row=3)
        tk.Button(self, textvariable=self.run_all_txt, font=("Raleway", 14), bg=theme_color_1, command=self.run_job_all,
                  fg='white', height=2, width=30).grid(column=0, row=4)
        tk.Button(self, textvariable=self.run_cont_txt, font=("Raleway", 14), bg=theme_color_1,
                  command=self.run_job_continuous, fg='white', height=2, width=30).grid(column=0, row=5)

        tk.Canvas(self, width=400, height=50).grid(columnspan=3)

    def run_job(self):
        self.run_txt.set("Launching {} Job...".format(self.category.capitalize()))
        os.chdir(LAUNCH_DIR)
        launch_rocket(launchpad=self.lpad, fworker=self.fireworker)
        AlertDialog(self, alert_msg="Firework successfully launched!")
        self.run_txt.set("Run a Job")
        self.destroy()

    def run_job_all(self):
        self.parent.destroy()
        os.chdir(LAUNCH_DIR)
        print('LAUNCHING ALL READY {} JOBS...\n\n'.format(self.category.upper()))
        rapidfire(launchpad=self.lpad, fworker=self.fireworker, nlaunches=0)

    def run_job_continuous(self):
        self.parent.destroy()
        os.chdir(LAUNCH_DIR)
        print('LAUNCHING {} JOBS CONTINUOUSLY...\n\n'.format(self.category.upper()))
        rapidfire(launchpad=self.lpad, fworker=self.fireworker, nlaunches=-1, sleep_time=10)

    def view_fw_workflows(self):
        self.parent.destroy()
        subprocess.call('lpad -l {} webgui'.format(LAUNCHPAD))


class RunInit(RunBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title('Initialize Workflow')
        self.fireworker = FWorker.from_file(INIT_FWORKER.as_posix())
        self.category = "initialize"
        self.design_frame()


class RunRobot(RunBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title('Run Robot')
        self.fireworker = FWorker.from_file(ROBOT_FWORKER.as_posix())
        self.category = "robotics"
        self.design_frame()


class RunProcess(RunBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title('Run Processing')
        self.fireworker = FWorker.from_file(PROCESS_FWORKER.as_posix())
        self.category = "processing"
        self.design_frame()


class RunInstrument(RunBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title('Run Instruments')
        self.fireworker = FWorker.from_file(INSTRUMENT_FWORKER.as_posix())
        self.category = "instrument"
        self.design_frame()


class RoboticsGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title('D3TaLES Robotics')
        self.design_frame()

    def design_frame(self):
        info_frame = tk.Canvas(self, width=500, height=300)
        info_frame.grid(columnspan=2, rowspan=6)

        # logo
        logo = ImageTk.PhotoImage(logo_small)
        logo_label = tk.Label(image=logo)
        logo_label.image = logo
        logo_label.grid(columnspan=2, column=0, row=0)
        self.iconphoto(False, logo)

        # buttons
        view_workflows = tk.Button(self, text="View Workflows", command=self.view_fw_workflows, font=("Raleway", 14),
                                   bg=theme_color_2, fg='white', height=1, width=15)
        view_workflows.grid(column=0, row=2, pady=5)
        manage_jobs = tk.Button(self, text="Manage Jobs", command=self.open_manage, font=("Raleway", 14),
                                bg=theme_color_2, fg='white', height=1, width=15)
        manage_jobs.grid(column=0, row=3, pady=5)
        add_job = tk.Button(self, text="Add Workflow", command=self.open_add, font=("Raleway", 14), bg=theme_color_2,
                            fg='white',
                            height=1, width=15)
        add_job.grid(column=0, row=4, pady=5)
        push_to_db = tk.Button(self, text="Push Data to DB", command=self.open_push, font=("Raleway", 14),
                               bg=theme_color_3, fg='white', height=1, width=15)
        push_to_db.grid(column=0, row=5, pady=5)

        run_job = tk.Button(self, text="Initialize Workflow", command=self.open_run, font=("Raleway", 14),
                            bg=theme_color_3,
                            fg='white', height=1, width=20)
        run_job.grid(column=1, row=2, pady=5)
        run_robot = tk.Button(self, text="Run Robot", command=self.open_run_robot, font=("Raleway", 14),
                              bg=theme_color_1,
                              fg='white', height=1, width=20)
        run_robot.grid(column=1, row=3, pady=5)
        run_process = tk.Button(self, text="Run Process", command=self.open_run_process, font=("Raleway", 14),
                                bg=theme_color_1,
                                fg='white', height=1, width=20)
        run_process.grid(column=1, row=4, pady=5)
        run_instrument = tk.Button(self, text="Run Instruments", command=self.open_run_instrument, font=("Raleway", 14),
                                   bg=theme_color_1,
                                   fg='white', height=1, width=20)
        run_instrument.grid(column=1, row=5, pady=5)

        tk.Canvas(self, width=400, height=50).grid(columnspan=2)

        # self.mainloop()

    def open_push(self):
        window = PushToDB(self)
        window.grab_set()

    def open_manage(self):
        window = ManageJobs(self)
        window.grab_set()

    def open_add(self):
        window = AddJob(self)
        window.grab_set()

    def open_run(self):
        window = RunInit(self)
        window.grab_set()

    def open_run_robot(self):
        window = RunRobot(self)
        window.grab_set()

    def open_run_process(self):
        window = RunProcess(self)
        window.grab_set()

    def open_run_instrument(self):
        window = RunInstrument(self)
        window.grab_set()

    def view_fw_workflows(self):
        self.destroy()
        subprocess.call('lpad -l {} webgui'.format(LAUNCHPAD))


if __name__ == "__main__":
    py_path = f"{HOME_DIR};{PARENT_DIR / 'Packages' / 'd3tales_api'};{PARENT_DIR / 'Packages' / 'hardpotato' / 'src'}"
    os.environ['FW_CONFIG_FILE'] = os.path.abspath(FW_CONFIG_DIR / 'FW_config.yaml')
    os.environ['DB_INFO_FILE'] = os.path.abspath(HOME_DIR / 'db_infos.json')
    os.environ['PYTHONPATH'] = py_path
    robotics_app = RoboticsGUI()
    robotics_app.mainloop()
