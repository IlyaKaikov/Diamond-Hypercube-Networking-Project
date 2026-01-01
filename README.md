# Diamond Hypercube Networking Project

This repo reconstructs and evaluates the **Diamond–Hypercube (DQ)** interconnection network alongside **Mesh** and **2D Torus** topologies using **Mininet + Open vSwitch**.  
The goal is to measure how topology impacts Flow Completion Time (FCT) under realistic background traffic (**random-uniform** and **in-cast**).

The Diamond Hypercube topology described in [1].


## What's implemented

- *Custom Mininet topologies:*
  - Diamond Hypercube (DQ)
  - 2D Mesh
  - 2D Torus
    
- *Shortest path routing algorithms:*
  - X-Y routing for Mesh and Torus.
  - DQ routing:
      - Phase 1: route between groups by flipping group-label bits (hypercube-style).
      - Phase 2: route inside the diamond subgraph using precomputed next-hops (BFS-based).
- *Traffic patterns (background load):*
  - Random-uniform background flows: random source/destination pairs (seeded).
  - Incast (many-to-one) background flows: n random sources send to a single random destination (seeded).
- *Metric: Flow Completion Time (FCT):*
  - For each run, the system sends probe transfers between a fixed “farthest pair” in each topology, while background flows run concurrently. Probe completion time (from iperf3) is recorded as the FCT.
  - The median, 95th percentile and 99th percentile FCT is measured for the given topology and load level.
## Requirements

- **Linux enviromnemt**
- **Python 3.8+**
- **Mininet**
- **iperf3**

## How it works

1. Build topology in Mininet (hosts + OVS switches).
2. Install static routes by adding OpenFlow rules into OVS switches.
3. Start background traffic (random-uniform or in-cast).
4. Run repeated probes to measure FCT.
5. Append results to CSV and create graphs for median/95th percentile/99th percentile FCT.

## Running experiments

1. *Random uniform background traffic (single run):*
   - **Example (Mesh, r=14):**
     
     - sudo python3 -m experiments.random_uniform_latency --topo mesh --r 14 --bg-num-flows 300 --bg-parallel-streams 1 --bg-duration 2000 --bg-warmup-sec 1 --num-probes 100 --probe-megabytes 10 --seed 1 --csv-out results_random_uniform.csv
       
2. *In-cast background traffic (single run):*
   - **Exmaple (DQ, d=5):**
     
     - sudo python3 -m experiments.incast_latency --topo dq --d 5 --bg-num-flows 300 --bg-parallel-streams 1 --bg-duration 2000 --bg-warmup-sec 1 --num-probes 100 --probe-megabytes 10 --seed 1 --csv-out results_incast.csv
3. *Grid runs:*
   - **Run a predefined grid for random-uniform:**
     
     - sudo python3 -m experiments.run_random_uniform_grid
   - **Run a predefined grid for in-cast:**
     
     - sudo python3 -m experiments.run_incast_grid

## Plotting and Analysis

- *A helper script computes median / p95 / p99 FCT vs background load and writes plots:*
  
  - python3 analysis/analyze_fct_vs_bg.py --csv results_incast.csv --r 14 --d 5 --outdir plots

## Citation

[1] *A. Saif, O. Alhuniti, A. Abu Taleb, A. Odeh, and B. A. Mahafzah,  
“Diamond hypercube interconnection network: topological structure and properties,”  
*The Journal of Supercomputing*, vol. 81, article 901, 2025.  
DOI: https://doi.org/10.1007/s11227-025-07379-4*
