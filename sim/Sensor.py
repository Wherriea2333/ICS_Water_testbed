from sim.Device import Device
import logging
import yaml
import sympy.core.evalf as sp_evalf
log = logging.getLogger('phy_sim')


class Sensor(Device):
    def __init__(self, worker_frequency=1, **kwargs):
        self.outputs = None
        self.inputs = None
        self.fluid = None
        self.device_to_monitor = None
        self.precision = 10
        super(Sensor, self).__init__(device_type="sensor", **kwargs)

    def output(self, to_device, volume):
        """Output used for pass-through sensors.
            If a connected device requests output, pass it upstream to the next device
        """
        available_volume = 0
        for i in self.inputs:
            available_volume = self.inputs[i].output(self, volume=volume)
        return available_volume

    def input(self, fluid, volume):
        """When fluid comes in, store the fluid context, and pass it downstream to all connected devices
        """
        self.fluid = fluid
        accepted_volume = 0
        for o in self.outputs:
            # Send the fluid on to all outputs
            # log.debug("%s sending fluid to %s" % (self, self.outputs[o]))
            accepted_volume = self.outputs[o].input(fluid, volume)
        return accepted_volume

    def worker(self):
        """Do something at `worker_frequency` rate
        """
        pass

    def monitor_device(self, device):
        """Attach to a device
        """
        self.device_to_monitor = device

    def read_sensor(self):
        """ Report sensor value
             Override this to customize the data reported back to PLC
        """
        return self.fluid

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


class StateSensor(Sensor):
    yaml_tag = u'!state'
    yaml_loader = yaml.CLoader

    def __init__(self, connected_to=None, **kwargs):
        self.device_to_monitor = connected_to
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
        self.device_to_monitor = connected_to
        super(Sensor, self).__init__(device_type="sensor", **kwargs)

    def worker(self):
        """Get the volume of `device_to_monitor`
        """
        self.volume = sp_evalf.N(self.device_to_monitor.volume, self.precision)

    def read_sensor(self):
        """ Report sensor value
        """
        return sp_evalf.N(self.volume, self.precision)
