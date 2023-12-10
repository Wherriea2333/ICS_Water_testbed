from ipmininet.cli import IPCLI
from ipmininet.ipnet import IPNet
from ipmininet.iptopo import IPTopo
from mininet.node import Node

#################################

redis = 'redis'
simulation = "simulation"


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
        if host == redis:
            install_redis(host)
        elif host == simulation:
            # copy the folder with all physics into the host,
            # install all dependencies
            # then run the simulation
            pass
        else:
            add_dns_to_hosts(host)
            install_open_plc(host)

    return root


def add_dns_to_hosts(host):
    if host != redis:
        host.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')


def install_redis(host):
    host.cmd("sudo apt-get install redis")
    # host.cmd("sudo apt install redis-tools")


def install_open_plc(host):
    host.cmd("mkdir" + str(host))
    host.cmd("cd " + str(host))
    host.cmd("git clone https://github.com/thiagoralves/OpenPLC_v3.git")
    host.cmd("cd OpenPLC_v3")
    host.cmd("./install.sh linux")
    host.cmd("./start_openplc.sh &")
    host.cmd("/")


class MyTopology_test_network(IPTopo):
    def build(self, *args, **kwargs):
        s1 = self.addSwitch('s1')

        h1 = self.addHost('h1', ip='192.168.1.2/24')

        h2 = self.addHost('h2', ip='192.168.1.3/24')

        h3 = self.addHost(simulation, ip='192.168.1.11')

        redis_host = self.addHost(redis, ip='192.168.1.10/24')

        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(redis_host, s1)
        self.addLink(h3, s1)

        super().build(*args, **kwargs)


if __name__ == '__main__':
    net = IPNet(topo=MyTopology_test_network(), use_v6=False, allocate_IPs=False, waitConnected=True)

    rootnode = connectToInternet(net)
    #        net.start()
    IPCLI(net)
    stopNAT(rootnode)
    net.stop()
