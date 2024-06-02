import logging
import uuid
from abc import abstractmethod
from typing import Union

import sympy.core.evalf as sp_evalf
import yaml
from numpy import random

from ics_sandbox.sim.physic_simulation.Device import Device

log = logging.getLogger('phy_sim')
# TODO: describe more the different label for each device in the readme
allowed_device_types = ['flowrate', 'state', 'volume']


class InvalidSensor(Exception):
    """Exception thrown for bad device types
    """

    def __init__(self, message):
        super(InvalidSensor, self).__init__(message)


class Sensor(yaml.YAMLObject):
    """Abstract Sensor"""

    def __init__(self, label='', sensor_type: str = None, location: str = None, state: bool = None,
                 connected_to: str = None) -> None:
        """
        :param sensor_type: Type of sensor (flowrate, state, volume)
        :param label: Label of sensor
        :param location: Location of sensor (i.e X1, X10, W2, W25)
        :param state: State of sensor
        :param connected_to: Device label to monitor
        """
        self.uid = str(uuid.uuid4())[:8]
        self.sensor_type = sensor_type
        self.label = label
        self.device_to_monitor_label = connected_to
        self.device_to_monitor = None
        self.location = location
        self.location_tuple = None
        self.active = False
        self.state = state

        if (not self.sensor_type) or (self.sensor_type not in allowed_device_types):
            raise InvalidSensor(f"{self.sensor_type} in not a valid device type")

    @classmethod
    def from_yaml(cls, loader, node):
        """Method to load python object from yml file"""
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def activate(self) -> None:
        """Set this sensor as active so the worker gets called"""
        if not self.active:
            self.active = True
        log.info(f"{self.label}: Active")

    def deactivate(self) -> None:
        """Set this sensor as inactive to prevent the worker from being called"""
        if self.active:
            self.active = False
        log.info(f"{self.label}: Inactive")

    def read_state(self) -> None:
        """Read the sensor state"""
        return self.state

    def write_state(self, state: bool = None) -> bool:
        """Set the sensor state"""
        if state is not None:
            self.state = state
            return True
        return False

    @abstractmethod
    def worker(self):
        """Do something at `worker_frequency` rate"""
        pass

    def monitor_device(self, device: Device) -> None:
        """
        :param device: Device to monitor
        Attach a sensor to a device"""
        self.device_to_monitor = device

    def set_location_tuple(self) -> None:
        """Set the location tuple from the location defined in the yaml config file"""
        if "X" in self.location:
            x = self.location.split("X")
            self.location_tuple = ("X", int(x[1]))
        elif "W" in self.location:
            w = self.location.split("W")
            self.location_tuple = ("W", int(w[1]))
        else:
            log.error(f"Your sensor {self.label} has an invalid location {self.location}, "
                      f"location should be at X for bit, or W for word(int)")

    @abstractmethod
    def read_sensor(self):
        """ Report sensor value
             Override this to customize the data reported back to PLC
        """
        pass

    @abstractmethod
    def write_sensor(self, value=None):
        """ Override this to do something to the device when PLC receives write commands
            E.g. open/close valve
        """
        pass


class AnalogSensor(Sensor):
    """Abstract class for analog sensors"""

    def __init__(self, sensor_type: str = None, precision: int = 5, multiplier: Union[int, float] = 1, seed: int = 123,
                 standard_deviation: int = 0, **kwargs) -> None:
        """
        :param sensor_type: Type of sensor (flowrate, volume)
        :param precision: Number of digits to round the number
        :param multiplier: Multiplier of the sensor value
        :param seed: Seed for the random number generator
        :param standard_deviation: Standard deviation of the sensor
        """
        self.precision = precision
        self.multiplier = multiplier
        self.random_generator = random.default_rng(seed)
        self.standard_deviation = standard_deviation
        super().__init__(sensor_type=sensor_type, **kwargs)

    @abstractmethod
    def worker(self):
        """Do something at `worker_frequency` rate"""
        pass

    @abstractmethod
    def read_sensor(self):
        """ Report sensor value
             Override this to customize the data reported back to PLC
        """
        pass

    @abstractmethod
    def write_sensor(self, value=None):
        """ Override this to do something to the device when PLC receives write commands
            E.g. open/close valve
        """
        pass


class FlowRateSensor(AnalogSensor):
    """Flow rate sensor"""
    yaml_tag = u'!flowrate'
    yaml_loader = yaml.Loader

    def __init__(self, sensor_type: str = 'flowrate', **kwargs):
        """
        :param sensor_type: Type of sensor: flowrate
        """
        self.flowrate = 0
        super().__init__(sensor_type=sensor_type, **kwargs)

    def worker(self) -> None:
        """Get the flow rate of the monitored device
        """
        self.flowrate = sp_evalf.N(
            self.device_to_monitor.current_flow_rate + self.random_generator.normal(0, self.standard_deviation),
            self.precision)

    def read_sensor(self) -> None:
        """ Report device current flow rate
        """
        return sp_evalf.N(self.flowrate, self.precision)

    def write_sensor(self, state: bool = None) -> None:
        """ Empty function
        """
        return


class VolumeSensor(AnalogSensor):
    """Volume sensor"""
    yaml_tag = u'!volume'
    yaml_loader = yaml.Loader

    def __init__(self, sensor_type='volume', **kwargs):
        """
        :param sensor_type: Type of sensor: volume
        """
        self.volume = 0
        super().__init__(sensor_type=sensor_type, **kwargs)

    def worker(self) -> None:
        """Get the volume of fluid of the monitored device"""
        self.volume = sp_evalf.N(
            self.device_to_monitor.volume + self.random_generator.normal(0, self.standard_deviation), self.precision)

    def read_sensor(self) -> None:
        """Report sensor value"""
        return sp_evalf.N(self.volume, self.precision)

    def write_sensor(self, state: bool = None) -> None:
        """Empty function"""
        return


class StateSensor(Sensor):
    yaml_tag = u'!state'
    yaml_loader = yaml.Loader

    def __init__(self, sensor_type='state', **kwargs):
        """
        :param sensor_type: Type of sensor: state
        """
        self.recorded_state = None
        super().__init__(sensor_type=sensor_type, **kwargs)

    def worker(self) -> None:
        """Get the state of the monitored device"""
        self.recorded_state = self.device_to_monitor.read_state()
        pass

    def read_sensor(self) -> None:
        """Report device state"""
        return self.recorded_state

    def write_sensor(self, state: bool = None) -> None:
        """Set device state"""
        if state is not None:
            self.device_to_monitor.write_state(state)
            if state:
                self.device_to_monitor.activate()
            else:
                self.device_to_monitor.deactivate()
