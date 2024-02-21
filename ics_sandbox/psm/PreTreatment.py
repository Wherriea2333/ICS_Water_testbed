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

# global variables
P201 = "QX0.0"
P202 = "QX0.1"
P203 = "QX0.2"
P204 = "QX0.3"
P205 = "QX0.4"
P206 = "QX0.5"

MV201 = "QX0.6"
LS201 = "QW0"
LS202 = "QW1"


def hardware_init():
    # Insert your hardware initialization code in here
    psm.start()
    psm.set_var(P201, False)
    psm.set_var(P202, False)
    psm.set_var(P203, False)
    psm.set_var(P204, False)
    psm.set_var(P205, False)
    psm.set_var(P206, False)
    psm.set_var(MV201, True)


def update_inputs():
    # place here your code to update inputs
    pass


def update_outputs():
    # place here your code to work on outputs
    pass


if __name__ == "__main__":
    hardware_init()
    while (not psm.should_quit()):
        update_inputs()
        update_outputs()
        time.sleep(0.1)  # You can adjust the psm cycle time here
    psm.stop()
