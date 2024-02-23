import logging
import uuid
from abc import abstractmethod

import yaml
from pymodbus.client import ModbusTcpClient

from Sensor import StateSensor, VolumeSensor, FlowRateSensor

log = logging.getLogger('plc')

_16BITS = 65535


class InvalidPLC(Exception):
    """Exception thrown for bad device types
    """

    def __init__(self, message):
        super(InvalidPLC, self).__init__(message)


class Base_PLC(yaml.YAMLObject):

    def __init__(self, label='', state=None, host=None, port=502, controlled_sensors_label=None):
        if host is None:
            raise InvalidPLC(f"PLC {label} doesn't have host")
        self.precision = 10
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
        rr = self.client.read_coils(location, count + 1)
        return rr.bits[count]

    def read_single_register(self, location, count):
        rr = self.client.read_holding_registers(location, count + 1)
        return rr.registers[count]

    def write_single_bit_to_coil(self, location, value):
        return self.client.write_coil(location, value)

    def write_single_register(self, location, value):
        return self.client.write_register(location, value)

    @abstractmethod
    def worker(self):
        pass


class PLC(Base_PLC):
    yaml_tag = u'!plc'
    yaml_loader = yaml.Loader

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
                        self.write_single_bit_to_coil(sensor.location_tuple[1] * 8 + sensor.location_tuple[2], state)
            # if volume,flowrate -> write only
            elif type(sensor) == VolumeSensor or type(sensor) == FlowRateSensor:
                if "QW" == sensor.location_tuple[0]:
                    sensor_value = int(sensor.read_sensor())
                    if sensor.read_sensor() > _16BITS:
                        log.error(f"{sensor.label} has a value greater than 65535, {sensor.read_sensor()}")
                        sensor_value = _16BITS
                    self.write_single_register(sensor.location_tuple[1], sensor_value)
                elif "MD" == sensor.location_tuple[0]:
                    sensor_value = int(sensor.read_sensor() * sensor.multiplier)
                    if sensor.read_sensor() > _16BITS:
                        log.error(f"{sensor.label} has a value greater than 65535, {sensor.read_sensor()}")
                        sensor_value = _16BITS
                    # write it to MW, as an 16 bits int -> psm code should transform it from int to real(float)
                    self.write_single_register(1024 + sensor.location_tuple[1], sensor_value)
