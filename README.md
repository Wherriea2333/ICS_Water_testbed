# ICS_Water_testbed

## Install 
`pip install -r requirements.txt`

## Run command
`python run.py -c test.yml -v 1`

Option:
- -c (--config) : YAML configuration file to load
- -v (--verbose) [0, 1, 2] : Set verbosity level
- -m (--math) ['proportional','sympy','wolfram'] : Type of math expression parser

## How to construct a simulation
### 1. Settings
    speed: The speed at which a simulation tour is done
    precision: The number of digits of numbers
    max_cycle: The number of cycles the simulation will run
Structure:
```yaml
settings:
  speed: 1
  precision: 5
  max_cycle: 10
```
### 2. Devices
Authorized tag are :
- !pump
- !valve
- !filter
- !tank
- !reservoir
- !sensor
- !chlorinator

The yaml parser will instantiate python object, thus attributes can be initialized
in the simulation file. You can find the Devices in `/sim/Device.py`

Structure :
```yaml
devices:
  - !reservoir
    label: reservoir1
    fluid: !water {}
  - !pump
    label: pump1
```
### 3. Connections
Add connections between devices, each device can have multiples inputs and outputs
devices

If you use `-m` in 'sympy' mode or 'wolfram' mode, you can write a mathematical expression
to compute the output/input to/from each device.

`outputs` add the output device and also add it as the input of the output device. (`inputs` does inversely the same)
It is preferable to not mixes the two.


**Devices label are automatically added, you can also access to these devices attributes by `label.attr`**

Structure:
```yaml
connections:
  reservoir1:
    outputs:
      - pump1
      - pump2
    from_device_expr:
      pump1: 2 * pump1.volume_per_cycle / 3 + x
      pump2: 2 * pump2.volume_per_cycle / 3 + x
  pump1:
  outputs:
    - tank
  pump2:
    outputs:
      - tank
```
### 4. Symbols
**Devices label are automatically added, you can also access to these devices attributes by `label.attr`**

Add symbols used in the sympy/wolfram expression, they will be substituted when running the simulation
```yaml
symbols:
  x: 10
  y: 100
  z: 1000
```
### 5. Sensors
Sensors attached to devices in order to monitor somme values.
```yaml
sensors:
  - !volume
    label: reservoirsensor1
    connected_to: reservoir1
  - !volume
    label: municipaltanksensor
    connected_to: municipaltank
```