import argparse
import csv
import os
import time

from mininet.log import setLogLevel, info
from experiments.experiment_core import (TopologyConfig, create_and_start_network, install_static_routes, choose_default_probe_pair,)
from traffic.incast import generate_incast_pairs_n
from traffic.iperf_traffic import (start_iperf3_background_flows, start_iperf3_server, run_iperf3_client,)

def append_result_to_csv(path, row, fieldnames):
    file_exists = os.path.exists(path)
    with open(path, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def parse_args():
    p = argparse.ArgumentParser(description=("Runs probes under in-cast (many-to-one) background traffic, and outputs FCT results to a csv file."))
    p.add_argument("--topo", required=True, choices=["mesh", "torus2d", "dq"])
    p.add_argument("--r", type=int)
    p.add_argument("--d", type=int)
    p.add_argument("--bg-num-flows", type=int, required=True,) # Number of background flows (random src/dst pairs). Overrides --bg-multiplier
    p.add_argument("--bg-dst-seed", type=int, default=None,)
    p.add_argument("--bg-src-seed", type=int, default=None,)
    p.add_argument("--bg-allow-dst-as-source", action="store_true",)
    p.add_argument("--bg-parallel-streams", type=int, default=1,) # iperf3 -P value for background flows (parallel streams per flow)
    p.add_argument("--bg-duration", type=float, default=10.0)
    p.add_argument("--bg-warmup-sec", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=1,) # Can be used as default for bg seeds
    p.add_argument("--num-probes", type=int, default=20)
    p.add_argument("--probe-megabytes", type=float, default=10.0)
    p.add_argument("--probe-port", type=int, default=4000)
    p.add_argument("--iperf-cmd", default="iperf3")
    p.add_argument("--csv-out", default="results_incast_latency.csv")
    p.add_argument("--loglevel", default="info")
    return p.parse_args()

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
    bg_dst_seed = args.bg_dst_seed if args.bg_dst_seed is not None else args.seed
    bg_src_seed = args.bg_src_seed if args.bg_src_seed is not None else bg_dst_seed
    fieldnames = ["traffic_pattern","topology","r","d","num_hosts","bg_num_flows","bg_parallel_streams","bg_total_streams","bg_duration_sec",
                  "bg_warmup_sec","bg_dst_seed","bg_src_seed","bg_dst_host","probe_index","probe_megabytes","probe_fct_sec","probe_summary",]

    try:
        net = create_and_start_network(config)
        _, _ = install_static_routes(net, config)
        hosts = list(net.hosts)
        num_hosts = len(hosts)
        info(f"**** Network has {num_hosts} hosts ****\n")
        info(f"**** Generating in-cast background pairs: n={args.bg_num_flows}, dst_seed={bg_dst_seed}, src_seed={bg_src_seed} ****\n")

        bg_pairs, bg_dst = generate_incast_pairs_n(hosts, n=args.bg_num_flows, dst_seed=bg_dst_seed, src_seed=bg_src_seed, allow_dst_as_source=args.bg_allow_dst_as_source,)
        bg_num_flows = len(bg_pairs)
        bg_total_streams = bg_num_flows * max(1, args.bg_parallel_streams)
        bg_dst_name = getattr(bg_dst, "name", "") if bg_dst is not None else ""

        info(f"**** Starting {bg_num_flows} background flows (in-cast) -> {bg_dst_name} ****\n")
        bg_procs = start_iperf3_background_flows(bg_pairs, duration=args.bg_duration, iperf_cmd=args.iperf_cmd, parallel_streams=args.bg_parallel_streams,)

        if args.bg_warmup_sec and args.bg_warmup_sec > 0:
            info(f"**** Warming up for {args.bg_warmup_sec}s before probing ****\n")
            time.sleep(args.bg_warmup_sec)

        src, dst = choose_default_probe_pair(net, config)
        info(f"**** Probe pair: {src.name} -> {dst.name}, size={args.probe_megabytes} MB ****\n")
        probe_nbytes = int(args.probe_megabytes * 1024 * 1024)
        probe_server = start_iperf3_server(dst, port=args.probe_port, iperf_cmd=args.iperf_cmd, one_off=False)

        for probe_index in range(1, args.num_probes + 1):
            info(f"**** Starting probe {probe_index}/{args.num_probes} from {src.name} to {dst.name} ****\n")
            probe_result = run_iperf3_client(src, dst_ip=dst.IP(), port=args.probe_port, nbytes=probe_nbytes, iperf_cmd=args.iperf_cmd, parallel_streams=1,)
            fct = probe_result.get("fct_sec", None)
            summary = probe_result.get("summary", "")
            row = {"traffic_pattern": "incast", "topology": config.topo, "r": config.r if config.topo in ("mesh", "torus2d") else "", "d": config.d if config.topo == "dq" else "",
                "num_hosts": num_hosts,"bg_num_flows": bg_num_flows,"bg_parallel_streams": args.bg_parallel_streams,"bg_total_streams": bg_total_streams,
                "bg_duration_sec": args.bg_duration,"bg_warmup_sec": args.bg_warmup_sec,"bg_dst_seed": bg_dst_seed,"bg_src_seed": bg_src_seed,"bg_dst_host": bg_dst_name,
                "probe_index": probe_index,"probe_megabytes": args.probe_megabytes,"probe_fct_sec": fct if fct is not None else "","probe_summary": summary,}

            append_result_to_csv(args.csv_out, row, fieldnames)

        info("**** Finished all probes ****\n")

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
            info("**** Stopping network ****\n")
            net.stop()

if __name__ == "__main__":
    main()
