import logging
from abc import abstractmethod

import sympy.core.evalf as sp_evalf
import yaml

log = logging.getLogger('phy_sim')


class Sensor(yaml.YAMLObject):
    def __init__(self, **kwargs):
        self.device_to_monitor_label = None
        self.device_to_monitor = None
        self.precision = 10
        self.location = None
        super(Sensor, self).__init__(device_type="sensor", **kwargs)

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def worker(self):
        """Do something at `worker_frequency` rate
        """
        pass

    def monitor_device(self, device):
        """Attach to a device
        """
        self.device_to_monitor = device

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


# class pHSensor(Sensor):
#     yaml_tag = u'!ph'
#
#     def __init__(self, connected_to=None, **kwargs):
#         self.ph = None
#         self.device_to_monitor = connected_to
#         super(Sensor, self).__init__(device_type="sensor", **kwargs)
#
#     def input(self, fluid, volume):
#         """When fluid comes in, store the fluid context, and pass it downstream to all connected devices
#         """
#         self.ph = fluid.ph
#
#         log.debug("ph: ", self.ph)
#
#         accepted_volume = 0
#         for o in self.outputs:
#             accepted_volume = self.outputs[o].input(fluid, volume)
#         return accepted_volume
#
#     def read_sensor(self):
#         """ Report sensor value
#         """
#         return self.ph


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
