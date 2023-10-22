import logging
import threading
import time
import uuid
from abc import abstractmethod

import yaml

from sim.Fluid import Fluid

log = logging.getLogger('phy_sim')


def equal_division_to_devices(volume: float, number_of_devices: int):
    """Divide the volume equally among the devices
    """
    return volume / number_of_devices


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
        self.previous_output_device = None

        if (not self.device_type) or (self.device_type not in self.allowed_device_types):
            raise InvalidDevice(f"{self.device_type} in not a valid device type")

        log.info(f"{self}: Initialized")

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def add_input(self, device):
        """Add the connected `device` to our input_devices and add this device to the connected device's outputs
        """
        if device.uid not in self.input_devices:
            self.input_devices[device.uid] = device
            device.add_output(self)
            log.info(f"{self}: Added input <- {device}")

    def add_output(self, device):
        """Add the connected device to our outputs and add this device to connected device's input_devices
        """
        if device.uid not in self.output_devices:
            self.output_devices[device.uid] = device
            device.add_input(self)
            log.info(f"{self}: Added output -> {device}")

    def run(self):
        # TODO: not used for the moment
        """Executed at least once and at regular intervals if `worker_frequency` is not None.
            Used to call worker method
        """
        if self.active:
            # log.debug(f"{self} up at : {datetime.now()}")
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
            # self.run()
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
            Update fluid, pull input_devices, push outputs, etc.
            Override this for each custom Device
        """
        pass

    @abstractmethod
    def input(self, fluid: Fluid, volume: float):
        """Receive and process some fluid
            Override this with your own processing to perform when new fluid is received
        """
        return 0

    @abstractmethod
    def output(self, to_device, volume: float):
        """Receive and process some fluid
            Override this with your own processing to perform when fluid is outputted
        """
        return 0

    def __repr__(self):
        return f"Device: {self.uid} || {self.device_type} || {self.label}"


class Pump(Device):
    yaml_tag = u'!pump'
    yaml_loader = yaml.CLoader

    def __init__(self, device_type='pump', state='off', **kwargs):
        state = bool(['off', 'on'].index(state))
        super(Pump, self).__init__(device_type=device_type, state=state, **kwargs)

    def worker(self):
        """Manipulate the fluid just as this device would in the real world
        """
        if self.state:
            for i in self.input_devices:
                self.input_devices[i].output(self, 1)

    # TODO: what happen if a pump want to output to a devices which is closed?
    def input(self, fluid, volume=1):
        """Receive the fluid, add it to output devices equally"""
        if self.state:
            self.fluid = fluid
            if self.previous_output_device is None:
                for o in self.output_devices:
                    # Send the fluid on to all outputs
                    self.output_devices[o].input(fluid, volume / len(self.output_devices))
            else:
                self.previous_output_device.input(fluid, volume)
                self.previous_output_device = None
            return volume
        else:
            return 0

    def output(self, to_device, volume=1):
        if self.state:
            return self.fluid
        else:
            return 0

    def turn_on(self):
        self.state = True

    def turn_off(self):
        self.state = False


class Valve(Device):
    yaml_tag = u'!valve'
    yaml_loader = yaml.CLoader

    def __init__(self, device_type='valve', state='closed', capacity=0, **kwargs):

        state = bool(['closed', 'open'].index(state))
        self.capacity = capacity
        super(Valve, self).__init__(device_type=device_type, state=state, **kwargs)

    def open(self):
        self.state = True

    def close(self):
        self.state = False

    def worker(self):
        pass

    def output(self, to_device, volume=1):
        """If the valve is open, pull `volume` amount from connected devices
        """
        if self.state:
            # compute volume to output
            active_device_number = 0
            for device in self.output_devices.values():
                if device.active:
                    active_device_number += 1
            log.info(f"output volume from valve {volume}")
            max_volume_per_device = equal_division_to_devices(self.capacity, active_device_number)
            desired_volume = min(volume, max_volume_per_device)

            self.previous_output_device = to_device
            # call the previous device output with the desired volume
            for i in self.input_devices:
                self.input_devices[i].output(self, desired_volume)
            return desired_volume
        else:
            # log.debug("%s closed" % self)
            return 0

    def input(self, fluid, volume=1):
        """If the valve is open, pass `volume` amount of `fluid` to the connected devices
            Normally used when pump's push fluid through.
        """
        if self.state:
            active_device_number = 0
            for device in self.output_devices.values():
                if device.active:
                    active_device_number += 1
            max_volume_per_device = equal_division_to_devices(self.capacity, active_device_number)
            desired_volume = min(volume, max_volume_per_device)

            if self.previous_output_device is None:
                for o in self.output_devices:
                    # Send the fluid on to all outputs
                    self.output_devices[o].input(fluid, desired_volume)
            else:
                self.previous_output_device.input(fluid, min(volume, self.capacity))
                self.previous_output_device = None
            return volume
        else:
            return 0


class Filter(Device):
    yaml_tag = u'!filter'
    yaml_loader = yaml.CLoader

    def __init__(self, device_type='filter', **kwargs):
        super(Filter, self).__init__(device_type=device_type, **kwargs)

    def worker(self):
        pass

    def output(self, to_device, volume=1):
        volume_per_device = equal_division_to_devices(volume, len(self.input_devices))
        self.previous_output_device = to_device
        for i in self.input_devices:
            self.input_devices[i].output(self, volume=volume_per_device)
        return volume_per_device

    def input(self, fluid, volume=1):
        log.info(f"volume through filter: {volume}")
        if self.previous_output_device is None:
            for o in self.output_devices:
                self.output_devices[o].input(fluid, volume)
        else:
            self.previous_output_device.input(fluid, volume)
            self.previous_output_device = None
        return volume


class Tank(Device):
    """Infinite volume tank!"""
    yaml_tag = u'!tank'
    yaml_loader = yaml.CLoader

    def __init__(self, volume=0, device_type='tank', **kwargs):
        self.volume = volume
        super(Tank, self).__init__(device_type=device_type, **kwargs)

    def __increase_volume(self, volume):
        """Raise the tank's volume by `volume`"""
        self.volume += volume
        return volume

    def __decrease_volume(self, volume):
        """Lower the tank's volume by `volume`
        If it cannot decrease the requested volume, self.volume doesn't change"""
        self.volume -= self.__check_volume(volume)
        return volume

    def __check_volume(self, volume):
        """See if the tank has enough volume to provide the requested `volume` amount
        """
        if self.volume <= 0:
            volume = 0
        elif self.volume > volume:
            volume = volume
        else:
            volume = self.volume
        return volume

    def __update_fluid(self, new_context):
        self.fluid = new_context

    def input(self, fluid, volume=1):
        """Receive `volume` amount of `fluid`"""
        self.__update_fluid(fluid)
        accepted_volume = self.__increase_volume(volume)
        return accepted_volume

    # Tank output to only one device
    def output(self, to_device, volume=1):
        """Send `volume` amount of fluid to connected device
            This verifies that the connected device accepts the amount of volume before
            we decrease our volume. e.g. full tank.
        """
        self.previous_output_device = to_device
        accepted_volume = self.previous_output_device.input(self.fluid, self.__check_volume(volume))
        self.__decrease_volume(accepted_volume)
        self.previous_output_device = None
        return accepted_volume

    def worker(self):
        """For debugging only. Used to display the tank's volume"""
        pass


class Reservoir(Tank):
    yaml_tag = u'!reservoir'
    yaml_loader = yaml.CLoader

    def __init__(self, **kwargs):
        super(Reservoir, self).__init__(device_type='reservoir', **kwargs)

    def worker(self):
        """Make sure that we don't run dry.
        """
        self.volume += 10
