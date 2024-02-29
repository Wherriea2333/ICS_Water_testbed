import signal
import sys
import time

from pyModbusTCP.server import ModbusServer

from Device import *
from Fluid import *
from Plc import *
from Sensor import *
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
        """Start the simulation"""
        # TODO: being adaptable (logger)

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

        my_data_bank = DataBank()
        server = ModbusServer(self.settings['host_address'], self.settings['port'], data_bank=my_data_bank,
                              no_block=True)

        for plc in self.plcs.values():
            plc.set_data_bank(my_data_bank)
        # TODO: set init state of the physic simulation
        log.debug(self.devices)

        try:
            print("Start Modbus TCP server...")
            server.start()
            print("Server is online")
            print("Wait 10s to let plc's to connect to the server")
            time.sleep(10)

            if self.max_cycle == 0:
                while True:
                    self.main_loop()
            else:
                for i in range(self.max_cycle):
                    self.main_loop()
                server.stop()
        except:
            print("Shutdown server ...")
            server.stop()
            print("Server is offline")

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
        """set the number of output digits of devices, sensors, plc"""
        for device in self.devices.values():
            device.precision = precision

        for sensor in self.sensors.values():
            sensor.precision = precision

        for plc in self.plcs.values():
            plc.precision = precision

    def set_current_tanks_volume(self):
        """get the initial volume of fluid in tanks"""
        for device in self.devices.values():
            if isinstance(device, Tank):
                self.current_tanks_volume += device.volume

    def main_loop(self):
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

        for plc in self.plcs.values():
            plc.worker()
        time.sleep(int(self.settings['speed']) / 1000)

    def generate_st_files(self):
        for plc in self.plcs.values():
            to_be_written = []
            with open(f"{plc.label}.st", "w") as f:
                to_be_written.append(f"PROGRAM {plc.label}\n")
                to_be_written.append(f"  VAR\n")
                coil_variable_code = []
                for sensor in plc.controlled_sensors.values():
                    location = ""
                    data_type = None
                    if sensor.location_tuple[0] == "X":
                        data_type = "BOOL"
                        coil_variable_code.append(f"  {sensor.label} := {sensor.label};\n")
                        location = "IX" + str(sensor.location_tuple[1] // 8) + "." + str(sensor.location_tuple[1] % 8)
                    elif sensor.location_tuple[0] == "W":
                        data_type = "INT"
                        location = "IW" + str(sensor.location_tuple[1])
                    to_be_written.append(f"    {sensor.label} AT %{location} : {data_type};\n")
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
