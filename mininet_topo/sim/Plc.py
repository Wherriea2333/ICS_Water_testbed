import logging
import uuid

import yaml
from pymodbus.client import ModbusTcpClient

from mininet_topo.sim.Sensor import *

log = logging.getLogger('plc')


class InvalidPLC(Exception):
    """Exception thrown for bad device types
    """

    def __init__(self, message):
        super(InvalidPLC, self).__init__(message)


class PLC(yaml.YAMLObject):
    yaml_tag = u'!plc'
    yaml_loader = yaml.CLoader

    def __init__(self, label='', state=None, host=None, port=502, controlled_sensors_label=None):
        if host is None:
            raise InvalidPLC(f"PLC {label} doesn't have host")

        self.uid = str(uuid.uuid4())[:8]
        self.label = label
        self.state = state
        self.client = ModbusTcpClient(host, port)
        self.controlled_sensors_label = controlled_sensors_label
        self.controlled_sensors = {}

        log.info(f"{self}: Initialized")

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def connect_plc(self):
        self.state = self.client.connect()
        log.info(f"PLC {self.label}: Connected")

    def disconnect_plc(self):
        self.client.close()
        self.state = False
        log.info(f"PLC {self.label}: Disconnected")

    def read_single_bit_from_coil(self, location, count):
        rr = self.client.read_coils(location, count)
        return rr.bits[count - 1]

    def read_single_register(self, location, count):
        rr = self.client.read_holding_registers(location, count)
        return rr.registers[count - 1]

    def write_single_bit_from_coil(self, location, value):
        return self.client.write_coil(location, value)

    def write_single_register(self, location, value):
        return self.client.write_register(location, value)

    def worker(self):
        # each sensor read/write for himself
        # can be improved by reading a lot one time and giving to each sensor his data
        for sensor in self.controlled_sensors.values():
            # if state -> read & write
            if type(sensor) == StateSensor:
                if "QX" == sensor.location_tuple[0]:
                    state = self.read_single_bit_from_coil(sensor.location_tuple[1], sensor.location_tuple[2])
                    if state != sensor.device_to_monitor.active:
                        if state:
                            sensor.device_to_monitor.activate()
                        else:
                            sensor.device_to_monitor.deactivate()
                        self.write_single_bit_from_coil(sensor.location_tuple[1] * 8 + sensor.location_tuple[2], state)
            # if volume,flowrate -> write only
            if type(sensor) == VolumeSensor or type(sensor) == FlowRateSensor:
                # if "QX" == sensor.location_tuple[0]:
                #     state = self.read_single_bit_from_coil(sensor.location_tuple[1], sensor.location_tuple[2])
                if "QW" == sensor.location_tuple[0]:
                    self.write_single_register(sensor.location_tuple[1], sensor.device_to_monitor.read_sensor())
                elif "MD" == sensor.location_tuple[0]:
                    self.write_single_register(1024 + sensor.location_tuple[1], sensor.device_to_monitor.read_sensor())
