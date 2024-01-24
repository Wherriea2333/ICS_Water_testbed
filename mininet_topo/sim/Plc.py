import logging
import uuid

import yaml
from pymodbus.client import ModbusTcpClient

log = logging.getLogger('plc')


class InvalidPLC(Exception):
    """Exception thrown for bad device types
    """

    def __init__(self, message):
        super(InvalidPLC, self).__init__(message)


class PLC(yaml.YAMLObject):

    def __init__(self, label='', state=False, host=None, port=502, controlled_sensors_label=None):
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
