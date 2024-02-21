import logging
import random
import uuid

import yaml

log = logging.getLogger('phy_sim')


class InvalidFluid(Exception):
    """Exception handler for bad fluid types
    """

    def __init__(self, message):
        super(InvalidFluid, self).__init__(message)


class Fluid(yaml.YAMLObject):
    """Base class for all fluids
    """
    allowed_fluid_types = ['water', 'chlorine']

    def __init__(self, fluid_type=None, ph=None, temperature=None, salinity=None, pressure=None, flow_rate=None):
        self.uid = str(uuid.uuid4())[:8]
        self.fluid_type = fluid_type
        self.ph = ph  # For later use
        self.temperature = temperature  # For later use
        self.salinity = salinity  # For later use
        self.pressure = pressure  # For later use
        self.flow_rate = flow_rate  # For later use

        if (not fluid_type) or (fluid_type not in self.allowed_fluid_types):
            raise InvalidFluid(f"'{flow_rate}' in not a valid fluid type")

    def __repr__(self):
        return f"{self.uid} {self.fluid_type} " \
               f"pH: {self.ph} " \
               f"Salinity: {self.salinity}" \
               f" Pressure: {self.pressure} " \
               f"FlowRate: {self.flow_rate}"

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)


class Water(Fluid):
    yaml_tag = u'!water'
    yaml_loader = yaml.Loader

    def __init__(self, **kwargs):
        super(Water, self).__init__(fluid_type='water', **kwargs)
        self.ph = round(random.uniform(6.5, 8.0), 2)


class Chlorine(Fluid):
    yaml_tag = u'!chlorine'
    yaml_loader = yaml.Loader

    def __init__(self, **kwargs):
        super(Chlorine, self).__init__(fluid_type='chlorine', **kwargs)
        self.ph = 5
