import subprocess
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SizeConfig:
    label: str
    r: Optional[int]
    d: Optional[int]

@dataclass
class LoadConfig:
    label: str
    bg_num_flows: int
    bg_parallel_streams: int

SIZE_SETS: List[SizeConfig] = [SizeConfig(label="medium", r=14, d=5),]
LOAD_LEVELS: List[LoadConfig] = [LoadConfig(label="low", bg_num_flows=60, bg_parallel_streams=1),
                                   LoadConfig(label="low+", bg_num_flows=120, bg_parallel_streams=1),
                                   LoadConfig(label="medium", bg_num_flows=180, bg_parallel_streams=1),
                                   LoadConfig(label="medium+", bg_num_flows=240, bg_parallel_streams=1),]
TOPOLOGIES = ["dq"] # "mesh", "torus2d", "dq"
SEEDS = [1,2,3,4,5,6,7,8]
NUM_PROBES = 100
PROBE_MEGABYTES = 10.0
BG_DURATION = 2000.0
BG_WARMUP_SEC = 1
BG_DST_HOST: Optional[str] = "h15x1"
IPERF_CMD = "iperf3"
CSV_OUT = "results_incast_edgecase.csv"

def run_single_experiment(topo: str, size: SizeConfig, load: LoadConfig, seed: int):
    base_args: List[str] = ["python3","-m","experiments.incast_latency","--topo",topo,"--bg-num-flows",str(load.bg_num_flows),
                            "--bg-parallel-streams",str(load.bg_parallel_streams),"--bg-duration",str(BG_DURATION),
                            "--num-probes",str(NUM_PROBES),"--probe-megabytes",str(PROBE_MEGABYTES),
                            "--bg-warmup-sec",str(BG_WARMUP_SEC),"--seed",str(seed),"--iperf-cmd",IPERF_CMD,"--csv-out",CSV_OUT,"--loglevel","info",]

    if BG_DST_HOST:
        base_args.extend(["--bg-dst-host", BG_DST_HOST])

    if topo in ("mesh", "torus2d"):
        base_args.extend(["--r", str(size.r)])

    elif topo == "dq":
        base_args.extend(["--d", str(size.d)])

    else:
        raise ValueError(f"Unsupported topology '{topo}'")

    label = (f"topo={topo}, size={size.label}(r={size.r},d={size.d}), load={load.label}(bg_num_flows={load.bg_num_flows},P={load.bg_parallel_streams}), seed={seed}")
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
#   sudo python3 -m experiments.run_incast_grid
