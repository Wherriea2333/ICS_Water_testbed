from ipmininet.cli import IPCLI
from ipmininet.ipnet import IPNet
from ipmininet.iptopo import IPTopo
from mininet.node import Node

#################################

REDIS = 'redis'
SIMULATION = "simulation"
OPENPLC_BASH = "install_openplc.sh"
REDIS_SERVER_BASH = "install_redis_server.sh"

def startNAT(root, inetIntf, subnet):
    """Start NAT/forwarding between Mininet and external network
    root: node to access iptables from
    inetIntf: interface for internet access
    subnet: Mininet subnet (default 10.0/8)="""

    # Identify the interface connecting to the mininet network
    localIntf = root.defaultIntf()

    # Flush any currently active rules
    root.cmd('iptables -F')
    root.cmd('iptables -t nat -F')

    # Create default entries for unmatched traffic
    root.cmd('iptables -P INPUT ACCEPT')
    root.cmd('iptables -P OUTPUT ACCEPT')
    root.cmd('iptables -P FORWARD DROP')

    # Configure NAT
    root.cmd('iptables -I FORWARD -i', localIntf, '-d', subnet, '-j DROP')
    root.cmd('iptables -A FORWARD -i', localIntf, '-s', subnet, '-j ACCEPT')
    root.cmd('iptables -A FORWARD -i', inetIntf, '-d', subnet, '-j ACCEPT')
    root.cmd('iptables -t nat -A POSTROUTING -o ', inetIntf, '-j MASQUERADE')

    # Instruct the kernel to perform forwarding
    root.cmd('sysctl net.ipv4.ip_forward=1')


def stopNAT(root):
    """Stop NAT/forwarding between Mininet and external network"""
    # Flush any currently active rules
    root.cmd('iptables -F')
    root.cmd('iptables -t nat -F')

    # Instruct the kernel to stop forwarding
    root.cmd('sysctl net.ipv4.ip_forward=0')


def fixNetworkManager(root, intf):
    """Prevent network-manager from messing with our interface,
       by specifying manual configuration in /etc/network/interfaces
       root: a node in the root namespace (for running commands)
       intf: interface name"""
    cfile = '/etc/network/interfaces'
    line = '\niface %s inet manual\n' % intf
    config = open(cfile).read()
    if (line) not in config:
        print('*** Adding', line.strip(), 'to', cfile)
        with open(cfile, 'a') as f:
            f.write(line)
    # Probably need to restart network-manager to be safe -
    # hopefully this won't disconnect you
    root.cmd('service network-manager restart')


def connectToInternet(network, switch='s1', rootip='192.168.1.43/24', subnet='192.168.1.0/24'):
    """Connect the network to the internet
       switch: switch to connect to root namespace
       rootip: address for interface in root namespace
       subnet: Mininet subnet"""
    switch = network.get(switch)
    prefixLen = subnet.split('/')[1]
    routes = [subnet]  # host networks to route to

    # Create a node in root namespace
    root = Node('root', inNamespace=False)

    # Prevent network-manager from interfering with our interface
    # fixNetworkManager(root, 'root-eth0')

    # Create link between root NS and switch
    link = network.addLink(root, switch)
    link.intf1.setIP(rootip, prefixLen)

    # Start network that now includes link to root namespace
    network.start()

    # Start NAT and establish forwarding
    startNAT(root, "enp0s8", subnet)

    # Establish routes from end hosts
    for host in network.hosts:
        host.cmd('ip route flush root 0/0')
        host.cmd('route add -net', subnet, 'dev', host.defaultIntf())
        host.cmd('route add default gw', rootip.split('/')[0])

    # establish dns on PLC hosts
    for host in network.hosts:
        # create a folder for each host
        host.cmd(f"mkdir -p {host.name}")
        add_dns_to_hosts(host)
        if host.name == REDIS:
            install_redis_server(host)
            # launch the redis server
            # host.cmd("redis-server ./redis.conf")
        elif host.name == SIMULATION:
            # copy the folder with all physics into the host
            copy_physic_simulation(host)
            install_redis_tools(host)
        else:
            install_redis_tools(host)
            install_open_plc(host)
    return root


def add_dns_to_hosts(host):
    host.cmd('echo nameserver 8.8.8.8 > /etc/resolv.conf')


def install_redis_server(host):
    # copy redis install script to host dedicated folder
    host.cmd(f"cp ./bash_utils/{REDIS_SERVER_BASH} ./{host.name}")
    host.cmd(f"cd {host.name} || exit 1")
    host.cmd(f"chmod +x ./{REDIS_SERVER_BASH}")
    host.cmd(f"sudo ./{REDIS_SERVER_BASH}")
    host.cmd("cd ..")


def copy_physic_simulation(host):
    host.cmd(f"cp -r sim {host}/sim")


def install_redis_tools(host):
    # sudo apt-get install redis-tools
    host.cmd(f"cd {host.name} || exit 1")
    host.cmd("sudo apt install redis-tools")
    host.cmd("cd ..")


# redis server auth required password
# check redis
# redis-cli ping
# systemctl status redis
# connection to redis
# redis-cli -a "password" PING
# redis-cli -h "host-address" -p 6379 PING

def install_open_plc(host):
    # copy openplc install script to host dedicated folder
    host.cmd(f"cp ./bash_utils/{OPENPLC_BASH} ./{host.name}")
    host.cmd(f"cd {host.name} || exit 1")
    host.cmd(f"chmod +x ./{OPENPLC_BASH}")
    host.cmd(f"sudo ./{OPENPLC_BASH}")
    host.cmd("cd ..")


class Simplest_test_network(IPTopo):
    def build(self, *args, **kwargs):
        s1 = self.addSwitch('s1')

        h1 = self.addHost('h1', ip='192.168.1.2/24')

        sym = self.addHost(SIMULATION, ip='192.168.1.11/24')

        redis = self.addHost(REDIS, ip='192.168.1.10/24')

        self.addLink(h1, s1)
        self.addLink(redis, s1)
        self.addLink(sym, s1)

        super().build(*args, **kwargs)

class star_topology(IPTopo):
    def build(self, *args, **kwargs):
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        s5 = self.addSwitch('s5')
        s6 = self.addSwitch('s6')
        s7 = self.addSwitch('s7')
        s8 = self.addSwitch('s8')

        plc1 = self.addHost('plc1', ip='192.168.1.2/24')
        plc2 = self.addHost('plc2', ip='192.168.1.3/24')
        plc3 = self.addHost('plc3', ip='192.168.1.4/24')
        plc4 = self.addHost('plc4', ip='192.168.1.5/24')
        plc5 = self.addHost('plc5', ip='192.168.1.6/24')
        plc6 = self.addHost('plc6', ip='192.168.1.7/24')

        sym = self.addHost(SIMULATION, ip='192.168.1.11/24')

        redis = self.addHost(REDIS, ip='192.168.1.10/24')

        # TODO: change this scada system with a real one ...
        scada = self.addHost("scada", ip='192.168.1.12/24')

        # add link to each switch with its PLC
        self.addLink(s1, s2)
        self.addLink(s1, s3)
        self.addLink(s1, s4)
        self.addLink(s1, s5)
        self.addLink(s1, s6)
        self.addLink(s1, s7)
        self.addLink(s2, plc1)
        self.addLink(s3, plc2)
        self.addLink(s4, plc3)
        self.addLink(s5, plc4)
        self.addLink(s6, plc5)
        self.addLink(s7, plc6)

        # add link s1 to scada system
        self.addLink(s1, scada)

        super().build(*args, **kwargs)


if __name__ == '__main__':
    net = IPNet(topo=Simplest_test_network(), use_v6=False, allocate_IPs=False, waitConnected=True)

    rootnode = connectToInternet(net)
    #        net.start()
    IPCLI(net)
    stopNAT(rootnode)
    net.stop()
