import time
import subprocess
from typing import Tuple, Dict

def parse_iperf3_summary(output):
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    for line in reversed(lines):
        if "sender" in line or "receiver" in line:
            return line
    return None

def extract_fct_from_summary(summary_line):
    if not summary_line:
        return None

    parts = summary_line.split()
    interval_token = None
    for token in parts:
        if "-" in token and token.replace(".", "").replace("-", "").isdigit():
            interval_token = token
            break

    if interval_token is None:
        if len(parts) > 2:
            interval_token = parts[2]
        else:
            return None

    try:
        start_str, end_str = interval_token.split("-")
        start = float(start_str)
        end = float(end_str)
        return max(0.0, end - start)
    except Exception:
        return None

def run_iperf3_round(net, pairs, duration = 5, base_port = 5000, iperf_cmd = "iperf3",):
    results: Dict[Tuple[str, str], Dict[str, str]] = {}

    if not pairs:
        return results

    for idx, (src, dst) in enumerate(pairs):
        port = base_port + idx
        server_cmd = f"{iperf_cmd} -s -p {port} -1"
        dst.popen(server_cmd, shell=True)

    time.sleep(0.3)
    client_procs = []
    for idx, (src, dst) in enumerate(pairs):
        port = base_port + idx
        dst_ip = dst.IP()
        client_cmd = f"{iperf_cmd} -c {dst_ip} -p {port} -t {duration}"
        proc = src.popen(client_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,)
        client_procs.append((src, dst, proc))

    for src, dst, proc in client_procs:
        stdout_bytes, stderr_bytes = proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="ignore") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="ignore") if stderr_bytes else ""

        summary_line = parse_iperf3_summary(stdout)
        key = (src.name, dst.name)
        results[key] = {"stdout": stdout, "stderr": stderr, "summary": summary_line or "",}

    return results

def run_iperf3_single_flow(src, dst, nbytes = 100 * 1024 * 1024, port = 5000, iperf_cmd = "iperf3",):
    server_cmd = f"{iperf_cmd} -s -p {port} -1"
    dst.popen(server_cmd, shell=True)

    time.sleep(0.3)
    dst_ip = dst.IP()
    client_cmd = f"{iperf_cmd} -c {dst_ip} -p {port} -n {nbytes}"
    proc = src.popen(client_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,)
    stdout_bytes, stderr_bytes = proc.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="ignore") if stdout_bytes else ""
    stderr = stderr_bytes.decode("utf-8", errors="ignore") if stderr_bytes else ""
    summary_line = parse_iperf3_summary(stdout)
    fct = extract_fct_from_summary(summary_line) if summary_line else None

    return {"stdout": stdout, "stderr": stderr, "summary": summary_line or "", "fct_sec": fct,}

def start_iperf3_background_flows(pairs, duration = 10, base_port = 5000, iperf_cmd = "iperf3", parallel_streams = 1,):
    procs = {"servers": [], "clients": []}

    if not pairs:
        return procs

    for idx, (src, dst) in enumerate(pairs):
        port = base_port + idx
        server_cmd = f"{iperf_cmd} -s -p {port} -1"
        server_proc = dst.popen(server_cmd, shell=True)
        procs["servers"].append(server_proc)

    time.sleep(0.3)
    for idx, (src, dst) in enumerate(pairs):
        port = base_port + idx
        dst_ip = dst.IP()
        client_cmd = f"{iperf_cmd} -c {dst_ip} -p {port} -t {duration}"
        if parallel_streams and parallel_streams > 1:
            client_cmd += f" -P {parallel_streams}"
            
        client_proc = src.popen(client_cmd, shell=True)
        procs["clients"].append(client_proc)

    return procs