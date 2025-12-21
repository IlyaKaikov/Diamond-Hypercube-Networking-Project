import time
import subprocess

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

def start_iperf3_server(dst, port: int, iperf_cmd: str = "iperf3", one_off: bool = False):
    one_off_flag = " -1" if one_off else ""
    server_cmd = f"{iperf_cmd} -s -p {port}{one_off_flag}"
    return dst.popen(server_cmd, shell=True)

def run_iperf3_client(src, dst_ip: str, port: int, nbytes: int, iperf_cmd: str = "iperf3", parallel_streams: int = 1, retries: int = 5, retry_delay_sec: float = 0.05,):
    last = {"stdout": "", "stderr": "", "summary": "", "fct_sec": None}
    for attempt in range(retries):
        client_cmd = f"{iperf_cmd} -c {dst_ip} -p {port} -n {nbytes}"
        if parallel_streams and parallel_streams > 1:
            client_cmd += f" -P {parallel_streams}"

        proc = src.popen(client_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_bytes, stderr_bytes = proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="ignore") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="ignore") if stderr_bytes else ""
        summary_line = parse_iperf3_summary(stdout)
        fct = extract_fct_from_summary(summary_line) if summary_line else None
        last = {"stdout": stdout, "stderr": stderr, "summary": summary_line or "", "fct_sec": fct}

        if proc.returncode == 0 and fct is not None:
            return last

        if attempt < retries - 1:
            time.sleep(retry_delay_sec)

    return last

def run_iperf3_single_flow(src, dst, nbytes: int = 100 * 1024 * 1024, port: int = 5000, iperf_cmd: str = "iperf3", parallel_streams: int = 1,):
    server_proc = start_iperf3_server(dst, port=port, iperf_cmd=iperf_cmd, one_off=True)
    result = run_iperf3_client(src, dst_ip=dst.IP(), port=port, nbytes=nbytes, iperf_cmd=iperf_cmd, parallel_streams=parallel_streams,)
    try:
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
    except Exception:
        pass
    return result

def start_iperf3_background_flows(pairs, duration = 10, base_port = 5000, iperf_cmd = "iperf3", parallel_streams = 1,):
    procs = {"servers": [], "clients": []}
    if not pairs:
        return procs

    for idx, (src, dst) in enumerate(pairs):
        port = base_port + idx
        server_proc = start_iperf3_server(dst, port=port, iperf_cmd=iperf_cmd, one_off=True)
        procs["servers"].append(server_proc)

    time.sleep(0.5)
    for idx, (src, dst) in enumerate(pairs):
        port = base_port + idx
        dst_ip = dst.IP()
        client_cmd = f"{iperf_cmd} -c {dst_ip} -p {port} -t {duration}"
        if parallel_streams and parallel_streams > 1:
            client_cmd += f" -P {parallel_streams}"
            
        client_proc = src.popen(client_cmd, shell=True)
        procs["clients"].append(client_proc)

    return procs
