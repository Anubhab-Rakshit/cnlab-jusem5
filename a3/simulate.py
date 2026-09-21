import subprocess
import time
import sys
import json
import csv
import argparse

def run_simulation(strategy, n_stations, p=0.5, frames_per_station=5, port=8000):
    # Start channel
    channel_proc = subprocess.Popen([sys.executable, "channel.py", "--port", str(port)])
    time.sleep(0.5) # Wait for channel to bind
    
    # Start stations
    station_procs = []
    start_time = time.time()
    for i in range(n_stations):
        cmd = [
            sys.executable, "station.py",
            "--id", f"st_{i}",
            "--port", str(port),
            "--strategy", strategy,
            "--p", str(p),
            "--frames", str(frames_per_station)
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        station_procs.append(proc)
        
    # Wait for all stations to finish and collect their outputs
    total_delay = 0
    total_station_collisions = 0
    
    for i, proc in enumerate(station_procs):
        stdout, _ = proc.communicate()
        print(f"\033[94m[PROGRESS]\033[0m Station {i+1}/{n_stations} completed.")
        # Parse stdout: Station st_X finished. Frames: 5, Collisions: 2, Avg Delay: 0.123s
        for line in stdout.splitlines():
            if "Avg Delay:" in line:
                parts = line.split(",")
                col_part = parts[1].split(":")[1].strip()
                delay_part = parts[2].split(":")[1].strip().replace("s", "")
                total_station_collisions += int(col_part)
                total_delay += float(delay_part)
                
    end_time = time.time()
    total_time = end_time - start_time
    
    # We can compute throughput based on how much time was spent successfully transmitting
    tx_time_per_frame = 0.1
    total_frames = n_stations * frames_per_station
    successful_tx_time = total_frames * tx_time_per_frame
    throughput = successful_tx_time / total_time if total_time > 0 else 0
    
    avg_delay = total_delay / n_stations if n_stations > 0 else 0
    
    # Stop channel
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Get channel metrics first
    sock.sendto("GET_METRICS".encode(), ("127.0.0.1", port))
    try:
        sock.settimeout(2.0)
        data, _ = sock.recvfrom(1024)
        channel_metrics = json.loads(data.decode())
        channel_collisions = channel_metrics.get("collisions", 0)
    except:
        channel_collisions = total_station_collisions # Fallback
        
    sock.sendto("STOP".encode(), ("127.0.0.1", port))
    channel_proc.wait()
    
    return {
        "strategy": strategy,
        "N": n_stations,
        "p": p,
        "collisions": channel_collisions,
        "avg_delay": round(avg_delay, 4),
        "throughput": round(throughput, 4)
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='Run a quick simulation for testing')
    args = parser.parse_args()
    
    results = []
    
    # i) For p-persistent CSMA, plot metrics as functions of p (fixed N = 10)
    p_values = [0.1, 0.3, 0.5, 0.7, 0.9] if not args.quick else [0.3, 0.7]
    print("\n\033[1;36m=== PHASE 1: Simulating p-persistent with varying p (N=10) ===\033[0m")
    port = 8500
    for p in p_values:
        print(f"\n\033[1;33m>>> Running p-persistent, p={p}...\033[0m")
        res = run_simulation("p-persistent", n_stations=10, p=p, frames_per_station=3, port=port)
        results.append(res)
        port += 1
        
    # Find best p (the one with highest throughput)
    p_results = [r for r in results if r["strategy"] == "p-persistent"]
    best_p = max(p_results, key=lambda x: x["throughput"])["p"] if p_results else 0.5
    print(f"Best p found: {best_p}")
    
    # ii) For all schemes, plot metrics as functions of N
    schemes = ["non-persistent", "1-persistent", "p-persistent", "csmacd"]
    N_values = [2, 5, 10, 15, 20] if not args.quick else [2, 5]
    
    print("\n\033[1;36m=== PHASE 2: Simulating all schemes with varying N ===\033[0m")
    for strategy in schemes:
        for N in N_values:
            p_val = best_p if strategy == "p-persistent" else 0.5
            print(f"\n\033[1;33m>>> Running {strategy}, N={N}...\033[0m")
            res = run_simulation(strategy, n_stations=N, p=p_val, frames_per_station=3, port=port)
            results.append(res)
            port += 1

    # Save results
    with open("results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["strategy", "N", "p", "collisions", "avg_delay", "throughput"])
        writer.writeheader()
        writer.writerows(results)
        
    print("\nSimulation complete. Results saved to results.csv.")
    print("Run `python visualize.py` to generate the plots.")

if __name__ == "__main__":
    main()
