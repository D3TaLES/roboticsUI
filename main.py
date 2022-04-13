import tkinter.messagebox
import uuid
from tkinter import *
import tkinter.font as font
import json
from tinydb import TinyDB, Query
import time
import os
from tkinter import filedialog as fd

USER = os.getlogin()
WORKDIR = r"C:\Users\{}\D3tics".format(USER)

if not os.path.exists(WORKDIR):
    os.makedirs(WORKDIR)

# mainWindow
root = Tk()
root.geometry("800x800")
root.configure(bg="white")
d3font = font.Font(size=15, weight="bold")


global data

def select_file():
    filetypes = (
        ('python files', '*.py'),
    )
    global filename
    filename = fd.askopenfilename(
        title='Open a file',
        initialdir=r"C:\Users\{}\Desktop".format(USER),
        filetypes=filetypes)
    open_py_file["text"] = "Selected file is \n {}".format(filename)

def reset_db():
    db = TinyDB(r"{}\db.json".format(WORKDIR))
    db.drop_tables()
    tkinter.messagebox.showwarning("View Database","Database was reset")
    json_window.destroy()

def run_script():
    identifier = uuid.uuid4().__str__()
    path = "{}/{}".format(WORKDIR,identifier)
    os.makedirs(path)
    os.system("python {}".format(filename))
    with open("{}/rundata.txt".format(path),"w") as f:
        f.write("This is a demo file")
    data = {}

    db = TinyDB(r"{}\db.json".format(WORKDIR))
    db.insert({ "identifier": identifier,
                "python_file":filename,
                "username":USER.lower(),
                "data":data,
                "last_updated":time.asctime(time.localtime(time.time()))})
    tkinter.messagebox.showinfo("Run Robot","Run successful! Database is now updated")


    robot_window.destroy()

def jsonview():
    global json_window
    # create window
    json_window = Toplevel()
    json_window.geometry("500x500")
    json_window.title("View Database")

    # load database
    db = TinyDB(r"{}\db.json".format(WORKDIR))
    text = json.dumps(db.all(), indent=2)

    # add data text to window
    label = Label(json_window, text=text, font="Times", justify='left')
    label.pack()

    rest_button = Button(json_window, text="Rest database",command=reset_db)
    rest_button.pack()

def robot():
    global robot_window
    # create window
    robot_window = Toplevel()
    robot_window.geometry("500x500")
    robot_window.title("Run Robot")

    # ask for the python file for robot
    text = "Select python file to run"
    open_py_label = Label(robot_window, text=text, font="Times", justify='left')
    open_py_label.pack()
    open_py = Button(robot_window, text="Browse", wraplength=100,
                     height=5, width=15,
                     command=select_file)
    open_py["font"] = d3font
    open_py.pack()

    file_selected = "Selected file is "
    global open_py_file
    open_py_file = Label(robot_window, text=file_selected, font="Times", justify='left')
    open_py_file.pack()
    # run the python file
    run_py = Button(robot_window, text="Run Now", wraplength=100,
                     height=5, width=15,
                     command=run_script)
    run_py["font"] = d3font
    run_py.pack()




info_frame = Frame()
info_frame.config(bg="white")
welcome_text = "Hello, {}!\n\n" \
               "Welcome to the D3TaLES robotics platform.".format(USER.capitalize())
welcome_label = Label(info_frame, text=welcome_text,bg="white",pady=100,
                      anchor="w",justify=LEFT)
welcome_label["font"] = font.Font(size=13,)
welcome_label.pack()
info_frame.pack()

buttons_frame = Frame()
buttons_frame.config(bg="white")

view_db = Button(buttons_frame, text="View Database",wraplength=100,
                 height=5,width=15,
                 command=jsonview)
view_db["font"] = d3font
view_db.grid(row=0,column=0,padx=20,pady=50)

run_robot = Button(buttons_frame, text="Run Robot",wraplength=100,
                 height=5,width=15, bg="#1a3260", fg="white",
                 command=robot)
run_robot["font"] = d3font
run_robot.grid(row=0,column=2,padx=10,pady=50)

buttons_frame.pack()

root.mainloop()



