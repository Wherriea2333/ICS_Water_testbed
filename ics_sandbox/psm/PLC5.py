#                  - OpenPLC Python SubModule (PSM) -
#
# PSM is the bridge connecting OpenPLC core to Python programs. PSM allows
# you to directly interface OpenPLC IO using Python and even write drivers
# for expansion boards using just regular Python.
#
# PSM API is quite simple and just has a few functions. When writing your
# own programs, avoid touching on the "__main__" function as this regulates
# how PSM works on the PLC cycle. You can write your own hardware initialization
# code on hardware_init(), and your IO handling code on update_inputs() and
# update_outputs()
#
# To manipulate IOs, just use PSM calls psm.get_var([location name]) to read
# an OpenPLC location and psm.set_var([location name], [value]) to write to
# an OpenPLC location. For example:
#     psm.get_var("QX0.0")
# will read the value of %QX0.0. Also:
#     psm.set_var("IX0.0", True)
# will set %IX0.0 to true.
#
# Below you will find a simple example that uses PSM to switch OpenPLC's
# first digital input (%IX0.0) every second. Also, if the first digital
# output (%QX0.0) is true, PSM will display "QX0.0 is true" on OpenPLC's
# dashboard. Feel free to reuse this skeleton to write whatever you want.

import time

# import all your libraries here
import psm
from pymodbus.client.sync import ModbusTcpClient

# global variables
MV501 = "IX1.2"
MV503 = "IX1.3"
P501 = "IX1.4"
P502 = "IX1.5"

FIT501 = "IW6"
FIT502 = "IW7"
FIT503 = "IW8"
client = None


def hardware_init():
    # Insert your hardware initialization code in here
    global client
    client = ModbusTcpClient('172.18.0.1', 12345)
    print(f"connected to simulation: {client.connect()}")
    # tell the simulation PLC connected
    client.write_coil(65005, True)
    psm.start()
    # set sim, plc state
    client.write_coil(10, True)
    psm.set_var(MV501, True)
    client.write_coil(11, False)
    psm.set_var(MV503, False)
    client.write_coil(12, False)
    psm.set_var(P501, False)
    client.write_coil(13, False)
    psm.set_var(P502, False)


def update_inputs():
    global client
    fit501 = client.read_holding_registers(6, 1).registers[0]
    psm.set_var(FIT501, fit501)
    print(f"Water through Filter-501:  {fit501}")
    fit502 = client.read_holding_registers(7, 1).registers[0]
    psm.set_var(FIT502, fit502)
    print(f"Water through MV-501:  {fit502}")

    client.write_coil(10, True)
    psm.set_var(P501, True)
    client.write_coil(12, True)
    psm.set_var(P502, True)
    client.write_coil(13, True)
    psm.set_var(MV501, True)
    # DO NOT TOUCH MV503 -> if open, make in infinite loop with pump
    pass


def update_outputs():
    pass


if __name__ == "__main__":
    hardware_init()
    while (not psm.should_quit()):
        update_inputs()
        update_outputs()
        time.sleep(0.5)  # You can adjust the psm cycle time here
    psm.stop()
