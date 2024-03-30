import logging
from enum import Enum

import yaml

logging.basicConfig()
log = logging.getLogger('phy_sim')


class Allowed_math_type(Enum):
    proportional = 'proportional'
    sympy = 'sympy'
    wolfram = 'wolfram'


def parse_yml(path_to_yml_file):
    with open(path_to_yml_file, 'r') as stream:
        config = yaml.load(stream, Loader=yaml.Loader)
    return config


def build_simulation(config, math_parser):
    """Build simulation from config file"""
    settings = config['settings']
    devices = {}
    sensors = {}
    plcs = {}

    build_devices(config, devices, math_parser)

    build_sensors(config, devices, sensors)

    build_plc(config, plcs, sensors)

    return {'settings': settings, 'devices': devices, 'sensors': sensors, 'plcs': plcs}


def build_devices(config, devices, math_parser):
    # Process devices
    for device in config['devices']:
        devices[device.label] = device
    # Attribute the appropriate string parser to use math formulas in distribution of fluid in devices
    if math_parser not in [e.value for e in Allowed_math_type]:
        raise ValueError(f'Math type {math_parser} is not allowed.')
    for device in devices.values():
        device.math_parser = math_parser

    build_connection_between_device(config, devices, math_parser)
    # debug purpose log
    for device in devices.values():
        log.debug(f"{device}")
        log.debug(f"symbols:  {device.symbol_dict}")
        log.debug(f"input devices expr:  {device.input_devices_expr}")
        log.debug(f"output devices expr:  {device.output_devices_expr}")
    # add symbols to each device
    if math_parser != Allowed_math_type.proportional.value and math_parser in [e.value for e in Allowed_math_type]:
        for device in devices.values():
            device.symbol_dict.update(config['symbols'])
            device.symbol_dict.update(devices)
            log.debug(f"devices symbols:  {device.symbol_dict}")


def build_connection_between_device(config, devices, math_parser):
    # process connections between devices
    for device_label, connections in config['connections'].items():
        if 'outputs' in connections:
            for dev_output in connections['outputs']:
                devices[device_label].add_output(devices[dev_output])
        if 'inputs' in connections:
            for dev_input in connections['inputs']:
                devices[device_label].add_input(devices[dev_input])
        if 'output_devices_expr' in connections:
            if math_parser == Allowed_math_type.proportional.value:
                log.warning(f"Math parser is {Allowed_math_type.proportional.value}, Should not have expressions. ")
            for to_device_label, dev_output_expr in connections['output_devices_expr'].items():
                devices[device_label].add_to_device_expr(to_device_label, dev_output_expr)
        if 'input_devices_expr' in connections:
            if math_parser == Allowed_math_type.proportional.value:
                log.warning(f"Math parser is {Allowed_math_type.proportional.value}, Should not have expressions. ")
            for from_device_label, dev_input_expr in connections['input_devices_expr'].items():
                devices[device_label].add_from_device_expr(from_device_label, dev_input_expr)


def build_sensors(config, devices, sensors):
    # process sensors
    for sensor in config['sensors']:
        device_to_monitor = devices[sensor.device_to_monitor_label]
        sensor.set_location_tuple()
        sensor.monitor_device(device_to_monitor)
        sensors[sensor.label] = sensor
    # debug purpose log
    for sensor in sensors.values():
        log.debug(f"{sensor.label}")
        log.debug(f"location:  {sensor.location}")
        log.debug(f"location tuple:  {sensor.location_tuple}")
        log.debug(f"device to monitor:  {sensor.device_to_monitor_label}")


def build_plc(config, plcs, sensors):
    # process plcs
    for plc in config['plcs']:
        for sensor_label in plc.controlled_sensors_label:
            plc.controlled_sensors[sensor_label] = sensors[sensor_label]
        plcs[plc.label] = plc
    # debug purpose log
    for plc in plcs.values():
        log.debug(f"{plc.label}")
        # log.debug(f"controlled sensor:  {plc.controlled_sensors_label}")
