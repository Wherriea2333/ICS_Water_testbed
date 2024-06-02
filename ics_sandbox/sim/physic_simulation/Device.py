import logging
import uuid
from abc import abstractmethod
from typing import Union

import sympy.core.evalf as sp_evalf
import sympy.parsing.mathematica as mp
import sympy.parsing.sympy_parser as sp
import yaml

from Fluid import Fluid
from utils import Allowed_math_type

log = logging.getLogger('phy_sim')
allowed_device_types = ['pump', 'valve', 'filter', 'tank', 'reservoir', 'vessel']


class InvalidDevice(Exception):
    """Exception thrown for bad device types
    """

    def __init__(self, message):
        super(InvalidDevice, self).__init__(message)


# Devices
class Device(yaml.YAMLObject):
    """
    Base class for all devices
    """

    def __init__(self, device_type=None, fluid=None, label='', state=None):
        """
        :param device_type: type of device ('pump', 'valve', 'filter', 'tank', 'reservoir', 'vessel')
        :param fluid: fluid object
        :param label: label of device
        :param state: state of device

        :attr input_devices: dict of input devices, key is label, value is device object
        :attr output_devices: dict of output devices, key is label, value is device object
        :attr fluid: fluid object of class Fluid
        :attr current_flow_rate: current flow rate of device
        :attr active: active state of device
        :attr state: state of device
        :attr math_parser: str. type of math parser used
        :attr output_devices_expr: dict of output devices expressions, key is label, value is the math expression
        :attr input_devices_expr: dict of input devices expressions, key is label, value is the math expression
        :attr symbol_dict: dict of symbols, key is label used in yaml/math expression, value is the variable that can be modified
        :attr precision: number of digits rounded
        """
        self.uid = str(uuid.uuid4())[:8]
        self.device_type = device_type
        self.label = label
        self.input_devices = {}
        self.output_devices = {}
        self.fluid = fluid
        self.current_flow_rate = 0
        self.active = False
        self.state = state
        self.math_parser = None
        self.output_devices_expr = {}
        self.input_devices_expr = {}
        self.symbol_dict = {}
        self.precision = 10

        if (not self.device_type) or (self.device_type not in allowed_device_types):
            raise InvalidDevice(f"{self.device_type} in not a valid device type")

        log.info(f"{self.label}: Initialized")

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def add_input(self, device: 'Device') -> None:
        """Add the connected `device` to our input_devices and add this device to the connected device's outputs
        """
        if device.uid not in self.input_devices:
            self.input_devices[device.uid] = device
            device.add_output(self)
            log.info(f"{self}: Added input <- {device}")

    def add_output(self, device: 'Device') -> None:
        """Add the connected device to our outputs and add this device to connected device's input_devices
        """
        if device.uid not in self.output_devices:
            self.output_devices[device.uid] = device
            device.add_input(self)
            log.info(f"{self}: Added output -> {device}")

    def add_symbol(self, label: str, value) -> None:
        """Add a symbol to the symbol dict used for sympy"""
        self.symbol_dict.update({label: value})
        log.debug(f"Added Label: {label} -> {value} in symbols")

    def add_to_device_expr(self, label: str, value) -> None:
        """Add expression to an output to a device"""
        self.output_devices_expr.update({label: value})
        log.debug(f"Added Expression: push to {label} amount of {value} fluid")

    def add_from_device_expr(self, label: str, value) -> None:
        """Add expression to an input from a device"""
        self.input_devices_expr.update({label: value})
        log.debug(f"Added Expression: pull from {label} amount of {value} fluid")

    def reset_current_flow_rate(self) -> None:
        """Reset the current flow rate of the device"""
        self.current_flow_rate = 0

    def activate(self) -> None:
        """Set this device as active so the worker gets called"""
        if not self.active:
            self.active = True
        log.info(f"{self.label}: Active")

    def deactivate(self) -> None:
        """Set this device as inactive to prevent the worker from being called"""
        if self.active:
            self.active = False
        log.info(f"{self.label}: Inactive")

    def read_state(self) -> None:
        """
        Read the device state
        """
        return self.state

    def write_state(self, state: bool = None) -> bool:
        """ Set the device state
        :param state: state of device
        """
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
    def input(self, fluid: Fluid, volume: Union[int, float]):
        """Receive and process some fluid
            Override this with your own processing to perform when new fluid is received
            :param fluid: fluid object
            :param volume: volume of fluid
        """
        return 0

    @abstractmethod
    def output(self, to_device, volume: Union[int, float]):
        """Receive and process some fluid
            Override this with your own processing to perform when fluid is outputted
            :param to_device: device to output to
            :param volume: volume of fluid
        """
        return 0

    def input_fluid(self, fluid: Fluid, volume: Union[int, float]) -> Union[int, None]:
        """
        Generic input fluid function:
        proportional: determine the number of output devices, then call each device with the same amount of volume
        sympy/wolfram: decided by the yaml configuration
        """
        open_device_number = 0
        for o in self.output_devices:
            # TODO: There might be a bug here, should be active
            if self.output_devices[o].state or self.output_devices[o].state is None:
                open_device_number += 1
        # When no tank can take the input of fluid
        if open_device_number == 0:
            log.error(f"device {self} has no device to output fluid")
            return 0
        if self.math_parser == Allowed_math_type.proportional.value:
            for o in self.output_devices:
                # Send the fluid on to all outputs equally
                # log.debug(
                #     f"Device {self} call input of output_device {self.output_devices[o]} with volume {volume / open_device_number}")
                self.output_devices[o].input(fluid, volume / open_device_number)
        else:
            self.symbol_dict['accepted_volume'] = volume
            self.symbol_dict['open_output_devices_number'] = open_device_number

            if self.math_parser == Allowed_math_type.sympy.value:
                for devices_label, expr in self.output_devices_expr.items():
                    # log.debug(f"Device {self} call input of output_device {self.symbol_dict[devices_label]} "
                    #           f"with volume {sp_evalf.N(sp.parse_expr(expr, local_dict=self.symbol_dict), self.precision)}")
                    self.symbol_dict[devices_label] \
                        .input(fluid, sp_evalf.N(sp.parse_expr(expr, local_dict=self.symbol_dict), self.precision))

            elif self.math_parser == Allowed_math_type.wolfram.value:
                for devices_label, expr in self.output_devices_expr.items():
                    # log.debug(f"Device {self} call input of output_device {self.symbol_dict[devices_label]} "
                    #           f"with volume {sp_evalf.N(mp.mathematica(expr).subs(self.symbol_dict), self.precision)}")
                    self.symbol_dict[devices_label] \
                        .input(fluid, sp_evalf.N(mp.mathematica(expr).subs(self.symbol_dict), self.precision))

    def output_fluid(self, volume: Union[int, float]) -> Union[int, None]:
        """
        Generic output fluid function:
        proportional: determine the number of input devices, then call each device with the same amount of volume
        sympy/wolfram: decided by the yaml configuration
        """
        open_device_number = 0
        for o in self.input_devices:
            # TODO: There might be a bug here, should be active
            if self.input_devices[o].state or self.input_devices[o].state is None:
                open_device_number += 1
        # When no tank can take the input of fluid
        if open_device_number == 0:
            log.error(f"device {self} has no device to get input fluid")
            return 0
        if self.math_parser == Allowed_math_type.proportional.value:
            for o in self.input_devices:
                # Request the fluid from all inputs devices equally
                # log.debug(
                #     f"Device {self} call output of input device {self.input_devices[o]} with volume {volume / open_device_number}")
                self.input_devices[o].output(self, sp_evalf.N(volume / open_device_number, self.precision))
        else:
            self.symbol_dict['requested_volume'] = volume
            self.symbol_dict['open_input_devices_number'] = open_device_number
            if self.math_parser == Allowed_math_type.sympy.value:
                for devices_label, expr in self.input_devices_expr.items():
                    # log.debug(f"Device {self} call output of input device {self.symbol_dict[devices_label]} "
                    #           f"with volume {sp_evalf.N(sp.parse_expr(expr, local_dict=self.symbol_dict), self.precision)}")
                    self.symbol_dict[devices_label] \
                        .output(self, sp_evalf.N(sp.parse_expr(expr, local_dict=self.symbol_dict), self.precision))
            elif self.math_parser == Allowed_math_type.wolfram.value:
                for devices_label, expr in self.input_devices_expr.items():
                    # log.debug(f"Device {self} call output of input device {self.symbol_dict[devices_label]} "
                    #           f"with volume {sp_evalf.N(mp.mathematica(expr).subs(self.symbol_dict), self.precision)}")
                    self.symbol_dict[devices_label] \
                        .output(self, sp_evalf.N(mp.mathematica(expr).subs(self.symbol_dict), self.precision))

    def __repr__(self):
        return f"Device: {self.uid} || {self.device_type} || {self.label}"


class Pump(Device):
    yaml_tag = u'!pump'
    yaml_loader = yaml.Loader

    def __init__(self, device_type='pump', state='off', volume_per_cycle: Union[int, float] = 1, **kwargs):
        """
        Constructor
        :param device_type: type of device (pump)
        :param state: state of device (on, off)
        :param volume_per_cycle: volume of fluid to pump each cycle
        """
        state = bool(['off', 'on'].index(state))
        self.volume_per_cycle = volume_per_cycle
        super(Pump, self).__init__(device_type=device_type, state=state, **kwargs)

    def worker(self):
        """Manipulate the fluid just as this device would in the real world
        """
        if self.state:
            self.output_fluid(self.volume_per_cycle)

    def input(self, fluid: Fluid, volume: Union[int, float] = 1) -> Union[int, float]:
        """Receive the fluid, add it to output devices equally
        :param fluid: fluid object
        :param volume: volume of fluid
        """
        if self.state:
            self.fluid = fluid
            self.current_flow_rate += volume
            self.input_fluid(fluid, volume)
            return volume
        else:
            return 0

    def output(self, to_device: 'Device', volume: Union[int, float] = 1) -> Union[int, float]:
        """called only if 'pump' in series
        :param to_device: device to output to
        :param volume: volume of fluid
        """
        if self.state:
            if self.current_flow_rate + volume >= self.volume_per_cycle:
                log.warning(f"EXCEED {self} volume_per_cycle")
            self.output_fluid(volume)
            return volume
        else:
            return 0

    def turn_on(self):
        """Turn on the pump
        set state at True"""
        self.state = True

    def turn_off(self):
        """Turn off the pump
        set state at False"""
        self.state = False


class Valve(Device):
    yaml_tag = u'!valve'
    yaml_loader = yaml.Loader

    def __init__(self, device_type='valve', state='closed', **kwargs):
        """
        Constructor
        :param device_type: type of device (valve)
        :param state: state of device (closed, open)
        """
        state = bool(['closed', 'open'].index(state))
        super(Valve, self).__init__(device_type=device_type, state=state, **kwargs)

    def open(self):
        """Open the valve
        set state at True"""
        self.state = True

    def close(self):
        """Close the valve
        set state at False"""
        self.state = False

    def worker(self):
        """Do nothing, no worker required"""
        pass

    def output(self, to_device: 'Device', volume=1):
        """If the valve is open, pull `volume` amount from connected devices
        """
        if self.state:
            self.output_fluid(volume)
            return volume
        else:
            # log.debug("%s closed" % self)
            return 0

    def input(self, fluid: Fluid, volume: Union[int, float] = 1):
        """If the valve is open, pass `volume` amount of `fluid` to the connected devices
            Normally used when pump's push fluid through.
        """
        if self.state:
            self.current_flow_rate += volume
            self.input_fluid(fluid, volume)
            return volume
        else:
            return 0


class Filter(Device):
    yaml_tag = u'!filter'
    yaml_loader = yaml.Loader

    def __init__(self, device_type='filter', **kwargs):
        super(Filter, self).__init__(device_type=device_type, **kwargs)

    def worker(self):
        pass

    def output(self, to_device: 'Device', volume: Union[int, float] = 1):
        self.output_fluid(volume)
        return volume

    def input(self, fluid: Fluid, volume: Union[int, float] = 1):
        self.current_flow_rate += volume
        self.input_fluid(fluid, volume)
        return volume


class Tank(Device):
    """Infinite volume tank!"""
    yaml_tag = u'!tank'
    yaml_loader = yaml.Loader

    def __init__(self, volume: Union[int, float] = 0, max_volume: float = float('inf'), device_type: str = 'tank',
                 state: bool = True, **kwargs):
        """
        Constructor
        :param volume: initial volume of fluid in the tank
        :param max_volume: maximum volume of fluid in the tank
        """
        self.volume = volume
        self.max_volume = max_volume
        super(Tank, self).__init__(device_type=device_type, state=state, **kwargs)

    def __increase_volume(self, volume: Union[int, float]):
        """Raise the tank's volume by `volume`
        :param volume: amount of volume to raise
        :return: amount of volume that was accepted
        """
        self.volume += self.__check_increase_volume(volume)
        return volume

    def __decrease_volume(self, volume: Union[int, float]):
        """Lower the tank's volume by `volume`
        If it cannot decrease the requested volume, self.volume doesn't change
        :param volume: amount of volume to lower
        :return: amount of volume that can be lowered
        """
        self.volume -= self.__check_decrease_volume(volume)
        return volume

    def __check_increase_volume(self, volume: Union[int, float]):
        """See if the tank has enough space to store the received `volume` amount
        :param volume: amount of volume to raise
        :return: amount of volume that can be raised
        """
        if self.volume == self.max_volume:
            volume = 0
            log.warning(f"{self} full")
        elif self.volume + volume < self.max_volume:
            volume = volume
        else:
            volume = self.max_volume - self.volume
            log.warning(f"{self} max volume reached")
        return volume

    def __check_decrease_volume(self, volume: Union[int, float]):
        """See if the tank has enough volume to provide the requested `volume` amount
        :param volume: amount of volume to lower
        :return: amount of volume that can be lowered
        """
        if self.volume <= 0:
            volume = 0
            log.warning(f"{self} empty")
        elif self.volume > volume:
            volume = volume
        else:
            volume = self.volume
            log.warning(f"{self} empty")
        return volume

    def __update_fluid(self, new_context):
        """Update the fluid in the tank
        :param new_context: new fluid
        """
        self.fluid = new_context

    def input(self, fluid: Fluid, volume: Union[int, float] = 1):
        """Receive `volume` amount of `fluid`"""
        self.__update_fluid(fluid)
        accepted_volume = self.__increase_volume(volume)
        self.current_flow_rate += volume
        return accepted_volume

    # Tank output to only one device
    def output(self, to_device: 'Device', volume: Union[int, float] = 1):
        """Send `volume` amount of fluid to connected device
            This verifies that the connected device accepts the amount of volume before
            we decrease our volume. e.g. full tank.
        """
        accepted_volume = to_device.input(self.fluid, self.__check_decrease_volume(volume))
        self.__decrease_volume(accepted_volume)
        self.current_flow_rate -= volume
        return accepted_volume

    def worker(self):
        """For debugging only. Used to display the tank's volume"""
        pass


class Reservoir(Tank):
    # TODO: fix the issue for self input (workaround -> add tank+pump+valve as the initial tank input)
    yaml_tag = u'!reservoir'
    yaml_loader = yaml.Loader

    def __init__(self, device_type: str = 'reservoir', input_per_cycle: Union[int, float] = 0, self_input="no",
                 **kwargs):
        """
        Constructor
        :param device_type: type of device (reservoir)
        :param input_per_cycle: amount of fluid to add per cycle

        """
        self.input_per_cycle = input_per_cycle
        # if type(self_input) == bool:
        #     _inputs = self_input
        # else:
        #     _inputs = bool(['no', 'yes'].index(self_input))
        super(Reservoir, self).__init__(device_type=device_type, state=True, **kwargs)

    def worker(self):
        """Make sure that we don't run dry.
        """
        self.volume += self.input_per_cycle


class Vessel(Tank):
    yaml_tag = u'!vessel'
    yaml_loader = yaml.Loader

    def __init__(self, device_type='vessel', **kwargs):
        # self.max_volume = max_volume
        super(Vessel, self).__init__(device_type=device_type, **kwargs)

    def increase_volume(self, volume: Union[int, float]):
        """Raise the vessel's volume by `volume` until it is full and return the exceeded volume
        :param volume: amount of volume to raise
        :return: exceed volume to transmit to the next device
        """
        exceed = max(self.volume + volume - self.max_volume, 0)
        self.volume = min(self.max_volume, self.volume + volume)
        return exceed

    def input(self, fluid: Fluid, volume: Union[int, float] = 1):
        """Receive `volume` amount of `fluid`
        :param volume: amount of volume to raise
        :return: amount of volume that need to pass to the next device
        """
        exceed_volume = self.increase_volume(volume)
        self.current_flow_rate += exceed_volume
        self.input_fluid(fluid, exceed_volume)
        return exceed_volume

    # Tank output to only one device
    def output(self, to_device: 'Device', volume: Union[int, float] = 1):
        """Send `volume` amount of fluid to connected device
            This verifies that the connected device accepts the amount of volume before
            we decrease our volume. e.g. full tank.
        """
        self.output_fluid(volume)
        return volume

    def worker(self):
        """For debugging only. Used to display the tank's volume"""
        pass
