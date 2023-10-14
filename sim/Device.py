import logging
import threading
import time
import uuid
from abc import abstractmethod
from datetime import datetime

import yaml

log = logging.getLogger('phy_sim')


class InvalidDevice(Exception):
    """Exception thrown for bad device types
    """

    def __init__(self, message):
        super(InvalidDevice, self).__init__(message)


# Devices
class Device(yaml.YAMLObject):
    allowed_device_types = ['pump', 'valve', 'filter', 'tank', 'reservoir', 'sensor', 'chlorinator']

    def __init__(self, device_type=None, fluid=None, label='', state=None, worker_frequency=1):
        self.uid = str(uuid.uuid4())[:8]
        self.device_type = device_type
        self.label = label
        self.input_devices = {}
        self.output_devices = {}
        self.fluid = fluid
        self.active = False
        # Time interval in seconds. set to None if the device doesn't need a worker loop
        self.worker_frequency = worker_frequency
        self.speed = 1
        self.state = state

        if (not self.device_type) or (self.device_type not in self.allowed_device_types):
            raise InvalidDevice(f"{self.device_type} in not a valid device type")

        log.info(f"{self}: Initialized")

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def add_input(self, device):
        """Add the connected `device` to our inputs and add this device to the connected device's outputs
        """
        if device.uid not in self.input_devices:
            self.input_devices[device.uid] = device
            device.add_output(self)
            log.info(f"{self}: Added input <- {device}")

    def add_output(self, device):
        """Add the connected device to our outputs and add this device to connected device's inputs
        """
        if device.uid not in self.output_devices:
            self.output_devices[device.uid] = device
            device.add_input(self)
            log.info(f"{self}: Added output -> {device}")

    def run(self):
        """Executed at at least once and at regular intervals if `worker_frequency` is not None.
            Used to call worker method
        """
        if self.active:
            log.debug(f"{self} up at : {datetime.now()}")
            self.worker()

            if self.worker_frequency:
                # Calculate the next run time based on simulation speed and device frequency
                delay = (-time.time() % (self.speed * self.worker_frequency))
                t = threading.Timer(delay, self.run)
                t.daemon = True
                t.start()

    def activate(self):
        """Set this device as active so the worker gets called"""
        if not self.active:
            self.active = True
            self.run()
        log.info(f"{self}: Active")

    def deactivate(self):
        """Set this device as inactive to prevent the worker from being called"""
        if self.active:
            self.active = False
        log.info(f"{self}: Inactive")

    def read_state(self):
        return self.state

    def write_state(self, state=None):
        """ Set the devices state"""
        if state is not None:
            self.state = state
            return True
        return False

    @abstractmethod
    def worker(self):
        """Do something each cycle of `worker_frequency`
            Update fluid, pull inputs, push outputs, etc.
            Override this for each custom Device
        """
        pass

    @abstractmethod
    def input(self):
        """Receive and process some fluid
            Override this with your own processing to perform when new fluid is received
        """
        return 0

    @abstractmethod
    def output(self):
        """Receive and process some fluid
            Override this with your own processing to perform when fluid is outputted
        """
        return 0

    def __repr__(self):
        return f"Device: {self.uid} || {self.device_type} || {self.label}"
