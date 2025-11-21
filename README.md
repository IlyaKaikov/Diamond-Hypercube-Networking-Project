# Diamond Hypercube Networking Project

This project emulates different network topologies in **Mininet** (Python) and compares their performance, with a focus on the **Diamond Hypercube (DQ)** topology versus more traditional ones like a **2D mesh** and **2D torus**.

This project is based on the Diamond Hypercube topology described in [1].


## Goals

- Implement custom Mininet topologies:
  - Diamond Hypercube (DQ)
  - 2D Mesh
  - 2D Torus
- Add simple one-to-one routing for each topology using static OpenFlow rules.
- Measure and compare:
  - Latency

## Requirements

- Ubuntu with **Mininet**
- **Python 3**

## Reference

[1] A. Saif, O. Alhuniti, A. Abu Taleb, A. Odeh, and B. A. Mahafzah,  
“Diamond hypercube interconnection network: topological structure and properties,”  
*The Journal of Supercomputing*, vol. 81, article 901, 2025.  
DOI: https://doi.org/10.1007/s11227-025-07379-4
