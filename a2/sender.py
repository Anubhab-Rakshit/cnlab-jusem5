import socket
import argparse
import time
from utils import make_frame, parse_ack, channel_simulate

def read_data(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    # Chunk into 46 bytes payload
    return [data[i:i+46] for i in range(0, len(data), 46)]

def stop_and_wait(sock, dest, frames, timeout_val, loss, err, inject):
    seq_bits = 1
    seq_mod = 1 << seq_bits
    injected = set()
    
    for i, payload in enumerate(frames):
        seq = i % seq_mod
        frame = make_frame(seq, payload)
        
        while True:
            # Check for injections
            force_drop = (inject == f'drop_{seq}' and inject not in injected)
            force_err = (inject == f'corr_{seq}' and inject not in injected)
            if force_drop or force_err:
                injected.add(inject)
                print(f"[Sender] *** INJECTING ERROR: {inject} ***")
                
            # Simulate channel
            sim_frame = channel_simulate(frame, loss, err, max_delay=0.1, force_drop=force_drop, force_err=force_err)
            if sim_frame:
                sock.sendto(sim_frame, dest)
                print(f"[Sender] Sent frame {seq}")
            else:
                print(f"[Sender] Frame {seq} lost in channel")
            
            sock.settimeout(timeout_val)
            try:
                ack, _ = sock.recvfrom(1024)
                ack_seq, is_valid = parse_ack(ack)
                
                if inject == f'drop_ack_{ack_seq}' and inject not in injected:
                    injected.add(inject)
                    print(f"[Sender] *** INJECTING ERROR: {inject} ***")
                    raise socket.timeout
                    
                if is_valid and ack_seq == (seq + 1) % seq_mod:
                    print(f"[Sender] Got ACK {ack_seq}, moving to next")
                    break
                else:
                    print(f"[Sender] Invalid/wrong ACK {ack_seq if is_valid else 'corrupt'}")
            except socket.timeout:
                print(f"[Sender] Timeout for frame {seq}. Retransmitting...")

def go_back_n(sock, dest, frames, window_size, timeout_val, loss, err, inject):
    seq_mod = 256
    base = 0
    next_seq = 0
    num_frames = len(frames)
    timers = {}
    injected = set()
    
    sock.settimeout(0.1) # short polling
    
    while base < num_frames:
        # Send while within window
        while next_seq < base + window_size and next_seq < num_frames:
            seq = next_seq % seq_mod
            frame = make_frame(seq, frames[next_seq])
            
            force_drop = (inject == f'drop_{seq}' and inject not in injected)
            force_err = (inject == f'corr_{seq}' and inject not in injected)
            if force_drop or force_err:
                injected.add(inject)
                print(f"[Sender] *** INJECTING ERROR: {inject} ***")
                
            sim_frame = channel_simulate(frame, loss, err, max_delay=0.0, force_drop=force_drop, force_err=force_err)
            if sim_frame:
                sock.sendto(sim_frame, dest)
                print(f"[Sender] Sent frame {seq} (Index {next_seq})")
            else:
                print(f"[Sender] Frame {seq} lost")
            
            timers[next_seq] = time.time()
            next_seq += 1
            
        try:
            ack, _ = sock.recvfrom(1024)
            ack_seq, is_valid = parse_ack(ack)
            if inject == f'drop_ack_{ack_seq}' and inject not in injected:
                injected.add(inject)
                print(f"[Sender] *** INJECTING ERROR: {inject} ***")
                is_valid = False # Pretend it dropped
                
            if is_valid:
                print(f"[Sender] Got cumulative ACK {ack_seq}")
                # ACK is for the next expected sequence number
                # Map ack_seq back to window indices
                for i in range(base, next_seq):
                    if (i + 1) % seq_mod == ack_seq:
                        print(f"[Sender] Window advanced to {i + 1}")
                        for j in range(base, i + 1):
                            if j in timers: del timers[j]
                        base = i + 1
                        break
        except socket.timeout:
            pass
            
        # Check timeout for base
        if base in timers and (time.time() - timers[base]) > timeout_val:
            print(f"[Sender] Timeout! Go-Back-N from {base}")
            next_seq = base # Reset to base to resend

def selective_repeat(sock, dest, frames, window_size, timeout_val, loss, err, inject):
    seq_mod = 256
    base = 0
    next_seq = 0
    num_frames = len(frames)
    
    acked = [False] * num_frames
    timers = {}
    injected = set()
    
    sock.settimeout(0.1)
    
    while base < num_frames:
        # Send new frames in window
        while next_seq < base + window_size and next_seq < num_frames:
            seq = next_seq % seq_mod
            frame = make_frame(seq, frames[next_seq])
            force_drop = (inject == f'drop_{seq}' and inject not in injected)
            force_err = (inject == f'corr_{seq}' and inject not in injected)
            if force_drop or force_err:
                injected.add(inject)
                print(f"[Sender] *** INJECTING ERROR: {inject} ***")
                
            sim_frame = channel_simulate(frame, loss, err, max_delay=0.0, force_drop=force_drop, force_err=force_err)
            if sim_frame:
                sock.sendto(sim_frame, dest)
                print(f"[Sender] Sent frame {seq} (Index {next_seq})")
            timers[next_seq] = time.time()
            next_seq += 1
            
        # Check for ACKs
        try:
            ack, _ = sock.recvfrom(1024)
            ack_seq, is_valid = parse_ack(ack)
            
            if inject == f'drop_ack_{ack_seq}' and inject not in injected:
                injected.add(inject)
                print(f"[Sender] *** INJECTING ERROR: {inject} ***")
                is_valid = False
                
            if is_valid:
                print(f"[Sender] Got ACK {ack_seq}")
                for i in range(base, next_seq):
                    if i % seq_mod == ack_seq and not acked[i]:
                        acked[i] = True
                        if i in timers: del timers[i]
                        break
                
                # Advance base if possible
                while base < num_frames and acked[base]:
                    base += 1
        except socket.timeout:
            pass
            
        # Check individual timeouts
        for i in range(base, next_seq):
            if not acked[i] and i in timers and (time.time() - timers[i]) > timeout_val:
                print(f"[Sender] Timeout for frame {i % seq_mod}. Resending.")
                seq = i % seq_mod
                frame = make_frame(seq, frames[i])
                sim_frame = channel_simulate(frame, loss, err, max_delay=0.0)
                if sim_frame:
                    sock.sendto(sim_frame, dest)
                timers[i] = time.time()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', choices=['saw', 'gbn', 'sr'], default='saw')
    parser.add_argument('--file', default='sample.txt')
    parser.add_argument('--window', type=int, default=4)
    parser.add_argument('--timeout', type=float, default=2.0)
    parser.add_argument('--loss', type=float, default=0.1)
    parser.add_argument('--err', type=float, default=0.1)
    parser.add_argument('--inject', type=str, default='none', help='Deterministic injection e.g., drop_2, corr_3, drop_ack_1')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    
    # write sample text if doesn't exist
    import os
    if not os.path.exists(args.file):
        with open(args.file, 'w') as f:
            f.write("Hello World! This is a test file for CN assignment 2 flow control. " * 10)
            
    frames = read_data(args.file)
    print(f"Total frames to send: {len(frames)}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (args.host, args.port)
    
    if args.protocol == 'saw':
        stop_and_wait(sock, dest, frames, args.timeout, args.loss, args.err, args.inject)
    elif args.protocol == 'gbn':
        go_back_n(sock, dest, frames, args.window, args.timeout, args.loss, args.err, args.inject)
    elif args.protocol == 'sr':
        selective_repeat(sock, dest, frames, args.window, args.timeout, args.loss, args.err, args.inject)
        
    sock.close()
    print("Done!")
