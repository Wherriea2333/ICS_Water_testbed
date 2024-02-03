import logging
from abc import abstractmethod

import sympy.core.evalf as sp_evalf
import yaml

log = logging.getLogger('phy_sim')


class Sensor(yaml.YAMLObject):
    def __init__(self, location=None, state=None, **kwargs):
        self.device_to_monitor_label = None
        self.device_to_monitor = None
        self.precision = 10
        self.location = location
        self.location_tuple = None
        self.active = False
        self.state = state
        super(Sensor, self).__init__(device_type="sensor", **kwargs)

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def activate(self):
        """Set this sensor as active so the worker gets called"""
        if not self.active:
            self.active = True
        log.info(f"{self}: Active")

    def deactivate(self):
        """Set this sensor as inactive to prevent the worker from being called"""
        if self.active:
            self.active = False
        log.info(f"{self}: Inactive")

    def read_state(self):
        return self.state

    def write_state(self, state=None):
        """ Set the sensor state"""
        if state is not None:
            self.state = state
            return True
        return False

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
            self.location_tuple = (qx[0], location[0], location[1])
        elif "QW" in self.location:
            qw = self.location.split("QW")
            self.location_tuple = (qw[0], qw[1])
        elif "MD" in self.location:
            md = self.location.split("MD")
            self.location_tuple = (md[0], md[1])

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
    yaml_loader = yaml.CLoader

    def __init__(self, connected_to=None, **kwargs):
        self.device_to_monitor_label = connected_to
        self.flowrate = 0
        super(Sensor, self).__init__(device_type="sensor", **kwargs)

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
    yaml_loader = yaml.CLoader

    def __init__(self, connected_to=None, **kwargs):
        self.device_to_monitor_label = connected_to
        super(Sensor, self).__init__(device_type="sensor", **kwargs)

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
    yaml_loader = yaml.CLoader

    def __init__(self, connected_to=None, **kwargs):
        self.volume = 0
        self.device_to_monitor_label = connected_to
        super(Sensor, self).__init__(device_type="sensor", **kwargs)

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
