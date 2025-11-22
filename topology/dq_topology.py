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

    def build(self, d = 2):
        if d < 1:
            raise ValueError("Dimension must be at least 1")
        
        num_groups = 1 << (d - 1)
        switches = {}

        for group in range(num_groups):
            for i in range(7):
                switch_name = f"s{group}x{i}"
                host_name = f"h{group}x{i}"

                switch = self.addSwitch(switch_name)
                switches[(group, i)] = switch

                host = self.addHost(host_name)
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
                        for i in range(7):
                            self.addLink(switches[(group, i)], switches[(neighbor_group, i)])

topos = {"dq": lambda d = 2, **params: DQTopology(d = int(d), **params)}