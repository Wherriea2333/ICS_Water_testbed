from yaml import CLoader

from sim.Device import *


def parse_yml(path_to_yml_file):
    with open(path_to_yml_file, 'r') as stream:
        config = yaml.load(stream, Loader=CLoader)
    return config


def build_simulation(config, math_parser):
    allowed_math_type = ['proportional', 'sympy', 'wolfram']
    settings = config['settings']
    devices = {}
    sensors = {}

    # Process devices
    for device in config['devices']:
        devices[device.label] = device
        # yaml.dump(device, sys.stdout)
        # print(device.fluid)

    # check and attribute the appropriate string parser to use math formulas in distribution of water in devices
    if math_parser not in allowed_math_type:
        raise ValueError(f'Math type {math_parser} is not allowed.')
    log.info(devices)
    for device in devices.values():
        device.math_parser = math_parser

    # process connections
    for device_label, connections in config['connections'].items():
        if 'outputs' in connections:
            for dev_output in connections['outputs']:
                devices[device_label].add_output(devices[dev_output])
        if 'inputs' in connections:
            for dev_input in connections['inputs']:
                devices[device_label].add_input(devices[dev_input])

    # process distributions
    # TODO: not finished
    # for device_label, distribution in config['distributions'].items():
    #     devices[device_label].set_distribution(distribution)

    # process sensors
    for sensor in config['sensors']:
        device_to_monitor = devices[sensor.device_to_monitor]
        sensor.monitor_device(device_to_monitor)
        sensors[sensor.label] = sensor

    return {'settings': settings, 'devices': devices, 'sensors': sensors}
