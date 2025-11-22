from mininet.topo import Topo

class Torus2DTopology(Topo):
    def build(self, r = 3):
        if r < 2:
            raise ValueError("Parameter r must be at least 2")
        
        self.r = r
        switches = [[None for _ in range(r)] for _ in range(r)]

        for i in range(r):
            for j in range(r):
                switch = self.addSwitch(f"s{i}x{j}")
                switches[i][j] = switch
                host = self.addHost(f"h{i}x{j}")
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

topos = { "torus2d": lambda r = 3, **params: Torus2DTopology(r = int(r), **params) }