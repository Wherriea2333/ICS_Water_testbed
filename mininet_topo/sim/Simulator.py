import signal
import sys
import time

from Device import *
from Fluid import *
from Sensor import *
from Plc import *
from utils import parse_yml, build_simulation

logging.basicConfig()
log = logging.getLogger('phy_sim')
log.setLevel(logging.WARN)


def foo():
    """Empty function to not accidentally delete import from Device,Fluid,Sensor"""
    device = Device()
    fluid = Fluid()
    sensor = Sensor(None, None)
    plc = PLC()


def check_reservoir_volume(devices: {}, last_volume: float, precision: int):
    current_volume = 0
    for device in devices.values():
        if isinstance(device, Tank):
            current_volume += device.volume
        if isinstance(device, Reservoir):
            last_volume += device.input_per_cycle
    if current_volume - last_volume > 1 ** - precision:
        log.debug(f"Current volume: {current_volume}")
        log.debug(f"Last volume: {last_volume}")
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
        self.plcs = None
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
        self.plcs = simulation['plcs']

        self.set_precision(self.settings['precision'])
        self.max_cycle = self.settings['max_cycle']
        self.set_current_tanks_volume()

    def start(self):
        # adjust redis host to the right address
        """
        r = redis.Redis(host="192.168.1.10", port=6379, password="testpassword",
                        decode_responses=True, socket_timeout=10, retry_on_timeout=True)
        try:
            r.ping()
            log.info("Connected to redis server")
        except redis.ConnectionError:
            log.error("Cannot connect to redis server")
        """

        """Start the simulation"""
        # TODO: being adaptable

        log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        root_logger = logging.getLogger()
        file_handler = logging.FileHandler("simulator.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(log_formatter)
        root_logger.addHandler(console_handler)

        for device in self.devices.values():
            device.activate()

        for sensor in self.sensors.values():
            sensor.activate()

        for plc in self.plcs.values():
            plc.connect_plc()

        log.debug(self.devices)
        log.debug("Wait 5 seconds to be sure the connection is established")
        time.sleep(5)

        for i in range(self.max_cycle):
            for device in self.devices.values():
                device.reset_current_flow_rate()
            for device in self.devices.values():
                device.worker()
            # check all reservoir
            self.current_tanks_volume = check_reservoir_volume(self.devices, self.current_tanks_volume,
                                                               self.settings['precision'])
            for sensor in self.sensors.values():
                sensor.worker()
                log.debug(f"Device: {sensor.device_to_monitor.label} sensor value: {sensor.read_sensor()}")
                # r.set(sensor.device_to_monitor.label, sensor.read_sensor())
            # read data from the redis server for each PLC
            # apply it to make the change according to the value read from redis
            for plc in self.plcs.values():
                plc.worker()
            time.sleep(int(self.settings['speed'])/1000)

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

    def generate_st_files(self):
        for plc in self.plcs.values():
            to_be_written = []
            with open(f"{plc.label}.st", "w") as f:
                to_be_written.append(f"PROGRAM {plc.label}\n")
                to_be_written.append(f"  VAR\n")
                coil_variable_code = []
                for sensor in plc.controlled_sensors.values():
                    data_type = None
                    if sensor.location_tuple[0] == "QX":
                        data_type = "BOOL"
                        coil_variable_code.append(f"  {sensor.label} := {sensor.label};\n")
                    elif sensor.location_tuple[0] == "QW":
                        data_type = "INT"
                    elif sensor.location_tuple[0] == "MD":
                        data_type = "REAL"
                    to_be_written.append(f"    {sensor.label} AT {sensor.location} : %{data_type};\n")
                to_be_written.append(f"  END_VAR\n\n")
                to_be_written.extend(coil_variable_code)
                to_be_written.append("END_PROGRAM\n\n\n")
                to_be_written.append("CONFIGURATION Config0\n\n")
                to_be_written.append("  RESOURCE Res0 ON PLC\n")
                to_be_written.append(f"    TASK task0(INTERVAL := T#{self.settings['speed']}ms,PRIORITY := 0);\n")
                to_be_written.append(f"    PROGRAM instance0 WITH task0 : {plc.label};\n")
                to_be_written.append("  END_RESOURCE\n")
                to_be_written.append("END_CONFIGURATION\n")
                f.writelines(to_be_written)
