import logging
import uuid
from abc import abstractmethod

import sympy.core.evalf as sp_evalf
import yaml

log = logging.getLogger('phy_sim')
# TODO: describe more the different label for each device in the readme
allowed_device_types = ['flowrate', 'state', 'volume']


class InvalidSensor(Exception):
    """Exception thrown for bad device types
    """

    def __init__(self, message):
        super(InvalidSensor, self).__init__(message)


class Sensor(yaml.YAMLObject):
    def __init__(self, label='', sensor_type=None, location=None, state=None, connected_to=None):
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
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def activate(self):
        """Set this sensor as active so the worker gets called"""
        if not self.active:
            self.active = True
        log.info(f"{self.label}: Active")

    def deactivate(self):
        """Set this sensor as inactive to prevent the worker from being called"""
        if self.active:
            self.active = False
        log.info(f"{self.label}: Inactive")

    def read_state(self):
        return self.state

    def write_state(self, state=None):
        """ Set the sensor state"""
        if state is not None:
            self.state = state
            return True
        return False

    @abstractmethod
    def worker(self):
        """Do something at `worker_frequency` rate
        """
        pass

    def monitor_device(self, device):
        """Attach to a device
        """
        self.device_to_monitor = device

    def set_location_tuple(self):
        if "QX" in self.location:
            qx = self.location.split("QX")
            location = qx[1].split(".")
            self.location_tuple = ("QX", int(location[0]), int(location[1]))
        elif "QW" in self.location:
            qw = self.location.split("QW")
            self.location_tuple = ("QW", int(qw[1]))
        elif "MD" in self.location:
            md = self.location.split("MD")
            self.location_tuple = ("MD", int(md[1]))

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


class FlowRateSensor(Sensor):
    yaml_tag = u'!flowrate'
    yaml_loader = yaml.Loader

    def __init__(self, sensor_type='flowrate', multiplier=1, **kwargs):
        self.flowrate = 0
        self.precision = 10
        self.multiplier = multiplier
        super().__init__(sensor_type=sensor_type, **kwargs)

    def worker(self):
        """Get the volume of `device_to_monitor`
        """
        self.flowrate = sp_evalf.N(self.device_to_monitor.current_flow_rate, self.precision)

    def read_sensor(self):
        """ Report device current flow rate
        """
        return sp_evalf.N(self.flowrate, self.precision)

    def write_sensor(self, state=None):
        """ Empty function
        """
        return


class StateSensor(Sensor):
    yaml_tag = u'!state'
    yaml_loader = yaml.Loader

    def __init__(self, sensor_type='state', **kwargs):
        super().__init__(sensor_type=sensor_type, **kwargs)

    def worker(self):
        pass

    def read_sensor(self):
        """ Report device state
        """
        return self.device_to_monitor.read_state()

    def write_sensor(self, state=None):
        """ set device state
        """
        if state is not None:
            self.device_to_monitor.write_state(state)


class VolumeSensor(Sensor):
    yaml_tag = u'!volume'
    yaml_loader = yaml.Loader

    def __init__(self, sensor_type='volume', multiplier=1, **kwargs):
        self.volume = 0
        self.precision = 10
        self.multiplier = multiplier
        super().__init__(sensor_type=sensor_type, **kwargs)

    def worker(self):
        """Get the volume of `device_to_monitor`
        """
        self.volume = sp_evalf.N(self.device_to_monitor.volume, self.precision)

    def read_sensor(self):
        """ Report sensor value
        """
        return sp_evalf.N(self.volume, self.precision)

    def write_sensor(self, state=None):
        """ Empty function
        """
        return
