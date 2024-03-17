# ICS_Water_testbed

## TODO: Install from vagrant
1. Install vagrant
2. Download the vagrantfile
3. cd to the vagrantfile
4. `vagrant up`
5. `vagrant ssh`

## Install from scratch
1. Install [mininet](https://mininet.org/download/): \
`git clone https://github.com/mininet/mininet` \
`mininet/util/install.sh -a`
2. Install [IPMininet](https://ipmininet.readthedocs.io/en/latest/install.html): \
`$ sudo pip install --upgrade git+https://github.com/cnp3/ipmininet.git@v1.1` \
`sudo python -m ipmininet.install -af`
3. Clone the repository

```Tree
├── ICS_Water_testbed
│   ├── mininet_topo
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
├── LICENSE
├── README.md
└── .gitignore
```
In mininet_topo, there is all files used related to the mininet topology, installation of dependencies...

bash_utils contain bash script used to install `OpenPlc` on hosts

psm contain python script run by each PLC's of `OpenPlc`, these codes should be copied and paste to the right PLC before run

sim contain files for the "physic" simulation

yml contain different pretested structure

main.py is where the mininet topology and the use of each host is defined

PLCs contain predefined ladder logic for the SWOT simulation

Vagrant directory contains a Vagrantfile that can be used to generate the VM, and a readme about the process to create it


## Install dependencies of physic simulation
`pip install -r requirements.txt`

## Run command example
`python run.py -c test.yml -v 1`

Option:
- -c (--config) : YAML configuration file to load
- -v (--verbose) [0, 1, 2] : Set verbosity level
- -m (--math) ['proportional','sympy','wolfram'] : Type of math expression parser
- -g (--generate) : Will generate basic ladder logic files that can be used for OpenPLC (Doesn't contain "real" logic in them)
## How to construct a simulation
### 1. Settings
    sim_speed: The speed at which a simulation tour is done
    plc_speed: The speed at which the PLC ladder run
    precision: The number of digits of numbers
    max_cycle: The number of cycles the simulation will run
Structure:
```yaml
settings:
  speed: 10
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
    output_devices_expr:
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
Authorized tag are :
- !flowrate
- !state
- !volume

Sensors attached to devices in order to monitor somme values.

connected_to
```yaml
sensors:
  - !volume
    label: P101
    state: 'on'
    connected_to: P-101
    location: QX0.0
  - !flowrate
    label: P102
    state: 'on'
    connected_to: P-102
    location: QX0.1
```