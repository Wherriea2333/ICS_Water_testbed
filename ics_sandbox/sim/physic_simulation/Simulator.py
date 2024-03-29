import signal
import sys
import time
import traceback

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


def set_logging():
    # TODO: being adaptable (logger)
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()
    file_handler = logging.FileHandler("simulator.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)


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
        self.devices: dict[str, Device] = simulation['devices']
        self.sensors: dict[str, Sensor] = simulation['sensors']
        self.plcs: dict[str, PLC] = simulation['plcs']

        self.set_precision(self.settings['precision'])
        self.max_cycle = self.settings['max_cycle']
        self.set_current_tanks_volume()

    def start(self):
        # adjust redis host to the right address
        """Start the simulation"""
        set_logging()

        # Create data bank and modbus server
        my_data_bank = DataBank()
        server = ModbusServer(self.settings['host_address'], self.settings['port'], data_bank=my_data_bank,
                              no_block=True)

        self.set_inner_state(my_data_bank)
        self.set_initial_state()

        try:
            log.info("Start Modbus TCP server...")
            server.start()
            log.info("Server is online")

            # wait all PLCs are connected
            self.wait_PLCs_connection()
            if self.max_cycle == 0:
                while True:
                    self.main_loop()
            else:
                for i in range(self.max_cycle):
                    self.main_loop()
            server.stop()
        except Exception as error:
            # TODO: implement proper signal handling
            log.info("Shutdown server ...")
            server.stop()
            log.info("Server is offline")
            traceback.print_exc()

    def wait_PLCs_connection(self):
        for i in range(1200):
            count = 0
            for plc in self.plcs.values():
                if plc.check_connected():
                    count += 1
                else:
                    log.info(f"PLC {plc.label} not connected")
            if count == len(self.plcs):
                log.info(f"All PLCs are connected")
                break
            else:
                log.info(f"Waiting 3 s")
                time.sleep(3)

    def set_inner_state(self, my_data_bank):
        for device in self.devices.values():
            # TODO: MAY NEED TO BE DEBUG (state not set correctly)
            if device.read_state():
                device.activate()
        for sensor in self.sensors.values():
            if sensor.read_state():
                sensor.activate()
        for plc in self.plcs.values():
            plc.set_data_bank(my_data_bank)

    def set_initial_state(self):
        for sensor in self.sensors.values():
            if sensor.active:
                sensor.worker()
        for plc in self.plcs.values():
            plc.worker()

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
            if device.active:
                device.worker()
        # check all reservoir
        self.current_tanks_volume = check_reservoir_volume(self.devices, self.current_tanks_volume,
                                                           self.settings['precision'])
        for sensor in self.sensors.values():
            sensor.worker()

        for plc in self.plcs.values():
            plc.worker()
        time.sleep(int(self.settings['sim_speed']) / 1000)

    def generate_st_files(self):
        for plc in self.plcs.values():
            to_be_written = []
            with open(f"{plc.label}.st", "w") as f:
                to_be_written.append(f"PROGRAM {plc.label}\n")
                to_be_written.append(f"  VAR\n")
                in_to_out = []
                # set PLC's variables
                for sensor in plc.controlled_sensors.values():
                    if sensor.location_tuple[0] == "X":
                        data_type = "BOOL"
                        input_location = "IX" + str(sensor.location_tuple[1] // 8) + "." + str(
                            sensor.location_tuple[1] % 8)
                        output_location = "QX" + str(sensor.location_tuple[1] // 8) + "." + str(
                            sensor.location_tuple[1] % 8)
                        in_to_out.append(f"  {sensor.label}_Q := {sensor.label}_I;\n")
                        to_be_written.append(f"    {sensor.label}_Q AT %{output_location} : {data_type};\n")
                        to_be_written.append(f"    {sensor.label}_I AT %{input_location} : {data_type};\n")
                    elif sensor.location_tuple[0] == "W":
                        data_type = "INT"
                        input_location = "IW" + str(sensor.location_tuple[1])
                        output_location = "QW" + str(sensor.location_tuple[1])
                        in_to_out.append(f"  {sensor.label}_Q := {sensor.label}_I;\n")
                        to_be_written.append(f"    {sensor.label}_Q AT %{output_location} : {data_type};\n")
                        to_be_written.append(f"    {sensor.label}_I AT %{input_location} : {data_type};\n")

                to_be_written.append(f"  END_VAR\n\n")
                # Ladder code to move input to output
                to_be_written.extend(in_to_out)

                to_be_written.append("END_PROGRAM\n\n\n")
                to_be_written.append("CONFIGURATION Config0\n\n")
                to_be_written.append("  RESOURCE Res0 ON PLC\n")
                to_be_written.append(f"    TASK task0(INTERVAL := T#{self.settings['plc_speed']}ms,PRIORITY := 0);\n")
                to_be_written.append(f"    PROGRAM instance0 WITH task0 : {plc.label};\n")
                to_be_written.append("  END_RESOURCE\n")
                to_be_written.append("END_CONFIGURATION\n")
                f.writelines(to_be_written)
