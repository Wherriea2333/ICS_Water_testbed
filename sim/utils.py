from enum import Enum

from yaml import CLoader

from sim.Device import *


class Allowed_math_type(Enum):
    proportional = 'proportional'
    sympy = 'sympy'
    wolfram = 'wolfram'


def parse_yml(path_to_yml_file):
    with open(path_to_yml_file, 'r') as stream:
        config = yaml.load(stream, Loader=CLoader)
    return config


def build_simulation(config, math_parser):
    settings = config['settings']
    devices = {}
    sensors = {}

    # Process devices
    for device in config['devices']:
        devices[device.label] = device
        # yaml.dump(device, sys.stdout)
        # print(device.fluid)

    # check and attribute the appropriate string parser to use math formulas in distribution of water in devices
    if math_parser not in [e.value for e in Allowed_math_type]:
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
        if 'to_device_expr' in connections:
            for dev_output_expr in connections['to_device_expr']:
                devices[device_label].add_to_device_expr(device_label, dev_output_expr)
        if 'from_device_expr' in connections:
            for dev_input_expr in connections['from_device_expr']:
                devices[device_label].add_from_device_expr(device_label, dev_input_expr)

    for device in devices.values():
        device.symbol_dict.update(config['symbols'])
        device.symbol_dict.update(devices)
        log.debug(device.symbol_dict)

    # process sensors
    for sensor in config['sensors']:
        device_to_monitor = devices[sensor.device_to_monitor]
        sensor.monitor_device(device_to_monitor)
        sensors[sensor.label] = sensor

    return {'settings': settings, 'devices': devices, 'sensors': sensors}
