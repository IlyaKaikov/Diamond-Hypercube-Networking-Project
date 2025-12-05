import argparse
from importlib import import_module
import csv
import os

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.log import setLogLevel, info

from routing.utils import build_coord_maps, build_ports_map
from routing.xy_routing import build_xy_routes
from routing.dq_routing import build_dq_routes

from traffic.random_uniform import generate_uniform_pairs, generate_uniform_pairs_k
from traffic.iperf_traffic import (start_iperf3_background_flows, run_iperf3_single_flow,)

TOPO_MODULES = {"mesh":"topology.mesh_topology", "torus2d":"topology.torus_2d_topology", "dq":"topology.dq_topology",}

def build_topology(topo_name, r, d):
    if topo_name not in TOPO_MODULES:
        raise ValueError(f"Unknown topology '{topo_name}'")

    module_name = TOPO_MODULES[topo_name]
    mod = import_module(module_name)

    if not hasattr(mod, "topos"):
        raise RuntimeError(f"Module {module_name} has no 'topos' dict")

    topo_factories = getattr(mod, "topos")
    if topo_name not in topo_factories:
        raise RuntimeError(f"'topos' in {module_name} does not contain key '{topo_name}'")

    factory = topo_factories[topo_name]

    if topo_name in ("mesh", "torus2d"):
        topo = factory(r=r)
    elif topo_name == "dq":
        topo = factory(d=d)
    else:
        raise RuntimeError(f"Unhandled topology '{topo_name}'")

    return topo

def install_static_routes(net: Mininet, topo_name, d):
    info("*** Building coord maps for routing\n")
    switch_coord_map, host_coord_map = build_coord_maps(net)

    if topo_name in ("mesh", "torus2d"):
        is_torus = (topo_name == "torus2d")
        info(f"*** Building ports map for {'2D Torus' if is_torus else 'Mesh'}\n")
        ports = build_ports_map(switch_coord_map, host_coord_map, is_torus=is_torus)

        info("*** Installing X–Y static routes\n")
        build_xy_routes(ports, switch_coord_map, host_coord_map, is_torus=is_torus)

    elif topo_name == "dq":
        info("*** Installing DQ one-to-one static routes\n")
        build_dq_routes(switch_coord_map, host_coord_map, d=d)

    else:
        raise RuntimeError(f"Static routing not implemented for topo '{topo_name}'")

def pick_probe_hosts(net):
    if len(net.hosts) < 2:
        raise RuntimeError("Need at least 2 hosts to run a probe flow.")
    src = net.hosts[0]
    dst = net.hosts[-1]
    return src, dst

def append_result_to_csv(csv_path, row, fieldnames,):
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run a single probe flow under random uniform background traffic "
            "and measure its FCT. Optionally log results to CSV."
        )
    )
    parser.add_argument("--topo", choices=["mesh", "torus2d", "dq"], default="torus2d", help="Topology to use",)
    parser.add_argument("--r", type=int, default=3, help="Grid size (for mesh / torus2d). Default: 3",)
    parser.add_argument("--d", type=int, default=2, help="Dimension (for dq). Default: 2",)
    parser.add_argument("--seed", type=int, default=42, help="Random seed for background pair generation.",)
    parser.add_argument("--bg-duration", type=int, default=10, help="Duration (seconds) for each background iperf3 flow. Default: 10.",)
    parser.add_argument("--probe-megabytes", type=float, default=50.0, help="Size of the probe flow in MB (default: 50 MB).",)
    parser.add_argument("--bg-base-port", type=int, default=5000, help="Base port for background iperf3 flows. Default: 5000.",)
    parser.add_argument("--probe-port", type=int, default=6000, help="TCP port for probe iperf3 flow. Default: 6000.",)
    parser.add_argument("--bg-multiplier", type=int, default=1,
        help="How many random destinations each host should have (k flows per host). "
             "Total BG flows ~= num_hosts * bg_multiplier.",)
    parser.add_argument("--bg-parallel-streams", type=int, default=1, help="Number of parallel TCP streams per BG flow (iperf3 -P N).",)
    parser.add_argument( "--csv-out", type=str, default=None, help="If set, append a CSV row with this run's results to the given file path.",)

    args = parser.parse_args()
    setLogLevel("info")

    info(f"*** Building topology '{args.topo}'\n")
    topo = build_topology(args.topo, r=args.r, d=args.d)

    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, autoSetMacs=True, autoStaticArp=True,)

    info("*** Starting network\n")
    net.start()

    try:
        info("*** Installing static routes\n")
        install_static_routes(net, topo_name=args.topo, d=args.d)

        info("*** Running pingAll() to verify connectivity\n")
        net.pingAll()

        if args.bg_multiplier <= 1:
            info("*** Generating background random uniform pairs (one dest per host)\n")
            bg_pairs = generate_uniform_pairs(
                net.hosts, seed=args.seed, allow_self=False
            )
        else:
            info(
                f"*** Generating background random uniform pairs: "
                f"{args.bg_multiplier} flows per host\n"
            )
            bg_pairs = generate_uniform_pairs_k(
                net.hosts,
                k=args.bg_multiplier,
                seed=args.seed,
                allow_self=False,
            )

        for src, dst in bg_pairs:
            info(f"    BG: {src.name} -> {dst.name}\n")
        
        bg_num_flows = len(bg_pairs)
        bg_total_streams = bg_num_flows * max(1, args.bg_parallel_streams)

        info(
            f"*** Starting background iperf3 flows: {len(bg_pairs)} flows, "
            f"duration={args.bg_duration}s\n"
        )
        bg_procs = start_iperf3_background_flows(bg_pairs, duration=args.bg_duration, base_port=args.bg_base_port, iperf_cmd="iperf3", parallel_streams=args.bg_parallel_streams,)

        src_probe, dst_probe = pick_probe_hosts(net)
        info(
            f"*** Probe flow under load: {src_probe.name} ({src_probe.IP()}) "
            f"-> {dst_probe.name} ({dst_probe.IP()})\n"
        )

        nbytes = int(args.probe_megabytes * 1024 * 1024)
        info(
            f"*** Starting iperf3 probe of {args.probe_megabytes} MB "
            f"(nbytes={nbytes}) on port {args.probe_port}\n"
        )

        probe_result = run_iperf3_single_flow(src_probe, dst_probe, nbytes=nbytes, port=args.probe_port, iperf_cmd="iperf3",)

        info("*** Probe flow completed under background load\n")
        info(f"    Summary: {probe_result['summary']}\n")
        if probe_result["fct_sec"] is not None:
            info(f"    Estimated FCT: {probe_result['fct_sec']:.4f} seconds\n")
        else:
            info("    FCT could not be parsed from summary\n")

        info("*** Waiting for background flows to finish\n")
        for proc in bg_procs.get("clients", []):
            try:
                proc.wait(timeout=args.bg_duration + 5)
            except Exception:
                pass

        info("*** Experiment finished\n")

        if args.csv_out is not None:
            info(f"*** Writing results to CSV: {args.csv_out}\n")

            fieldnames = ["topology", "r", "d", "num_hosts", "bg_num_flows", "bg_multiplier", "bg_parallel_streams", "bg_total_streams", "bg_duration_sec", "bg_seed", "probe_megabytes", "probe_fct_sec", "probe_summary",]

            row = {
                "topology": args.topo,
                "r": args.r if args.topo in ("mesh", "torus2d") else "",
                "d": args.d if args.topo == "dq" else "",
                "num_hosts": len(net.hosts),
                "bg_num_flows": bg_num_flows,
                "bg_multiplier": args.bg_multiplier,
                "bg_parallel_streams": args.bg_parallel_streams,
                "bg_total_streams": bg_total_streams,
                "bg_duration_sec": args.bg_duration,
                "bg_seed": args.seed,
                "probe_megabytes": args.probe_megabytes,
                "probe_fct_sec": (
                    probe_result["fct_sec"]
                    if probe_result["fct_sec"] is not None
                    else ""
                ),
                "probe_summary": probe_result["summary"],
            }

            append_result_to_csv(args.csv_out, row, fieldnames)

    finally:
        info("*** Stopping network\n")
        net.stop()

if __name__ == "__main__":
    main()
