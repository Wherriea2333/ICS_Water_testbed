from ipmininet.cli import IPCLI
from ipmininet.ipnet import IPNet
from ipmininet.iptopo import IPTopo
from mininet.node import Node


#################################
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


def connectToInternet(network, switch='s1', rootip='10.0.2.5/24', subnet='10.0.2.0/24'):
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
    fixNetworkManager(root, 'root-eth0')

    # Create link between root NS and switch
    link = network.addLink(root, switch)
    link.intf1.setIP(rootip, prefixLen)

    # Start network that now includes link to root namespace
    network.start()

    # Start NAT and establish forwarding
    startNAT(root, "enp0s3", subnet)

    # Establish routes from end hosts
    for host in network.hosts:
        print("GOES INTO THE HOSTS")
        host.cmd('ip route flush root 0/0')
        host.cmd('route add -net', subnet, 'dev', host.defaultIntf())
        host.cmd('route add default gw', rootip.split('/')[0])

    return root


class MyTopology_test_network(IPTopo):
    def build(self, *args, **kwargs):
        s1 = self.addSwitch('s1')

        h1 = self.addHost('h1', ip='10.0.2.1/24')

        h2 = self.addHost('h2', ip='10.0.2.2/24')

        self.addLink(h1, s1)
        self.addLink(h2, s1)

        super().build(*args, **kwargs)


if __name__ == '__main__':
    net = IPNet(topo=MyTopology_test_network(), use_v6=False, allocate_IPs=False, waitConnected=True)

    rootnode = connectToInternet(net)
    #        net.start()
    IPCLI(net)
    stopNAT(rootnode)
    net.stop()
