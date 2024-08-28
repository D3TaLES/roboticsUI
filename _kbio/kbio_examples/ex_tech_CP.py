""" Bio-Logic OEM package python API.

Script shown as an example of how to run an experiment with a Biologic instrument
using the EC-Lab OEM Package library.

The script uses parameters which are provided below.

"""

import sys
import time
from dataclasses import dataclass

import _kbio.kbio_types as KBIO
from _kbio.kbio_api import KBIO_api

from _kbio.c_utils import c_is_64b
from _kbio.utils import exception_brief

from _kbio.kbio_tech import ECC_parm, make_ecc_parm, make_ecc_parms, print_experiment_data

#------------------------------------------------------------------------------#

# Test parameters, to be adjusted

verbosity = 2

address = "USB0"
# address = "10.100.100.136"
channel = 1

binary_path = "../../EC-Lab Development Package/"

# CP parameter values

cp3_tech_file = "cp.ecc"
cp4_tech_file = "cp4.ecc"

repeat_count = 2
record_dt = 0.1  # seconds
record_dE = 0.1  # Volts
i_range = 'I_RANGE_10mA'

# dictionary of CP parameters (non exhaustive)

CP_parms = {
    'current_step':  ECC_parm("Current_step", float),
    'step_duration': ECC_parm("Duration_step", float),
    'vs_init':       ECC_parm("vs_initial", bool),
    'nb_steps':      ECC_parm("Step_number", int),
    'record_dt':     ECC_parm("Record_every_dT", float),
    'record_dE':     ECC_parm("Record_every_dE", float),
    'repeat':        ECC_parm("N_Cycles", int),
    'I_range':       ECC_parm("I_Range", int),
}

# defining a current step parameter

@dataclass
class current_step :
    current: float
    duration: float
    vs_init: bool = False

# list of step parameters
steps = [
  current_step(0.001, 2), # 1mA during 2s
  current_step(0.002, 1), # 2mA during 1s
  current_step(0.0005, 3, True), # 0.5mA delta during 3s
]

#==============================================================================#

# helper functions

def newline () : print()
def print_exception (e) : print(f"{exception_brief(e, verbosity>=2)}")

def print_messages (ch) :
    """Repeatedly retrieve and print messages for a given channel."""
    while True :
        # BL_GetMessage
        msg = api.GetMessage(id_,ch)
        if not msg : break
        print(msg)

# determine library file according to Python version (32b/64b)

if c_is_64b :
    DLL_file = "EClib64.dll"
else :
    DLL_file = "EClib.dll"

DLL_path = binary_path + DLL_file

#==============================================================================#

"""

Example main :

  * open the DLL,
  * connect to the device using its address,
  * retrieve the device channel info,
  * test whether the proper firmware is running,
  * if it is, print all the messages this channel has accumulated so far,
  * create a CP parameter list (a subset of all possible parameters),
  * load the CP technique into the channel,
  * start the technique,
  * in a loop :
      * retrieve and display experiment data,
      * display messages,
      * stop when channel reports it is no longer running

Note: for each call to the DLL, the base API function is shown in a comment.

"""

try :

    newline()

    # API initialize
    api = KBIO_api(DLL_path)

    # BL_GetLibVersion
    version = api.GetLibVersion()
    print(f"> EcLib version: {version}")
    newline()

    # BL_Connect
    id_, device_info = api.Connect(address)
    print(f"> device[{address}] info :")
    print(device_info)
    newline()

    # detect instrument family
    is_VMP3 = device_info.model in KBIO.VMP3_FAMILY

    # BL_GetChannelInfos
    channel_info = api.GetChannelInfo(id_,channel)
    print(f"> Channel {channel} info :")
    print(channel_info)
    newline()

    if not channel_info.is_kernel_loaded :
        print("> kernel must be loaded in order to run the experiment")
        sys.exit(-1)

    # pick the correct ecc file based on the instrument family
    tech_file = cp3_tech_file if is_VMP3 else cp4_tech_file

    # BL_GetMessage
    print("> messages so far :")
    print_messages(channel)
    newline()

    # BL_Define<xxx>Parameter

    p_steps = list()

    for idx, step in enumerate(steps) :
        parm = make_ecc_parm(api, CP_parms['current_step'], step.current, idx)
        p_steps.append(parm)
        parm = make_ecc_parm(api, CP_parms['step_duration'], step.duration, idx)
        p_steps.append(parm)
        parm = make_ecc_parm(api, CP_parms['vs_init'], step.vs_init, idx)
        p_steps.append(parm)

    # number of steps is one less than len(steps)
    p_nb_steps = make_ecc_parm(api, CP_parms['nb_steps'], idx)

    # record parameters
    p_record_dt = make_ecc_parm(api, CP_parms['record_dt'], record_dt)
    p_record_dE = make_ecc_parm(api, CP_parms['record_dE'], record_dE)

    # repeating factor
    p_repeat = make_ecc_parm(api, CP_parms['repeat'], repeat_count)
    p_I_range  = make_ecc_parm(api, CP_parms['I_range'], KBIO.I_RANGE[i_range].value)

    # make the technique parameter array
    ecc_parms = make_ecc_parms(api, *p_steps, p_nb_steps, p_record_dt, p_record_dE, p_I_range, p_repeat)

    # BL_LoadTechnique
    api.LoadTechnique(id_, channel, tech_file, ecc_parms, first=True, last=True, display=(verbosity>1))

    # BL_StartChannel
    api.StartChannel(id_, channel)

    # experiment loop

    while True :

        # BL_GetData
        data = api.GetData(id_, channel)
        status = print_experiment_data(api, data)

        print("> snaps_20240828 messages :")
        print_messages(channel)

        if status == 'STOP' :
            break

        time.sleep(1);

    print("> experiment done")
    newline()

    # BL_Disconnect
    api.Disconnect(id_)

except KeyboardInterrupt :
    print(".. interrupted")

except Exception as e :
    print_exception(e)

#==============================================================================#
