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

# import all your libraries here
import psm
import time
from pymodbus.client.sync import ModbusTcpClient

# global variables
client = None
P301 = "IX0.5"
P302 = "IX0.6"
MV302 = "IX0.7"
LIT301 = "IW2"
FIT301 = "IW3"
containerMax = 1000


def hardware_init():
    # Insert your hardware initialization code in here
    global client
    client = ModbusTcpClient('127.0.0.1', 12345)
    print(client.connect())
    print("connected")
    psm.start()
    client.write_coil(5, False)
    client.write_coil(6, False)
    client.write_coil(7, False)
    psm.set_var(P301, False)
    psm.set_var(P302, False)
    psm.set_var(MV302, False)


def update_inputs():
    # place here your code to update inputs
    pass


def update_outputs():
    # place here your code to work on outputs
    global client
    lit301 = client.read_holding_registers(2, 1).registers[0]
    psm.set_var(LIT301, lit301)
    print(f"lit101:  {lit301}")
    if 500 <= lit301 <= 800:
        print(f"turn on: fit -> {lit301}")
        client.write_coil(5, True)
        client.write_coil(6, True)
        psm.set_var(P301, True)
        psm.set_var(P302, True)
    # min 20 %
    if lit301 <= 0.2 * containerMax:
        print('LIT 101 <= 0.2 * ContainerMax')
        client.write_coil(5, False)
        client.write_coil(6, False)
        psm.set_var(P301, False)
        psm.set_var(P302, False)
    # max 80 %
    if lit301 >= 0.8 * containerMax:
        print('LIT 101 >= 0.8 * ContainerMax')
        client.write_coil(7, False)
        psm.set_var(MV302, False)
    pass


if __name__ == "__main__":
    hardware_init()
    while (not psm.should_quit()):
        update_inputs()
        update_outputs()
        time.sleep(0.5)  # You can adjust the psm cycle time here
    psm.stop()
