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
                switch = self.addSwitch(f's{i}_{j}')
                switches[i][j] = switch
                host = self.addHost(f'h{i}_{j}')
                self.addLink(host, switch)

        for i in range(r):
            for j in range(r):
                current = switches[i][j]
                if j < r - 1:
                    right = switches[i][j + 1]
                    self.addLink(current, right)
                
                if i < r - 1:
                    bottom = switches[i + 1][j]
                    self.addLink(current, bottom)