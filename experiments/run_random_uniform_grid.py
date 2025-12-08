import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class SizeConfig:
    label: str # "small", "medium", "large"
    r: Optional[int]
    d: Optional[int]

@dataclass
class LoadConfig:
    label: str # "low", "medium", "high"
    bg_multiplier: int
    bg_parallel_streams: int

SIZE_SETS: List[SizeConfig] = [SizeConfig(label="small", r=4, d=2),]
LOAD_LEVELS: List[LoadConfig] = [LoadConfig(label="medium", bg_multiplier=5, bg_parallel_streams=5),]
TOPOLOGIES = ["mesh", "torus2d", "dq"]
SEEDS = [10, 20]
NUM_PROBES = 20
PROBE_MEGABYTES = 50.0
BG_DURATION = 120.0
IPERF_CMD = "iperf3"
CSV_OUT = "results_random_uniform_all.csv"

def run_single_experiment(topo, size: SizeConfig, load: LoadConfig, seed,):
    base_args: List[str] = ["python3", "-m", "experiments.random_uniform_latency", "--topo", topo,
                            "--bg-multiplier", str(load.bg_multiplier), "--bg-parallel-streams", str(load.bg_parallel_streams), 
                            "--bg-duration", str(BG_DURATION), "--num-probes", str(NUM_PROBES), "--probe-megabytes", str(PROBE_MEGABYTES), 
                            "--seed", str(seed), "--iperf-cmd",  IPERF_CMD, "--csv-out", CSV_OUT, "--loglevel", "info",]

    if topo in ("mesh", "torus2d"):
        if size.r is None:
            raise ValueError(f"Topology '{topo}' requires r, but size {size.label} has r=None")
        base_args.extend(["--r", str(size.r)])
    elif topo == "dq":
        if size.d is None:
            raise ValueError(f"Topology 'dq' requires d, but size {size.label} has d=None")
        base_args.extend(["--d", str(size.d)])
    else:
        raise ValueError(f"Unsupported topology '{topo}'")

    label = (f"topo={topo}, size={size.label}(r={size.r},d={size.d}), "
             f"load={load.label}(k={load.bg_multiplier},P={load.bg_parallel_streams}), seed={seed}")

    print(f"Running experiment: {label}")
    print("Command:", " ".join(base_args))

    subprocess.run(base_args, check=True)

def main():
    for size in SIZE_SETS:
        for load in LOAD_LEVELS:
            for topo in TOPOLOGIES:
                for seed in SEEDS:
                    run_single_experiment(topo=topo, size=size, load=load, seed=seed)

    print("\nAll experiments finished. Results are in:", CSV_OUT)

if __name__ == "__main__":
    main()
