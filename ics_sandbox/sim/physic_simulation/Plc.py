import logging
import uuid
from abc import abstractmethod

import yaml
from pyModbusTCP.server import DataBank

from Sensor import StateSensor, VolumeSensor, FlowRateSensor

logging.basicConfig()
log = logging.getLogger('phy_sim')
log.setLevel(logging.WARN)

_16BITS = 65535
_ZERO = 0


class InvalidPLC(Exception):
    """Exception thrown for bad device types
    """

    def __init__(self, message):
        super(InvalidPLC, self).__init__(message)


class Base_PLC(yaml.YAMLObject):

    def __init__(self, label='', connection_established_coil=65535, state=None, controlled_sensors_label=None):
        self.precision = 10
        self.uid = str(uuid.uuid4())[:8]
        self.label = label
        self.state = state
        self.controlled_sensors_label = controlled_sensors_label
        self.data_bank = None
        self.connection_established_coil = connection_established_coil
        self.controlled_sensors = {}

        log.info(f"{self}: Initialized")

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    @abstractmethod
    def worker(self):
        pass

    def set_data_bank(self, data_bank: DataBank):
        self.data_bank = data_bank


class PLC(Base_PLC):
    yaml_tag = u'!plc'
    yaml_loader = yaml.Loader

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def check_connected(self):
        coil_state = self.data_bank.get_coils(self.connection_established_coil, 1)
        if coil_state is not None and coil_state[0]:
            return True
        else:
            return False

    def worker(self):
        # each sensor read/write for himself
        # can be improved by reading a lot one time and giving to each sensor his data
        for sensor in self.controlled_sensors.values():
            # if state -> read & write
            if type(sensor) == StateSensor:
                if "X" == sensor.location_tuple[0]:
                    if sensor.active:
                        coil_data = self.data_bank.get_coils(sensor.location_tuple[1], 1)
                        log.debug(f"coil data X{sensor.location_tuple[1]}: {coil_data}")
                        if coil_data is not None:
                            if coil_data[0]:
                                sensor.device_to_monitor.activate()
                                self.data_bank.set_coils(sensor.location_tuple[1], [True])
                            else:
                                sensor.device_to_monitor.deactivate()
                                self.data_bank.set_coils(sensor.location_tuple[1], [False])
                        else:
                            log.error(f"Error reading coil {sensor.location}")
            # if volume,flow_rate -> write only
            elif type(sensor) == VolumeSensor or type(sensor) == FlowRateSensor:
                if "W" == sensor.location_tuple[0]:
                    sensor_value = int(sensor.read_sensor() * sensor.multiplier)
                    if sensor_value > _16BITS:
                        log.error(f"{sensor.label} has a value greater than 65535, {sensor_value}")
                        sensor_value = _16BITS
                    elif sensor_value < _ZERO:
                        log.error(f"{sensor.label} has a negative value, {sensor_value}")
                        sensor_value = _ZERO
                    self.data_bank.set_holding_registers(sensor.location_tuple[1], [sensor_value])
