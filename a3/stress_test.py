import os
import subprocess
import random
import csv
import pandas as pd
import matplotlib.pyplot as plt
import time
import sys

def run_stress_test():
    print("\033[1;36m=== STARTING AUTOMATED STRESS TEST (50 ITERATIONS) ===\033[0m")
    strategies = ["non-persistent", "1-persistent", "p-persistent", "csmacd"]
    
    os.makedirs("test_logs", exist_ok=True)
    results = []
    
    for i in range(1, 51):
        strategy = random.choice(strategies)
        N = random.randint(2, 25)
        p = round(random.uniform(0.1, 0.9), 2)
        frames = random.randint(2, 5)
        
        print(f"\r\033[94m[PROGRESS]\033[0m Running iteration {i}/50 (Strategy: {strategy}, N: {N})...", end="")
        sys.stdout.flush()
        
        # We will use the existing simulate.py logic by importing it, or just calling it.
        # However, simulate.py is hardcoded. It's better to just call channel and stations directly here.
        port = 9000 + i
        
        channel_proc = subprocess.Popen([sys.executable, "channel.py", "--port", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.2) # let channel start
        
        start_time = time.time()
        station_procs = []
        for j in range(N):
            cmd = [sys.executable, "station.py", "--id", f"st_{j}", "--port", str(port), "--strategy", strategy, "--p", str(p), "--frames", str(frames)]
            sproc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            station_procs.append(sproc)
            
        total_delay = 0
        total_collisions = 0
        for sproc in station_procs:
            stdout, _ = sproc.communicate()
            for line in stdout.splitlines():
                if "Avg Delay:" in line:
                    parts = line.split(",")
                    col_part = parts[1].split(":")[1].strip()
                    delay_part = parts[2].split(":")[1].strip().replace("s", "")
                    total_collisions += int(col_part)
                    total_delay += float(delay_part)
                    
        total_time = time.time() - start_time
        
        # Stop channel
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto("STOP".encode(), ("127.0.0.1", port))
        channel_proc.wait()
        
        # Rename the trace_log.txt to our junk test file
        junk_file = f"test_logs/iteration_{i:02d}_{strategy}_N{N}.txt"
        if os.path.exists("trace_log.txt"):
            os.rename("trace_log.txt", junk_file)
            
        throughput = (N * frames * 0.1) / total_time if total_time > 0 else 0
        avg_delay = total_delay / N if N > 0 else 0
        
        results.append({
            "iteration": i,
            "strategy": strategy,
            "N": N,
            "p": p,
            "frames_per_station": frames,
            "total_collisions": total_collisions,
            "avg_delay": avg_delay,
            "throughput": throughput,
            "log_file": junk_file
        })
        
    print("\n\033[1;32m=== STRESS TEST COMPLETE ===\033[0m")
    
    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv("stress_test_results.csv", index=False)
    
    # Process nicely and create visualizations
    plt.figure(figsize=(18, 6))
    
    # Plot 1: Collisions vs N (Scatter)
    plt.subplot(1, 3, 1)
    for strat in strategies:
        subset = df[df['strategy'] == strat]
        plt.scatter(subset['N'], subset['total_collisions'], label=strat, alpha=0.7, s=100)
    plt.title('Stress Test: Collisions vs Network Size')
    plt.xlabel('Number of Stations (N)')
    plt.ylabel('Total Collisions')
    plt.legend()
    plt.grid(True)
    
    # Plot 2: Delay vs N
    plt.subplot(1, 3, 2)
    for strat in strategies:
        subset = df[df['strategy'] == strat]
        plt.scatter(subset['N'], subset['avg_delay'], label=strat, alpha=0.7, s=100)
    plt.title('Stress Test: Avg Delay vs Network Size')
    plt.xlabel('Number of Stations (N)')
    plt.ylabel('Average Delay (s)')
    plt.legend()
    plt.grid(True)
    
    # Plot 3: Throughput Boxplot by Strategy
    plt.subplot(1, 3, 3)
    data = [df[df['strategy'] == strat]['throughput'].values for strat in strategies]
    plt.boxplot(data, tick_labels=strategies)
    plt.title('Stress Test: Throughput Distribution')
    plt.ylabel('Throughput')
    plt.grid(True, axis='y')
    
    plt.tight_layout()
    plt.savefig('stress_test_visualization.png')
    print("Generated 50 junk text files in test_logs/!")
    print("Generated stress_test_results.csv and stress_test_visualization.png!")

if __name__ == "__main__":
    run_stress_test()
