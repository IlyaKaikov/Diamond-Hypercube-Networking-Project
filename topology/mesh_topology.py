# mesh_topology.py
from mininet.topo import Topo

class MeshTopology(Topo):
    def build(self, r = 3):
        switches = [[None for _ in range(r)] for _ in range(r)]

        for i in range(r):
            for j in range(r):
                sw = self.addSwitch(f"s{i}{j}", stp = 1)
                switches[i][j] = sw

                host = self.addHost(f"h{i}{j}")
                self.addLink(host, sw)

        for i in range(r):
            for j in range(r):
                if j < r - 1:
                    self.addLink(switches[i][j], switches[i][j+1])
                if i < r - 1:
                    self.addLink(switches[i][j], switches[i+1][j])


topos = {"mesh": lambda r = 3, **params: MeshTopology(r = int(r), **params)}