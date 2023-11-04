import signal
import sys

from sim.Device import *
from sim.Fluid import *
from sim.Sensor import *
from sim.utils import parse_yml, build_simulation

logging.basicConfig()
log = logging.getLogger('phy_sim')
log.setLevel(logging.WARN)


def foo():
    """Empty function to not accidentally delete import from Device,Fluid,Sensor"""
    device = Device()
    fluid = Fluid()
    sensor = Sensor()


def check_reservoir_volume(devices: {}, last_volume):
    current_volume = 0
    for device in devices.values():
        if isinstance(device, Tank):
            current_volume += device.volume
        if isinstance(device, Reservoir):
            current_volume -= device.input_per_cycle
    if current_volume != last_volume:
        log.warning(f"Input to tank not equal to output !")
    return current_volume


class Simulator(object):

    def __init__(self, debug=0, math_parser='proportional'):
        signal.signal(signal.SIGINT, self.sig_handler)

        self.path_to_yaml_config = None
        self.config = None
        self.settings = None
        self.devices = None
        self.sensors = None
        self.math_parser = math_parser
        self.max_cycle = None
        self.current_tanks_volume = 0

        if debug == 1:
            log.setLevel(logging.INFO)
        if debug >= 2:
            log.setLevel(logging.DEBUG)

    def sig_handler(self):
        print("Received SIGINT, shutting down simulation.")
        self.stop()

    def load_yml(self, path_to_yaml_config):
        """Read and parse YAML configuration file into simulator devices
        """
        self.path_to_yaml_config = path_to_yaml_config
        self.config = parse_yml(path_to_yaml_config)
        simulation = build_simulation(self.config, self.math_parser)
        self.settings = simulation['settings']
        self.devices = simulation['devices']
        self.sensors = simulation['sensors']
        # self.plcs = simulation['plcs']

        self.set_speed(self.settings['speed'])
        self.set_precision(self.settings['precision'])
        self.max_cycle = self.settings['max_cycle']
        self.set_current_tanks_volume()

    def start(self):
        """Start the simulation"""
        for device in self.devices.values():
            device.activate()

        for sensor in self.sensors.values():
            sensor.activate()
        log.info(self.devices)
        for i in range(self.max_cycle):
            for device in self.devices.values():
                device.reset_current_flow_rate()
            for device in self.devices.values():
                device.worker()
            # check all reservoir
            check_reservoir_volume(self.devices, self.current_tanks_volume)
            for sensor in self.sensors.values():
                sensor.worker()
                log.debug(f"Device: {sensor.device_to_monitor.label} sensor value: {sensor.read_sensor()}")

        # for plc in self.plcs:
        #     for sensor in self.plcs[plc]['sensors']:
        #         self.plcs[plc]['sensors'][sensor][
        #             'read_sensor'] = self.sensors[sensor].read_sensor
        #         self.plcs[plc]['sensors'][sensor][
        #             'write_sensor'] = self.sensors[sensor].write_sensor
        # self.plcservice.loadPLCs(self.plcs)
        # self.plcservice.start()

    def pause(self):
        """Pause the simulation"""
        for device in self.devices.values():
            device.deactivate()

        for sensor in self.sensors.values():
            sensor.deactivate()

    def stop(self):
        """Stop and destroy the simulation"""
        self.pause()
        sys.exit(0)

    def set_speed(self, speed):
        """Increase/Decrease the speed of the simulation
            default: 1/second
        """
        for device in self.devices.values():
            device.speed = speed

        for sensor in self.sensors.values():
            sensor.speed = speed

    def restart(self):
        """Stop and reload the simulation from the original config"""
        self.pause()
        self.load_yml(self.path_to_yaml_config)
        self.start()

    def set_precision(self, precision):
        """set the number of output digits of sensors and devices"""
        for device in self.devices.values():
            device.precision = precision

        for sensor in self.sensors.values():
            sensor.precision = precision

    def set_current_tanks_volume(self):
        """get the initial volume of fluid in tanks"""
        for device in self.devices.values():
            if isinstance(device, Tank):
                self.current_tanks_volume += device.volume
