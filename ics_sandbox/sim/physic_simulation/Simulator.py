import csv
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
    """Check that the volume of fluid in the system correspond to
    the last cycle + the amount of fluid added in the current cycle to the system"""
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
    """Main class which control all the simulation"""

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

    """
    constructor
    :param debug: 0: level warning, 1: level info, 2:level debug
    :param math_parser: 'proportional', 'sympy' or 'wolfram'
    """

    def sig_handler(self) -> None:
        # TODO: implement proper signal handling
        print("Received SIGINT, shutting down simulation.")
        self.stop()

    def load_yml(self, path_to_yaml_config: str) -> None:
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

    def start(self) -> None:
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

            csv_field_names = ['timestamp_ns']
            for sensor in self.sensors.values():
                csv_field_names.append(sensor.label)

            with open('simulation_log.csv', 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_field_names)
                writer.writeheader()

                # wait all PLCs are connected
                self.wait_PLCs_connection()
                if self.max_cycle == 0:
                    while True:
                        self.main_loop(writer, csv_field_names)
                else:
                    for i in range(self.max_cycle):
                        self.main_loop(writer, csv_field_names)
            server.stop()
        except Exception as error:
            # TODO: implement proper signal handling
            log.info("Shutdown server ...")
            server.stop()
            log.info("Server is offline")
            traceback.print_exc()
        finally:
            log.info("Shutdown server ...")
            server.stop()
            log.info("Server is offline")

    def wait_PLCs_connection(self):
        """Wait until all PLCs are connected before starting the simulation"""
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

    def set_inner_state(self, my_data_bank: DataBank) -> None:
        """Set initial state of the modbus data bank with initial state given by the yaml config file"""
        for device in self.devices.values():
            if device.read_state():
                device.activate()
        for sensor in self.sensors.values():
            if sensor.read_state():
                sensor.activate()
        for plc in self.plcs.values():
            plc.set_data_bank(my_data_bank)

    def set_initial_state(self) -> None:
        """Set initial state of sensors and PLCs"""
        for sensor in self.sensors.values():
            if sensor.active:
                sensor.worker()
        for plc in self.plcs.values():
            plc.worker()

    def pause(self) -> None:
        # TODO: handle sigint to pause the simulation
        """Pause the simulation"""

        for device in self.devices.values():
            device.deactivate()

        for sensor in self.sensors.values():
            sensor.deactivate()

    def stop(self) -> None:
        # TODO: handle sigint to stop the simulation
        """Stop and destroy the simulation"""
        self.pause()
        sys.exit(0)

    def restart(self) -> None:
        # TODO: handle sigint to restart the simulation
        """Stop and reload the simulation from the original config"""
        self.pause()
        self.load_yml(self.path_to_yaml_config)
        self.start()

    def set_precision(self, precision: int) -> None:
        """
        Set the number of output digits of devices, sensors, plc
        :param precision: the number of digits to output
        """
        for device in self.devices.values():
            device.precision = precision

        for sensor in self.sensors.values():
            sensor.precision = precision

        for plc in self.plcs.values():
            plc.precision = precision

    def set_current_tanks_volume(self) -> None:
        """Set the initial volume of fluid in tanks"""
        for device in self.devices.values():
            if isinstance(device, Tank):
                self.current_tanks_volume += device.volume

    def main_loop(self, writer: csv.DictWriter, csv_field_names: list[str]) -> None:
        """Main loop of the simulation, reset flow rate to 0, make all active device worker work,
        check simulation volume is correct, sensors update read data,PLC get data from sensors and put them in data bank
         and also update sensor state(which will in their turn update device state)"""
        for device in self.devices.values():
            device.reset_current_flow_rate()
        for device in self.devices.values():
            if device.active:
                device.worker()

        # check all reservoir
        self.current_tanks_volume = check_reservoir_volume(self.devices, self.current_tanks_volume,
                                                           self.settings['precision'])
        to_write_to_csv = {'timestamp_ns': time.time_ns()}
        for sensor in self.sensors.values():
            sensor.worker()
            if sensor.label in csv_field_names:
                to_write_to_csv[sensor.label] = sensor.read_sensor()

        for plc in self.plcs.values():
            plc.worker()

        writer.writerow(to_write_to_csv)
        # improvement? -> measure time consumed for previous task
        # then to sleep = sim_speed/1000 - time_consumed (in ms)
        time.sleep(int(self.settings['sim_speed']) / 1000)

    def generate_st_files(self) -> None:
        """Function to generate basic ladder logic which just move input to output,
        only support Boolean and Word (IX/QX,IW/QW)"""
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
