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
P401 = "IX1.0"  # -> coil 8
P402 = "IX1.1"  # -> coil 9
LIT401 = "IW4"
containerMax = 10000
FIT401 = "IW5"
client = None


def hardware_init():
    # Insert your hardware initialization code in here
    global client
    client = ModbusTcpClient('172.18.0.1', 12345)
    print(f"connected to simulation: {client.connect()}")
    # tell the simulation PLC connected
    client.write_coil(65004, True)
    psm.start()
    # set sim, plc state
    client.write_coil(9, False)
    psm.set_var(P401, False)
    client.write_coil(8, False)
    psm.set_var(P402, False)


def update_inputs():
    # place here your code to update inputs
    global client
    lit401 = client.read_holding_registers(4, 1).registers[0]
    psm.set_var(LIT401, lit401)
    fit401 = client.read_holding_registers(5, 1).registers[0]
    psm.set_var(FIT401, fit401)
    print(f"FIT401:  {fit401}")
    if lit401 >= 0.5 * containerMax:
        print(f"LIT401 {lit401} High enough : Open P401, P402")
        print(f"turn on: P401.P402 -> {lit401}")
        client.write_coil(8, True)
        psm.set_var(P401, True)
        client.write_coil(9, True)
        psm.set_var(P402, True)
    # min 20 %
    elif lit401 <= 0.2 * containerMax:
        print(f"LIT401 {lit401} TOO LOW : Close P401, P402")
        client.write_coil(8, False)
        psm.set_var(P401, False)
        client.write_coil(9, False)
        psm.set_var(P402, False)
    else:
        print(f"LIT401: {lit401}")
    pass


def update_outputs():
    pass


if __name__ == "__main__":
    hardware_init()
    while (not psm.should_quit()):
        update_inputs()
        update_outputs()
        time.sleep(0.2)  # You can adjust the psm cycle time here
    psm.stop()
