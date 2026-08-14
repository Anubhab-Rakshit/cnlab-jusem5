import subprocess
import time
import csv
import sys
import os
import random
import string

def generate_random_file(filename, size_kb):
    with open(filename, 'w') as f:
        # Generate random text
        data = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation + ' \n', k=size_kb * 1024))
        f.write(data)

def compile_code():
    print("Compiling C++ code...")
    subprocess.run(["g++", "-std=c++17", "-O3", "receiver.cpp", "-o", "receiver"], check=True)
    subprocess.run(["g++", "-std=c++17", "-O3", "sender.cpp", "-o", "sender"], check=True)
    print("Compilation successful.")

def run_simulation(poly, error_type, files):
    print(f"Running batch simulation for Poly = {poly}, Error = {error_type}...")
    
    total_frames = 0
    crc_detect = 0
    checksum_detect = 0
    
    port = "6001"
    
    for file in files:
        receiver_proc = subprocess.Popen(
            ["./receiver", "--port", port],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(0.1) # Wait for listener
        
        sender_proc = subprocess.run(
            ["./sender", "--port", port, "--file", file, "--poly", poly, "--error", error_type],
            capture_output=True,
            text=True
        )
        
        out, err = receiver_proc.communicate(timeout=5)
        
        # Parse receiver output
        # checksum_accept: X
        # checksum_reject: X
        # crc_accept: X
        # crc_reject: X
        
        c_acc = c_rej = 0
        crc_acc = crc_rej = 0
        
        for line in out.splitlines():
            if "checksum_accept:" in line: c_acc = int(line.split(":")[1].strip())
            if "checksum_reject:" in line: c_rej = int(line.split(":")[1].strip())
            if "crc_accept:" in line: crc_acc = int(line.split(":")[1].strip())
            if "crc_reject:" in line: crc_rej = int(line.split(":")[1].strip())
                
        total_frames += (crc_acc + crc_rej)
        crc_detect += crc_rej
        checksum_detect += c_rej

    return {
        "poly": poly,
        "error_type": error_type,
        "total_frames": total_frames,
        "crc_detect": crc_detect,
        "checksum_detect": checksum_detect
    }

def main():
    compile_code()
    
    # Generate 50 random files for batch processing
    test_files = [f"batch_data{i}.txt" for i in range(1, 51)]
    for f in test_files:
        generate_random_file(f, size_kb=20) # 20 KB each, to give plenty of data
        
    polys = ["CRC-8", "CRC-10", "CRC-16", "CRC-32"]
    error_types = ["single", "two", "odd", "burst"]
    
    all_results = []
    
    # We will also collect the checksum data. Checksum is calculated 
    # regardless of the poly, so we can just average or use the data from any poly run.
    # To be perfectly accurate across the same data, we'll extract it simultaneously.
    
    for poly in polys:
        for et in error_types:
            res = run_simulation(poly, et, test_files)
            all_results.append(res)
            
    with open("batch_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["poly", "error_type", "total_frames", "crc_detect", "checksum_detect"])
        writer.writeheader()
        writer.writerows(all_results)
        
    print("Batch simulation complete. Results saved to batch_results.csv")

if __name__ == "__main__":
    main()
