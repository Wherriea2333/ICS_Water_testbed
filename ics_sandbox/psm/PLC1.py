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
P101 = "IX0.0"
P102 = "IX0.1"
# MV101 = "IX0.2"
# FIT101 = "MD0"
FIT201 = "IW0"
containerMax = 10000
LIT101 = "IW1"


def hardware_init():
    global client
    client = ModbusTcpClient('172.18.0.10', 12345)
    print(f"connected to simulation: {client.connect()}")
    # tell the simulation PLC connected
    client.write_coil(65001, True)
    psm.start()
    # set sim, plc state
    client.write_coil(0, False)
    psm.set_var(P101, False)

    client.write_coil(1, False)
    psm.set_var(P102, False)


def update_inputs():
    global client
    lit101 = client.read_holding_registers(1, 1).registers[0]
    psm.set_var(LIT101, lit101)
    print(f"lit101:  {lit101}")

    if 0.3 * containerMax <= lit101 <= 0.8 * containerMax:
        print(f"LIT101 {lit101} normal: Open P101,P102")
        client.write_coil(0, True)
        psm.set_var(P101, True)
        client.write_coil(1, True)
        psm.set_var(P102, True)
    elif lit101 < 0.3 * containerMax:
        print(f"LIT101 {lit101} TOO LOW : Close P101,P102")
        client.write_coil(0, False)
        client.write_coil(1, False)
        psm.set_var(P101, False)
        psm.set_var(P102, False)
    # max 80 %
    elif lit101 > 0.8 * containerMax:
        # TODO: control reservoir input per cycle
        print(f"LIT101 {lit101} TOO HIGH : Close MV101")
        # client.write_coil(2, False)
        # psm.set_var(MV101, False)

    # set flowrate
    fit201 = client.read_holding_registers(0, 1).registers[0]
    psm.set_var(FIT201, fit201)
    print(f"fit201:  {lit101}")
    pass


def update_outputs():
    pass


if __name__ == "__main__":
    hardware_init()
    while not psm.should_quit():
        update_inputs()
        update_outputs()
        time.sleep(0.2)  # You can adjust the psm cycle time here
    psm.stop()
