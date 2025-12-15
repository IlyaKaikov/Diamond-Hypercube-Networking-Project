import argparse
import csv
import os
import time

from mininet.log import setLogLevel, info
from experiments.experiment_core import (TopologyConfig, create_and_start_network, install_static_routes, choose_default_probe_pair,)
from traffic.random_uniform import (generate_uniform_pairs_k, generate_uniform_pairs_n,)
from traffic.iperf_traffic import (start_iperf3_background_flows, start_iperf3_server, run_iperf3_client,)

def append_result_to_csv(path, row, fieldnames):
    file_exists = os.path.exists(path)
    with open(path, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def parse_args():
    parser = argparse.ArgumentParser(description=("Run multiple one-to-one probe flows under random-uniform background traffic and record FCT samples."))
    parser.add_argument("--topo", required=True, choices=["mesh", "torus2d", "dq"],)
    parser.add_argument("--r", type=int,)
    parser.add_argument("--d", type=int,)
    parser.add_argument("--bg-num-flows", type=int, default=None, help="Number of background flows (random src/dst pairs). Overrides --bg-multiplier.")
    parser.add_argument("--bg-multiplier", type=int, default=1, help=("Flows per host (k). Ignored if --bg-num-flows is set."),)
    parser.add_argument("--bg-parallel-streams",type=int, default=1, help="iperf3 -P value for background flows (parallel streams per flow).",)
    parser.add_argument("--bg-duration", type=float, default=10.0,)
    parser.add_argument("--bg-warmup-sec", type=float, default=1.0,)
    parser.add_argument("--seed", type=int, default=1,)
    parser.add_argument("--num-probes", type=int, default=20, help="Number of probe flows to run sequentially under the same background load.",)
    parser.add_argument("--probe-megabytes", type=float, default=100.0, help="Probe flow size in megabytes (converted to iperf3 -n bytes).",)
    parser.add_argument("--probe-port", type=int, default=4000,help="TCP port for probe iperf3 flow (kept separate from background flows).",)
    parser.add_argument("--iperf-cmd", default="iperf3",)
    parser.add_argument("--csv-out", default="results_random_uniform_latency.csv",)
    parser.add_argument("--loglevel", default="info",)
    return parser.parse_args()

def build_topology_config(args) -> TopologyConfig:
    if args.topo in ("mesh", "torus2d") and args.r is None:
        raise SystemExit(f"Topology '{args.topo}' requires --r")
    if args.topo == "dq" and args.d is None:
        raise SystemExit("Topology 'dq' requires --d")

    config = TopologyConfig(topo=args.topo, r=args.r, d=args.d)
    config.validate()
    return config

def main():
    args = parse_args()
    setLogLevel(args.loglevel)
    config = build_topology_config(args)
    net = None
    bg_procs = {"servers": [], "clients": []}
    fieldnames = ["topology", "r", "d", "num_hosts", "bg_num_flows", "bg_multiplier", "bg_parallel_streams", "bg_total_streams", 
                  "bg_duration_sec", "bg_warmup_sec", "bg_seed", "probe_index", "probe_megabytes", "probe_fct_sec", "probe_summary",]

    try:
        net = create_and_start_network(config)
        switch_coord_map, host_coord_map = install_static_routes(net, config)
        hosts = list(net.hosts)
        num_hosts = len(hosts)
        info(f"*** Network has {num_hosts} hosts\n")
        info(f"*** Generating random-uniform pairs: k={args.bg_multiplier}, seed={args.seed}\n")

        if args.bg_num_flows is not None:
            bg_pairs = generate_uniform_pairs_n(hosts, n=args.bg_num_flows, seed=args.seed, allow_self=False)
        else:
            bg_pairs = generate_uniform_pairs_k(hosts, k=args.bg_multiplier, seed=args.seed, allow_self=False)
            
        bg_num_flows = len(bg_pairs)
        bg_total_streams = bg_num_flows * max(1, args.bg_parallel_streams)

        info(f"*** Starting {bg_num_flows} background flows ({bg_total_streams} total iperf3 streams) for {args.bg_duration}s\n")
        bg_procs = start_iperf3_background_flows(bg_pairs, duration=args.bg_duration, iperf_cmd=args.iperf_cmd, parallel_streams=args.bg_parallel_streams,)

        if args.bg_warmup_sec and args.bg_warmup_sec > 0:
            info(f"*** Warming up for {args.bg_warmup_sec}s before probing\n")
            time.sleep(args.bg_warmup_sec)

        src, dst = choose_default_probe_pair(net, config)
        info(f"*** Probe pair: {src.name} -> {dst.name}, size={args.probe_megabytes} MB\n")
        probe_nbytes = int(args.probe_megabytes * 1024 * 1024)

        probe_server = start_iperf3_server(dst, port=args.probe_port, iperf_cmd=args.iperf_cmd, one_off=False)

        for probe_index in range(1, args.num_probes + 1):
            info(f"*** Starting probe {probe_index}/{args.num_probes} from {src.name} to {dst.name}\n")
            probe_result = run_iperf3_client(src, dst_ip=dst.IP(), port=args.probe_port, nbytes=probe_nbytes, iperf_cmd=args.iperf_cmd, parallel_streams=1,)
            fct = probe_result.get("fct_sec", None)
            summary = probe_result.get("summary", "")
            row = {"topology": config.topo, "r": config.r if config.topo in ("mesh", "torus2d") else "", "d": config.d if config.topo == "dq" else "",
                "num_hosts": num_hosts, "bg_num_flows": bg_num_flows, "bg_multiplier": args.bg_multiplier, "bg_parallel_streams": args.bg_parallel_streams,
                "bg_total_streams": bg_total_streams, "bg_duration_sec": args.bg_duration, "bg_warmup_sec": args.bg_warmup_sec, "bg_seed": args.seed, "probe_index": probe_index,
                "probe_megabytes": args.probe_megabytes, "probe_fct_sec": fct if fct is not None else "", "probe_summary": summary,}

            append_result_to_csv(args.csv_out, row, fieldnames)

        info("*** Finished all probes\n")

    finally:
        try:
            if 'probe_server' in locals() and probe_server is not None:
                probe_server.terminate()
        except Exception:
            pass

        if bg_procs:
            for proc in bg_procs.get("clients", []):
                try:
                    proc.terminate()
                except Exception:
                    pass
            for proc in bg_procs.get("servers", []):
                try:
                    proc.terminate()
                except Exception:
                    pass

        if net is not None:
            info("*** Stopping network\n")
            net.stop()

if __name__ == "__main__":
    main()
