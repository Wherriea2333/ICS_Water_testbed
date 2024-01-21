import psm
import time
import redis

# global variables
counter = 0
var_state = False

r = redis.Redis(host='localhost', port=6379, decode_responses=True)


def hardware_init():
    # Insert your hardware initialization code in here
    psm.start()


def update_inputs():
    # place here your code to update inputs
    global counter
    global var_state
    psm.set_var("IX0.0", var_state)
    counter += 1
    r.set(counter, f'{counter}')
    if (counter == 10):
        counter = 0
        var_state = not var_state


def update_outputs():
    # place here your code to work on outputs
    a = psm.get_var("QX0.0")
    if a == True:
        print("QX0.0 is true")


if __name__ == "__main__":
    hardware_init()
    while (not psm.should_quit()):
        update_inputs()
        update_outputs()
        time.sleep(0.1)  # You can adjust the psm cycle time here
    psm.stop()