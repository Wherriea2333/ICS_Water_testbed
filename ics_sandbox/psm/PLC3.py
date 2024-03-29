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
containerMax = 10000


def hardware_init():
    # Insert your hardware initialization code in here
    global client
    client = ModbusTcpClient('172.18.0.10', 12345)
    print(f"connected to simulation: {client.connect()}")
    # tell the simulation PLC connected
    client.write_coil(65003, True)
    psm.start()
    # set sim, plc state
    client.write_coil(5, False)
    psm.set_var(P301, False)
    client.write_coil(6, False)
    psm.set_var(P302, False)
    client.write_coil(7, False)
    psm.set_var(MV302, False)


def update_inputs():
    global client
    lit301 = client.read_holding_registers(2, 1).registers[0]
    psm.set_var(LIT301, lit301)
    fit301 = client.read_holding_registers(3, 1).registers[0]
    psm.set_var(FIT301, fit301)
    print(f"lit301:  {lit301}")
    if 0.3 * containerMax <= lit301 <= 0.8 * containerMax:
        print(f"LIT301 {lit301} normal: Open P301, P302, MV302")
        client.write_coil(5, True)
        psm.set_var(P301, True)
        client.write_coil(6, True)
        psm.set_var(P302, True)
        client.write_coil(7, True)
        psm.set_var(MV302, True)
    # min 20 %
    elif lit301 < 0.3 * containerMax:
        print(f"LI3101 {lit301} TOO LOW : Close P301, P302, MV302")
        client.write_coil(5, False)
        psm.set_var(P301, False)
        client.write_coil(6, False)
        psm.set_var(P302, False)
        client.write_coil(7, False)
        psm.set_var(MV302, False)
    # max 80 %
    elif lit301 > 0.8 * containerMax:
        # TODO: define what to do when too much water
        # write to P101,P102,MV201 to be off ?
        print(f"LIT301 {lit301} TOO HIGH : BIG WARNING")
        # client.write_coil(7, False)
        # psm.set_var(MV302, False)
    pass


def update_outputs():
    # place here your code to work on outputs
    pass


if __name__ == "__main__":
    hardware_init()
    while not psm.should_quit():
        update_inputs()
        update_outputs()
        time.sleep(0.2)  # You can adjust the psm cycle time here
    psm.stop()
