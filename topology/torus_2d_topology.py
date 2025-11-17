from mininet.topo import Topo

class Torus2DTopology(Topo):
    def __init__(self, r = 3, **params):
        if r < 2:
            raise ValueError("Parameter r must be at least 2")
        
        super().__init__(**params)
        self.r = r
        
        switches = [[None for _ in range(r)] for _ in range(r)]

        for i in range(r):
            for j in range(r):
                switch = self.addSwitch(f's{i}_{j}')
                switches[i][j] = switch
                host = self.addHost(f'h{i}_{j}')
                self.addLink(host, switch)

        for i in range(r):
            for j in range(r):
                current = switches[i][j]
                
                right = switches[i][(j + 1) % r]
                if current != right:
                    self.addLink(current, right)
                
                bottom = switches[(i + 1) % r][j]
                if current != bottom:
                    self.addLink(current, bottom)