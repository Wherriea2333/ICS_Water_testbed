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
P601 = "IX1.6"
P603 = "IX1.7"
T601ContainerMax = 1000
T603ContainerMax = 1000
LS601 = "IW9"
LS603 = "IW10"
client = None


def hardware_init():
    # Insert your hardware initialization code in here
    global client
    client = ModbusTcpClient('172.18.0.1', 12345)
    print(client.connect())
    print("connected")
    psm.start()
    client.write_coil(14, False)
    client.write_coil(15, False)
    psm.set_var(P601, False)
    psm.set_var(P603, False)


def update_inputs():
    # place here your code to update inputs
    pass


def update_outputs():
    # place here your code to work on outputs
    global client
    ls601 = client.read_holding_registers(9, 1).registers[0]
    psm.set_var(LS601, ls601)
    print(f"ls601:  {ls601}")
    ls603 = client.read_holding_registers(10, 1).registers[0]
    psm.set_var(LS603, ls603)
    print(f"ls603:  {ls603}")
    # min 20 %
    if ls601 <= 0.2 * T601ContainerMax:
        print(f"turn off: P601 -> {ls601}")
        client.write_coil(14, False)
        psm.set_var(P601, False)
    # max 80 %
    elif ls601 >= 0.8 * ls601:
        print(f"turn on: P601 -> {ls601}")
        client.write_coil(14, True)
        psm.set_var(P601, True)

    # min 20 %
    if ls603 <= 0.2 * T603ContainerMax:
        print(f"turn off: P601 -> {ls603}")
        client.write_coil(15, False)
        psm.set_var(P601, False)
    # max 80 %
    elif ls603 >= 0.8 * ls603:
        print(f"turn on: P603 -> {ls603}")
        client.write_coil(15, True)
        psm.set_var(P601, True)


if __name__ == "__main__":
    hardware_init()
    while (not psm.should_quit()):
        update_inputs()
        update_outputs()
        time.sleep(0.5)  # You can adjust the psm cycle time here
    psm.stop()
