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
P601 = "QX0.0"
P603 = "QX0.1"
# TODO : add it to ladder
T601ContainerMax = 1000
T603ContainerMax = 1000
LS601 = "QW0"
LS603 = "QW1"

def hardware_init():
    # Insert your hardware initialization code in here
    psm.start()
    psm.set_var(P601, False)
    psm.set_var(P603, False)


def update_inputs():
    # place here your code to update inputs

    # if psm.get_var(FIT201) == 0:
    #     psm.set_var(P101, False)
    #     psm.set_var(P102, False)

    # T601
    # min 20 %
    if psm.get_var(LS601) <= 0.2 * T601ContainerMax:
        psm.set_var(P601, False)
    # max 80 %
    if psm.get_var(LS601) >= 0.8 * T601ContainerMax:
        psm.set_var(P601, True)

    # T603
    if psm.get_var(LS603) <= 0.2 * T603ContainerMax:
        psm.set_var(P603, False)
    if psm.get_var(LS603) >= 0.8 * T603ContainerMax:
        psm.set_var(P603, True)

def update_outputs():
    # place here your code to work on outputs
    print(f" P601 is at {psm.get_var(P601)}")
    print(f" P603 is at {psm.get_var(P603)}")
    print(f" T601 ContainerCurrentVolume is {psm.get_var(T601ContainerMax)}")
    print(f" T603 ContainerCurrentVolume is {psm.get_var(T603ContainerMax)}")


if __name__ == "__main__":
    hardware_init()
    while (not psm.should_quit()):
        update_inputs()
        update_outputs()
        time.sleep(0.1)  # You can adjust the psm cycle time here
    psm.stop()