from mininet.topo import Topo

class MeshTopology(Topo):
    def __init__(self, r = 3, **params):
        if r < 1:
            raise ValueError("Parameter r must be at least 1")
        
        super().__init__(**params)
        self.r = r
        
        switches = [[None for _ in range(r)] for _ in range(r)]

        for i in range(r):
            for j in range(r):
                switch = self.addSwitch(f'switch({i},{j})')
                switches[i][j] = switch
                host = self.addHost(f'host({i},{j})')
                self.addLink(host, switch)

        for i in range(r):
            for j in range(r):
                switch = switches[i][j]
                if j < r:
                    right_switch = switches[i][j + 1]
                    self.addLink(switch, right_switch)
                
                if i < r:
                    bottom_switch = switches[i + 1][j]
                    self.addLink(switch, bottom_switch)        

if __name__ == '__main__':
    from mininet.net import Mininet
    from mininet.cli import CLI
    from mininet.log import setLogLevel

    setLogLevel('info')
    
    topo = MeshTopology()
    
    net = Mininet(topo=topo)
    net.start()
    
    print("\n*** Mininet CLI started. ***")
    print("Your topology is a 3x3 Mesh.")
    print("Try running 'pingall' or 'nodes'.")
    
    CLI(net)
    
    net.stop() 