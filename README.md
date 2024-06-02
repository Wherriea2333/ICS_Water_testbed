# ICS_Water_testbed

## TODO: Install from vagrant
1. Install vagrant
2. Download the vagrantfile
3. cd to the vagrantfile
4. `vagrant up`
5. `vagrant ssh`

## Install from scratch
1. Install [docker](https://docs.docker.com/engine/install/)
2. Clone the repository
3. cd to `ICS_Water_test/ics_sandbox`, under this folder, there should be a main.py
4. Adjust the test.yml config file if needed, you may also need to change the deployment scripts of the PLC's if you change PLC address.
5. Launch the python file `sudo python3 main.py`
```Tree
├── ICS_Water_testbed
│   ├── ics_sandbox
│   │   ├── bash_utils
│   │   ├── psm
│   │   ├── sim
│   │   ├── yml
│   │   ├── main.py
├── PLCs
│   ├── DeChlorination
│   │   ├── DeChlorination.st
│   ...
├── Vagrant
│   ├── VagrantFile
├── scadaBR_conf
│   ├── scadaBR_conf.json
│   ├── scada_LTS_conf.json
├── LICENSE
├── README.md
└── .gitignore
```
In ics_sandbox, there is all files used related to the sandbox in itself, scripts to automatically deploy the sandbox, psm code for PLCs, yml config file for the physical simulation, and the python physic simulation in itself.

bash_utils contain bash scripts used to install `OpenPlc` PLCs, the physical simulation, and the `scadaBR` HMI into a docker network named swat.

psm contain python script run by each PLC's of `OpenPlc`, these codes should be copied and paste to the right PLC before run.
TODO: maybe it will be automatized !

sim contain files for the "physic" simulation in python of the swat in a simple manner.

yml contain different pretested structures

main.py just launch the installation of all docker containers at once. This file must be run as admin, due to the requirement of `OpenPLC` installation do be done by admin.

PLCs contain predefined ladder logic for the SWOT simulation. You can also generate PLC ladder logic by calling the `sim/run.py` with `-g` and the yaml config file as argument. These generated ladder program just transfer the input value to output.

Vagrant directory contains a Vagrantfile that can be used to generate the VM, and a readme about the process to create it


## Install dependencies of physic simulation
`pip install -r requirements.txt`

## Run command example
`python run.py -c test.yml -v 1`

Option:
- -c (--config) : YAML configuration file to load
- -v (--verbose) [0, 1, 2] : Set verbosity level
- -m (--math) ['proportional','sympy','wolfram'] : Type of math expression parser
- -g (--generate) : Will generate basic ladder logic files that can be used for OpenPLC (These ladder program just transfer the input to output)
## How to construct a simulation
### 1. Settings
    sim_speed: Sleeping time between simulation cycle in milliseconds
    plc_speed: When generating PLC ladder logic, the maximum time of a PLC ladder logic loop
    precision: The number of digits of numbers
    max_cycle: The number of cycles the simulation will run, if 0, it will run infinitely
    host_address: ip of the physic simulation, default is "172.18.0.10"
    port: port of the modbus server of the physic simulation, default is 12345.
Structure:
```yaml
settings:
  sim_speed: 500
  plc_speed: 20
  precision: 5
  max_cycle: 0
  host_address: "172.18.0.10"
  port: 12345
```
### 2. Devices
Authorized tag are :
- !pump
- !valve
- !filter
- !tank
- !reservoir
- !vessel

The yaml parser will instantiate python object, thus all attributes can be initialized in the yaml file if needed. The `label`, and `state` must be defined, you should also define the math function if you choose a math parser other than `proportional`. Other device specific attributes should be defined.
You can find the Devices in `/sim/Device.py`

Structure :
```yaml
devices:
  - !reservoir
    label: T-101
    max_volume: 10000
    volume: 1000
    fluid: !water {}
    self_input: 'yes'
    input_per_cycle: 20
  - !pump
    label: P-101
    volume_per_cycle: 10
    state: 'on'
  - !valve
    label: MV-201
    state: 'open'
  - !vessel
    label: RO-501
    volume: 0
    max_volume: 40
  - !filter
    label: Filter-501
```
### 3. Connections
Add connections between devices, each device can have multiples input and output devices

If you use `-m` in 'sympy' mode or 'wolfram' mode, you can write a mathematical expression to compute the output/input to/from each device.

`outputs` add the output device and also add it as the input of the output device. (`inputs` does inversely the same).
It is preferable to not mixes the two.


**Devices label are automatically added, you can also access to these devices attributes by `label.attribute`**

Some extra variables like `requested_volume` and `open_output_devices_number` are available in output_devices_expr. 
Similarly, `accepted_volume` and `open_input_devices_number` are available in input_devices_expr

Structure:
```yaml
connections:
  reservoir1:
    outputs:
      - valve1
  valve1:
    outputs:
      - pump1
      - pump2
    input_devices_expr:
      reservoir1: "requested_volume"
    output_devices_expr:
      pump1: 2 * "accepted_volume" / 3 + x
      pump2: 2 * "accepted_volume" / 3 + x
  pump1:
    outputs:
      - tank1
    input_devices_expr:
      valve1: pump1.volume_per_cycle
    output_devices_expr:
      tank: "accepted_volume"
  pump2:
    outputs:
      - tank1
    input_devices_expr:
      valve1: pump2.volume_per_cycle
    output_devices_expr:
      tank: "accepted_volume"
  tank1:
    input_devices_expr:
      pump1: "accepted_volume"
      pump2: "accepted_volume"
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
Authorized tag are :
- !flowrate
- !state
- !volume

Sensors attached to devices in order to monitor somme values. `connected_to` is the connected device_label of the sensor
The Location `X` is used for boolean value, while `W` is used for integer variable. In ModbusTCP, there is 65535 boolean and integer addresses. And the integer value should be between 0 and 65535, some boolean value after 65000 where used to verify that the PLCs are connected to the Master(physic simulation).

```yaml
sensors:
  - !volume
    label: P101
    state: 'on'
    connected_to: P-101
    location: W0
  - !flowrate
    label: P102
    state: 'on'
    connected_to: P-102
    location: W1
  - !state
    label: MV101
    state: 'on'
    connected_to: MV-101
    location: X0
```

### 6. PLCs
Instanciate PLCs with `!plc` label, the `connection_established_coil` is used to wait all PLCs being connected to start the physic simulation.
`controlled_sensors_label` list the sensors that should be read/write from the PLC.


```yaml
  - !plc
    label: PLC1
    state: 'on'
    connection_established_coil: 65001
    controlled_sensors_label:
      - P101
      - P102
      - FIT201
      - LIT101
```
