from yaml import CLoader

from sim.Device import *


def parse_yml(path_to_yml_file):
    config = None
    with open(path_to_yml_file, 'r') as stream:
        config = yaml.load(stream, Loader=CLoader)
    return config


def build_simulation(config):
    settings = config['settings']
    devices = {}
    sensors = {}

    # Process devices
    for device in config['devices']:
        devices[device.label] = device
        # yaml.dump(device, sys.stdout)
        # print(device.fluid)

    # process connections
    for device_label, connections in config['connections'].items():
        if 'outputs' in connections:
            for dev_output in connections['outputs']:
                devices[device_label].add_output(devices[dev_output])
        if 'inputs' in connections:
            for dev_input in connections['inputs']:
                devices[device_label].add_input(devices[dev_input])

    # process sensors
    for sensor in config['sensors']:
        device_to_monitor = devices[sensor.device_to_monitor]
        sensor.monitor_device(device_to_monitor)
        sensors[sensor.label] = sensor

    return {'settings': settings, 'devices': devices, 'sensors': sensors}
