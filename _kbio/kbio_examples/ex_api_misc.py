""" Bio-Logic OEM package python API.

Script shown as an example of how to interface with a Biologic instrument
in Python using the EC-Lab OEM Package library.

The script uses parameters which are provided below.

"""

import sys

import _kbio.kbio_types as KBIO
from _kbio.kbio_api import KBIO_api

from _kbio.c_utils import c_is_64b
from _kbio.utils import exception_brief

#------------------------------------------------------------------------------#

# Test parameters, to be adjusted

address = "USB0"
# address = "10.100.100.136"
channel = 1
timeout = 10

verbosity = 3
load_firmware = True

binary_path = "../../EC-Lab Development Package/"

#==============================================================================#

# Helper functions

def newline () : print()
def print_exception (e) : print(f"{exception_brief(e,verbosity)}")

def print_messages (ch) :
    while True :
        msg = api.GetMessage(id_,ch)
        if not msg : break
        print(msg)

def print_USB_info (index) :
    """Print device information at USB index, if any."""
    try :
        info = api.USB_DeviceInfo(index)
        print(f"> USB{index} info : {info}")
    except Exception as e :
        print(f"> USB{index} info : {e}")

# determine library file according to Python version (32b/64b)

newline()

if c_is_64b :
    print("> 64b application")
    DLL_file = "EClib64.dll"
else :
    print("> 32b application")
    DLL_file = "EClib.dll"

DLL_path = binary_path + DLL_file

#==============================================================================#

"""

Example main code : excercise various OEM package API calls.

  * open the DLL,
  * display its version,
  * display connected USB devices info if any,
  * connect to the device (whose address is defined above),
  * show relevant device info,
  * test whether the connection is working,
  * enumerate the channels available for that device,
  * retrieve and show the channel info (for the channel defined above),
  * optionally load the firmware if required,
  * re-display the channel info (might have changed if firmware was not loaded before),
  * display communication speed indication,
  * print messages that the firmware has issued,
  * display and modify the instrument hardware configuration,
  * disconnect from the target,
  * show how to translate an error code to a descriptive text,
  * demonstrate that an exception is raised in case of error
   (here calling a function after being disconnected)

Note: for each call to the DLL, the base API function is shown in a comment.

"""


try :

    # API initialize
    api = KBIO_api(DLL_path)

    # BL_GetLibVersion
    version = api.GetLibVersion()
    print(f"> EcLib version: {version}")
    newline()

    # BL_GetUSBdeviceinfos
    print_USB_info(0)
    print_USB_info(1)
    newline()

    # BL_Connect
    id_, device_info = api.Connect(address,timeout)
    print(f"> device[{address}] info :")
    print(device_info)
    newline()

    # detect instrument family
    is_VMP3   = device_info.model in KBIO.VMP3_FAMILY
    is_VMP300 = device_info.model in KBIO.VMP300_FAMILY

    # BL_TestConnection
    ok = "OK" if api.TestConnection(id_) else "not OK"
    print(f"> device[{address}] connection : {ok}")
    newline()

    # BL_GetChannelsPlugged
    # .. PluggedChannels is a generator, expand into a set
    channels = {*api.PluggedChannels(id_)}
    print(f"> device[{address}] channels : {channels}")
    newline()

    # test whether the configured channel exists
    if channel not in channels :
        print(f"Configured channel {channel} does not belong to device channels {channels}")
        sys.exit(-1)

    # BL_GetChannelInfos
    channel_info = api.GetChannelInfo(id_,channel)
    print(f"> Channel {channel} info :")
    print(channel_info)
    newline()

    # based on family, determine firmware filenames
    if is_VMP3 :
        firmware_path = "kernel.bin"
        fpga_path     = "Vmp_ii_0437_a6.xlx"
    elif is_VMP300 :
        firmware_path = "kernel4.bin"
        fpga_path     = "vmp_iv_0395_aa.xlx"
    else :
        firmware_path = None

    if firmware_path :
        print(f"> Loading {firmware_path} ...")
        # create a map from channel set
        channel_map = api.channel_map({channel})
        # BL_LoadFirmware
        api.LoadFirmware(id_, channel_map, firmware=firmware_path, fpga=fpga_path, force=load_firmware)
        print("> ... firmware loaded")
        newline()

    # re-display info, as loading firmware provides more
    print(f"> Channel {channel} info :")
    # BL_GetChannelInfos
    info = api.GetChannelInfo(id_,channel)
    print(info)
    newline()

    # BL_TestCommSpeed
    rcvt_speed, firmware_speed = api.TestComSpeed(id_, channel)
    speeds = {'rcvt': rcvt_speed, 'firmware': firmware_speed}
    print(f"> device[{address}] speeds :")
    print(speeds)
    newline()

    # BL_GetMessage
    print("> Messages so far :")
    print_messages(channel)
    newline()

    # the following functions are ony valid for a VMP300
    if is_VMP300 :

        # BL_GetHardConf
        hw_conf = api.GetHardwareConf(id_, channel)
        hw_conf = { 'cnx': hw_conf.connection, 'mode': hw_conf.mode }
        print("> current hardware configuration :")
        print(hw_conf)

        # BL_SetHardConf
        cnx = KBIO.HW_CNX.WE_TO_GND
        mode = KBIO.HW_MODE.FLOATING
        api.SetHardwareConf(id_, channel, cnx.value, mode.value)

        # BL_GetHardConf
        hw_conf = api.GetHardwareConf(id_, channel)
        hw_conf = {'cnx': hw_conf.connection, 'mode': hw_conf.mode}
        print("> new hardware configuration :")
        print(hw_conf)
        newline()

        # return to a standard configuration
        cnx = KBIO.HW_CNX.STANDARD
        mode = KBIO.HW_MODE.GROUNDED
        api.SetHardwareConf(id_, channel, cnx.value, mode.value)

    # BL_Disconnect
    api.Disconnect(id_)
    print(f"> disconnected from device[{address}]")
    newline()

    # BL_GetErrorMsg
    err_code = -202
    err_msg = api.GetErrorMsg(err_code)
    print(f"> error[{err_code}] description : '{err_msg}'")
    newline()

    # id_ is no longer valid, its use will trigger an exception
    print("> an exception will be raised :")
    ok = "OK" if api.TestConnection(id_) else "not OK"

except Exception as e :
    print_exception(e)

#==============================================================================#
