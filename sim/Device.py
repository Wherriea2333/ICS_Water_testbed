import logging
import uuid
from abc import abstractmethod

import sympy.parsing.sympy_parser as sp
import sympy.parsing.mathematica as mp
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
    allowed_math_type = ['proportional', 'sympy', 'wolfram']

    def __init__(self, device_type=None, fluid=None, label='', state=None):
        self.uid = str(uuid.uuid4())[:8]
        self.device_type = device_type
        self.label = label
        self.input_devices = {}
        self.output_devices = {}
        self.fluid = fluid
        self.active = False
        self.state = state
        self.math_parser = None
        self.to_device_expr = {}
        self.symbol_dict = {}

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

    def input_fluid(self, fluid, volume):
        if self.math_parser == 'proportional':
            for o in self.output_devices:
                # Send the fluid on to all outputs equally
                self.output_devices[o].input(fluid, volume / len(self.output_devices))
        elif self.math_parser == 'sympy':
            for devices_label, expr in self.to_device_expr:
                self.output_devices[devices_label].input(fluid, sp.parse_expr(expr, local_dict=self.symbol_dict))
        elif self.math_parser == 'wolfram':
            for devices_label, expr in self.output_devices:
                self.output_devices[devices_label].input(fluid, mp.mathematica(expr).subs(self.symbol_dict))

    def output_fluid(self, volume):
        if self.math_parser == 'proportional':
            for o in self.input_devices:
                # Send the fluid on to all outputs equally
                self.input_devices[o].output(self, volume)
        elif self.math_parser == 'sympy':
            for devices_label, expr in self.input_devices:
                self.input_devices[devices_label].output(self, volume)
        elif self.math_parser == 'wolfram':
            for devices_label, expr in self.input_devices:
                self.input_devices[devices_label].output(self, volume)

    def __repr__(self):
        return f"Device: {self.uid} || {self.device_type} || {self.label}"


class Pump(Device):
    yaml_tag = u'!pump'
    yaml_loader = yaml.CLoader

    def __init__(self, device_type='pump', state='off', **kwargs):
        state = bool(['off', 'on'].index(state))
        self.volume_per_cycle = 1
        super(Pump, self).__init__(device_type=device_type, state=state, **kwargs)

    def worker(self):
        """Manipulate the fluid just as this device would in the real world
        """
        if self.state:
            for i in self.input_devices:
                self.input_devices[i].output(self, self.volume_per_cycle)

    def input(self, fluid, volume=1):
        """Receive the fluid, add it to output devices equally"""
        if self.state:
            self.fluid = fluid
            self.input_fluid(fluid, volume)
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

    def __init__(self, device_type='valve', state='closed', **kwargs):

        state = bool(['closed', 'open'].index(state))
        self.current_flow_rate = 0
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
            self.current_flow_rate += volume
            self.output_fluid(volume)
            return volume
        else:
            # log.debug("%s closed" % self)
            return 0

    def input(self, fluid, volume=1):
        """If the valve is open, pass `volume` amount of `fluid` to the connected devices
            Normally used when pump's push fluid through.
        """
        if self.state:
            self.input_fluid(fluid, volume)
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
        self.output_fluid(volume)
        return volume_per_device

    def input(self, fluid, volume=1):
        log.info(f"volume through filter: {volume}")
        self.input_fluid(fluid, volume)
        return volume


class Tank(Device):
    """Infinite volume tank!"""
    yaml_tag = u'!tank'
    yaml_loader = yaml.CLoader

    def __init__(self, volume=0, device_type='tank', **kwargs):
        self.initial_volume = volume
        super(Tank, self).__init__(device_type=device_type, **kwargs)

    def __increase_volume(self, volume):
        """Raise the tank's volume by `volume`"""
        self.initial_volume += volume
        return volume

    def __decrease_volume(self, volume):
        """Lower the tank's volume by `volume`
        If it cannot decrease the requested volume, self.volume doesn't change"""
        self.initial_volume -= self.__check_volume(volume)
        return volume

    def __check_volume(self, volume):
        """See if the tank has enough volume to provide the requested `volume` amount
        """
        if self.initial_volume <= 0:
            volume = 0
        elif self.initial_volume > volume:
            volume = volume
        else:
            volume = self.initial_volume
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
        accepted_volume = to_device.input(self.fluid, self.__check_volume(volume))
        self.__decrease_volume(accepted_volume)
        return accepted_volume

    def worker(self):
        """For debugging only. Used to display the tank's volume"""
        pass


class Reservoir(Tank):
    yaml_tag = u'!reservoir'
    yaml_loader = yaml.CLoader

    def __init__(self, **kwargs):
        self.input_per_cycle = 10
        super(Reservoir, self).__init__(device_type='reservoir', **kwargs)

    def worker(self):
        """Make sure that we don't run dry.
        """
        self.initial_volume += self.input_per_cycle
