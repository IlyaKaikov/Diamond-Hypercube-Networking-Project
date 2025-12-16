from mininet.topo import Topo

class DQTopology(Topo):
    DIAMOND_NEIGHBORS = {
        0: [1, 2, 4],
        1: [0, 3, 5],
        2: [0, 3, 6],
        3: [1, 2],
        4: [0, 5, 6],
        5: [1, 4],
        6: [2, 4],
    }

    def build(self, d=2):
        if d < 1:
            raise ValueError("Dimension must be at least 1")

        m = d - 1  # number of hypercube/group bits
        if m > 16:
            raise ValueError("This IPv4 encoding supports at most d<=17 (group bits <=16)")

        num_groups = 1 << m
        switches = {}
        shift = 16 - m if m > 0 else 0

        for group in range(num_groups):
            group_tag = (group << shift) & 0xFFFF
            gh = (group_tag >> 8) & 0xFF
            gl = group_tag & 0xFF

            for p in range(7):
                switch_name = f"s{group}x{p}"
                host_name = f"h{group}x{p}"
                switch = self.addSwitch(switch_name)
                switches[(group, p)] = switch
                host = self.addHost(host_name, ip=f"10.{gh}.{gl}.{p+1}/8")
                self.addLink(host, switch)

        for group in range(num_groups):
            for i, neighbors in self.DIAMOND_NEIGHBORS.items():
                for j in neighbors:
                    if i < j:
                        self.addLink(switches[(group, i)], switches[(group, j)])

        if d > 1:
            group_bits = d - 1
            for group in range(num_groups):
                for bit in range(group_bits):
                    neighbor_group = group ^ (1 << bit)
                    if group < neighbor_group:
                        for p in range(7):
                            self.addLink(switches[(group, p)], switches[(neighbor_group, p)])

topos = {"dq": lambda d = 2, **params: DQTopology(d = int(d), **params)}