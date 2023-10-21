import signal
import sys

from sim.Device import *
from sim.Fluid import *
from sim.Sensor import *
from sim.utils import parse_yml, build_simulation

from time import sleep

logging.basicConfig()
log = logging.getLogger('phy_sim')
log.setLevel(logging.WARN)


def foo():
    """Empty function to not accidentally delete import from Device,Fluid,Sensor"""
    device = Device()
    fluid = Fluid()
    sensor = Sensor()


class Simulator(object):

    def __init__(self, debug=0):
        signal.signal(signal.SIGINT, self.sig_handler)

        self.path_to_yaml_config = None
        self.config = None
        self.settings = None
        self.devices = None
        self.sensors = None

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
        simulation = build_simulation(self.config)
        self.settings = simulation['settings']
        self.devices = simulation['devices']
        self.sensors = simulation['sensors']
        # self.plcs = simulation['plcs']

        self.set_speed(self.settings['speed'])

    def start(self):
        """Start the simulation"""
        for device in self.devices.values():
            device.activate()

        for sensor in self.sensors.values():
            sensor.activate()
        log.info(self.devices)
        for i in range(10):
            for device in self.devices.values():
                device.worker()
            for sensor in self.sensors.values():
                sensor.worker()
                log.info(sensor.read_sensor())

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

        # self.plcservice.stop_server()
        # self.plcservice.join()

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
        self.load_yml(self.path_to_yaml_config, )
        self.start()
