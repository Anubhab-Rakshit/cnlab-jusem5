import subprocess
import time
import sys
import os
import filecmp

def create_sample_file(filename="sample.txt", size_kb=10):
    text = "CDMA (Code Division Multiple Access) with Walsh Codes is amazing! This proves multiple access without collisions. "
    repetitions = (size_kb * 1024) // len(text)
    with open(filename, "w") as f:
        f.write(text * repetitions)
    print(f"Created {filename} ({os.path.getsize(filename)} bytes)")

def run_simulation(n_stations=4, noise=0.0):
    print(f"\n\033[96m=== Starting CDMA Simulation (N={n_stations}, Noise={noise}) ===\033[0m")
    
    # Cleanup old outputs
    import glob
    for f in glob.glob("output_st*.txt"):
        os.remove(f)
            
    create_sample_file()
    
    # Start channel
    channel = subprocess.Popen([sys.executable, "channel.py", "--stations", str(n_stations), "--noise", str(noise)])
    time.sleep(1) # Wait for channel to bind
    
    # Start stations
    stations = []
    for i in range(n_stations):
        # We start them simultaneously to ensure maximum stress on the channel
        cmd = [sys.executable, "station.py", "--file", "sample.txt"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL) # Hide stdout to keep console clean
        stations.append(proc)
        
    print(f"\033[93m[SIMULATE] {n_stations} stations are now simultaneously transmitting sample.txt over the SAME channel...\033[0m")
    
    # We estimate it will take a few seconds
    # Wait until output file size matches the sample file size
    target_size = os.path.getsize("sample.txt")
    start_time = time.time()
    
    while True:
        all_done = True
        for i in range(n_stations):
            for j in range(n_stations):
                if i == j: continue
                fname = f"output_st{i}_from_{j}.txt"
                if not os.path.exists(fname) or os.path.getsize(fname) < target_size:
                    all_done = False
                    break
            if not all_done: break
                
        if all_done or (time.time() - start_time) > 30:
            break
        time.sleep(0.5)
        
    print("\n\033[92m[SIMULATE] Transmission Complete! Terminating stations...\033[0m")
    for s in stations:
        s.terminate()
    channel.terminate()
    time.sleep(0.5)
    
    # Verification
    print("\n\033[96m=== Verifying Perfect Reconstruction ===\033[0m")
    all_perfect = True
    for i in range(n_stations):
        for j in range(n_stations):
            if i == j: continue
            fname = f"output_st{i}_from_{j}.txt"
            if not os.path.exists(fname):
                print(f"\033[91mStation {i} failed to receive from Station {j} (file missing)!\033[0m")
                all_perfect = False
                continue
                
            if filecmp.cmp("sample.txt", fname, shallow=False):
                print(f"\033[92m[PASS] Station {i} perfectly reconstructed Station {j}'s transmission!\033[0m")
            else:
                print(f"\033[91m[FAIL] Station {i}'s reconstruction of Station {j} had errors!\033[0m")
                all_perfect = False
            
    if all_perfect:
        print("\n\033[1;92mCDMA MAGIC CONFIRMED! All stations transmitted at the same time and reconstructed perfectly.\033[0m")
    else:
        print("\n\033[1;91mCDMA Reconstruction failed.\033[0m")

if __name__ == "__main__":
    print("Welcome to CDMA Test Suite!")
    print("1. Standard Stress Test (No Noise)")
    run_simulation(n_stations=4, noise=0.0)
    
    print("\n2. Noise Stress Test (AWGN Noise Sigma = 0.3)")
    run_simulation(n_stations=4, noise=0.3)
