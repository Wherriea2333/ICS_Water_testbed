1. Install VirtualBox, Vagrant

Create a folder to have VagrantFile

2. `mkdir thesis`

Download ubuntu as box

3. `vagrant init ubuntu/focal64`

Modify VagrantFile network setting to allow internet connection

4. `config.vm.network "public_network", ip: "192.168.2.1"`

Modify VagrantFile VM setting

`vb.memory = "4096" vb.cpus = "4"`

create shared folder to easy change

Install pip3

5. `sudo apt update` `sudo apt install python3-pip`

[Install Mininet](https://mininet.org/download/)
6. `git clone https://github.com/mininet/mininet`, `mininet/util/install.sh -a`

[Install IPMininet](https://ipmininet.readthedocs.io/en/latest/install.html)

7. `$ sudo pip install --upgrade git+https://github.com/cnp3/ipmininet.git@v1.1`, `sudo python -m ipmininet.install -af`

## TODO: automatize it in the python install script
8. add DNS on host to install openPLC

`h1 echo "nameserver 8.8.8.8" > /etc/resolv.conf`

9. install openPLC in hosts

`git clone https://github.com/thiagoralves/OpenPLC_v3.git`

`cd OpenPLC_v3`

`./install.sh linux`


create box (Should be in the VM directory)

`vagrant package --base vagrant --output /box/vm.box`

10. access mininet host from host

enable IP forwarding:

`sudo sysctl -w net.ipv4.ip_forward=1`

Configure firewall(if necessary)

`sudo iptables -I INPUT -i mn-0-eth0 -j ACCEPT`
`sudo iptables -I OUTPUT -o mn-0-eth0 -j ACCEPT`