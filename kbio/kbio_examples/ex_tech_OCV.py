""" Bio-Logic OEM package python API.

Script shown as an example of how to run an experiment with a Biologic instrument
using the EC-Lab OEM Package library.

The script uses parameters which are provided below.

"""

import sys
import time

import kbio.kbio_types as KBIO
from kbio.kbio_api import KBIO_api

from kbio.c_utils import c_is_64b
from kbio.utils import exception_brief

from kbio.kbio_tech import ECC_parm, make_ecc_parm, make_ecc_parms, print_experiment_data

#------------------------------------------------------------------------------#

# Test parameters, to be adjusted

verbosity = 2

# address = "USB0"
address = "10.100.100.136"
channel = 11

binary_path = "../../EC-Lab Development Package/"

# OCV parameter values

ocv3_tech_file   = "ocv.ecc"
ocv4_tech_file   = "ocv4.ecc"

duration = 10.   # seconds
record_dt = 0.1  # seconds
e_range = 'E_RANGE_10V'

# dictionary of OCV parameters (non exhaustive)

OCV_parms = {
    'duration':  ECC_parm("Rest_time_T", float),
    'record_dt': ECC_parm("Record_every_dT", float),
    'record_dE': ECC_parm("Record_every_dE", float),
    'E_range':   ECC_parm("E_Range", int),
    'timebase':  ECC_parm('tb', int),
}

#==============================================================================#

# helper functions

def newline () : print()
def print_exception (e) : print(f"{exception_brief(e, verbosity>=2)}")

def print_messages (ch) :
    """Repeatedly retrieve and print messages for a given channel."""
    while True :
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
  * create an OCV parameter list (a subset of all possible parameters),
  * load the OCV technique into the channel,
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
    tech_file = ocv3_tech_file if is_VMP3 else ocv4_tech_file

    # BL_GetMessage
    print("> messages so far :")
    print_messages(channel)
    newline()

    # BL_Define<xxx>Parameter
    p_duration = make_ecc_parm(api, OCV_parms['duration'], duration)
    p_record = make_ecc_parm(api, OCV_parms['record_dt'], record_dt)
    p_erange = make_ecc_parm(api, OCV_parms['E_range'], KBIO.E_RANGE[e_range].value)
    ecc_parms = make_ecc_parms(api, p_duration, p_record, p_erange)

    # BL_LoadTechnique
    api.LoadTechnique(id_, channel, tech_file, ecc_parms, first=True, last=True, display=(verbosity>1))

    # BL_StartChannel
    api.StartChannel(id_, channel)

    # experiment loop

    while True :

        # BL_GetData
        data = api.GetData(id_, channel)
        status = print_experiment_data(api, data)

        print("> new messages :")
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
