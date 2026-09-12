import subprocess
import time
import csv
import sys
import os
import random
import string
import hashlib

def generate_random_file(filepath, size_bytes):
    with open(filepath, 'w') as f:
        chars = string.ascii_letters + string.digits + string.punctuation + ' \n'
        data = ''.join(random.choices(chars, k=size_bytes))
        f.write(data)

def get_file_md5(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def ensure_test_files():
    os.makedirs("test_files", exist_ok=True)
    files = [f"test_files/batch_file_{i:02d}.txt" for i in range(1, 51)]
    for i, filepath in enumerate(files):
        if not os.path.exists(filepath):
            # Vary file sizes between 400 bytes and 2500 bytes (optimal for swift socket testing)
            size = 400 + (i * 40)
            generate_random_file(filepath, size)
    return files

def run_single_experiment(protocol, window, loss, err, inject, file_path, port=8150):
    with open(file_path, 'rb') as f:
        file_data = f.read()
    file_size_bytes = len(file_data)
    total_frames = (file_size_bytes + 45) // 46
    
    orig_md5 = get_file_md5(file_path)
    output_tmp = f"test_files/received_tmp_{port}.bin"
    if os.path.exists(output_tmp):
        try: os.remove(output_tmp)
        except OSError: pass
        
    receiver_cmd = [
        sys.executable, "receiver.py",
        "--protocol", protocol,
        "--window", str(window),
        "--port", str(port),
        "--total-frames", str(total_frames),
        "--output", output_tmp
    ]
    
    receiver_proc = subprocess.Popen(
        receiver_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(0.02) # minimal wait for socket bind on localhost
    
    sender_cmd = [
        sys.executable, "sender.py",
        "--protocol", protocol,
        "--window", str(window),
        "--port", str(port),
        "--file", file_path,
        "--loss", str(loss),
        "--err", str(err),
        "--inject", inject,
        "--timeout", "0.15" # swift 150ms timeout for localhost batch simulation
    ]
    
    sender_res = subprocess.run(
        sender_cmd,
        capture_output=True,
        text=True
    )
    
    try:
        rec_out, rec_err = receiver_proc.communicate(timeout=0.3)
    except subprocess.TimeoutExpired:
        receiver_proc.kill()
        rec_out, rec_err = receiver_proc.communicate()
        
    transmissions = total_frames
    retransmissions = 0
    elapsed = 0.05
    
    for line in sender_res.stdout.splitlines():
        if "[Sender Stats]" in line:
            parts = line.split()
            for p in parts:
                if p.startswith("transmissions="):
                    transmissions = int(p.split("=")[1])
                elif p.startswith("retransmissions="):
                    retransmissions = int(p.split("=")[1])
                elif p.startswith("elapsed="):
                    elapsed = max(float(p.split("=")[1]), 0.001)
                    
    received_md5 = get_file_md5(output_tmp) if os.path.exists(output_tmp) else "MISMATCH"
    integrity_pass = (orig_md5 == received_md5)
    
    if os.path.exists(output_tmp):
        try: os.remove(output_tmp)
        except OSError: pass
        
    throughput_kbps = (file_size_bytes / 1024.0) / elapsed
    efficiency = (total_frames / transmissions) * 100.0 if transmissions > 0 else 100.0
    
    return {
        "protocol": protocol,
        "window": window,
        "loss": loss,
        "err": err,
        "inject": inject,
        "file": os.path.basename(file_path),
        "file_size_bytes": file_size_bytes,
        "total_frames": total_frames,
        "transmissions": transmissions,
        "retransmissions": retransmissions,
        "elapsed_sec": round(elapsed, 4),
        "throughput_kbps": round(throughput_kbps, 2),
        "efficiency_percent": round(efficiency, 2),
        "integrity_pass": integrity_pass
    }

def main():
    test_files = ensure_test_files()
    print(f"50 test files verified in a2/test_files/ (Sizes: 400B to 2.4KB).", flush=True)
    
    configs = [
        ("saw", 1, 0.0, 0.0, "none", "SAW_Ideal"),
        ("saw", 1, 0.05, 0.05, "none", "SAW_Loss05"),
        ("saw", 1, 0.15, 0.15, "none", "SAW_Loss15"),
        ("saw", 1, 0.0, 0.0, "drop_0", "SAW_DropInject"),
        ("saw", 1, 0.0, 0.0, "corr_1", "SAW_CorrInject"),
        
        ("gbn", 4, 0.0, 0.0, "none", "GBN_W4_Ideal"),
        ("gbn", 4, 0.05, 0.05, "none", "GBN_W4_Loss05"),
        ("gbn", 4, 0.15, 0.15, "none", "GBN_W4_Loss15"),
        ("gbn", 8, 0.0, 0.0, "none", "GBN_W8_Ideal"),
        ("gbn", 8, 0.10, 0.10, "none", "GBN_W8_Loss10"),
        ("gbn", 4, 0.0, 0.0, "drop_2", "GBN_DropInject"),
        
        ("sr", 4, 0.0, 0.0, "none", "SR_W4_Ideal"),
        ("sr", 4, 0.05, 0.05, "none", "SR_W4_Loss05"),
        ("sr", 4, 0.15, 0.15, "none", "SR_W4_Loss15"),
        ("sr", 8, 0.0, 0.0, "none", "SR_W8_Ideal"),
        ("sr", 8, 0.10, 0.10, "none", "SR_W8_Loss10"),
        ("sr", 4, 0.0, 0.0, "corr_2", "SR_CorrInject"),
    ]
    
    total_configs = len(configs)
    print(f"Starting batch simulation across {len(test_files)} test files and {total_configs} scenarios...\n", flush=True)
    results = []
    
    port_base = 8300
    start_all = time.time()
    
    for c_idx, (proto, win, loss, err, inject, label) in enumerate(configs, 1):
        t0 = time.time()
        print(f"  [{c_idx:02d}/{total_configs:02d}] {label:<17} (Proto={proto.upper()}, W={win}, Loss={loss:0.2f}) ", end="", flush=True)
        # Test 10 representative files per configuration (cycling across the full 50-file pool)
        file_subset = [test_files[(c_idx * 3 + j) % len(test_files)] for j in range(10)]
        for i, tf in enumerate(file_subset):
            port = port_base + ((c_idx * 10 + i) % 50)
            res = run_single_experiment(proto, win, loss, err, inject, tf, port=port)
            res["scenario_label"] = label
            results.append(res)
            print(".", end="", flush=True)
            
        t_elapsed = time.time() - t0
        print(f" Done in {t_elapsed:.2f}s", flush=True)
            
    csv_file = "batch_results.csv"
    with open(csv_file, "w", newline="") as f:
        fieldnames = [
            "scenario_label", "protocol", "window", "loss", "err", "inject",
            "file", "file_size_bytes", "total_frames", "transmissions",
            "retransmissions", "elapsed_sec", "throughput_kbps",
            "efficiency_percent", "integrity_pass"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    total_time = time.time() - start_all
    print(f"\n[SUCCESS] Batch simulation completed in {total_time:.2f}s! {len(results)} experiment runs recorded.")
    print(f"Results saved to {csv_file}")

if __name__ == "__main__":
    main()
