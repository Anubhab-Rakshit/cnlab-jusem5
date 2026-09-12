import socket
import argparse
from utils import parse_frame, make_ack, channel_simulate

def recv_stop_and_wait(sock, total_frames=None, output_file=None):
    expected_seq = 0
    seq_mod = 2
    received_payloads = []
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            if total_frames is not None:
                break
            continue
            
        seq, payload, is_valid = parse_frame(data)
        
        if is_valid:
            if seq == expected_seq:
                print(f"[Receiver] Got frame {seq}")
                received_payloads.append(payload)
                expected_seq = (expected_seq + 1) % seq_mod
            else:
                print(f"[Receiver] Got duplicate frame {seq}")
            
            ack = make_ack(expected_seq)
            sock.sendto(ack, addr)
            print(f"[Receiver] Sent ACK {expected_seq}")
            
            if total_frames is not None and len(received_payloads) >= total_frames:
                break
        else:
            print("[Receiver] Corrupt frame dropped")

    if output_file and received_payloads:
        with open(output_file, 'wb') as f:
            f.write(b"".join(received_payloads))
    print(f"[Receiver] Transfer Finished. Received {len(received_payloads)} frames.")

def recv_go_back_n(sock, window_size, total_frames=None, output_file=None):
    seq_mod = 256
    expected_seq = 0
    received_payloads = []
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            if total_frames is not None:
                break
            continue
            
        seq, payload, is_valid = parse_frame(data)
        
        if is_valid:
            if seq == expected_seq:
                print(f"[Receiver] Got expected frame {seq}")
                received_payloads.append(payload)
                expected_seq = (expected_seq + 1) % seq_mod
            else:
                print(f"[Receiver] Got out-of-order frame {seq}, expected {expected_seq}")
            
            ack = make_ack(expected_seq)
            sock.sendto(ack, addr)
            print(f"[Receiver] Sent cumulative ACK {expected_seq}")
            
            if total_frames is not None and len(received_payloads) >= total_frames:
                break
        else:
            print("[Receiver] Corrupt frame dropped")

    if output_file and received_payloads:
        with open(output_file, 'wb') as f:
            f.write(b"".join(received_payloads))
    print(f"[Receiver] Transfer Finished. Received {len(received_payloads)} frames.")

def recv_selective_repeat(sock, window_size, total_frames=None, output_file=None):
    seq_mod = 256
    base = 0
    buffer = {}
    received_payloads = []
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            if total_frames is not None:
                break
            continue
            
        seq, payload, is_valid = parse_frame(data)
        
        if is_valid:
            print(f"[Receiver] Got frame {seq}")
            ack = make_ack(seq)
            sock.sendto(ack, addr)
            print(f"[Receiver] Sent ACK {seq}")
            
            dist = (seq - base) % seq_mod
            if dist < window_size:
                buffer[seq] = payload
                
                while base in buffer:
                    received_payloads.append(buffer[base])
                    del buffer[base]
                    base = (base + 1) % seq_mod
                print(f"[Receiver] Window base is now {base}")
                
            if total_frames is not None and len(received_payloads) >= total_frames:
                break
        else:
            print("[Receiver] Corrupt frame dropped")

    if output_file and received_payloads:
        with open(output_file, 'wb') as f:
            f.write(b"".join(received_payloads))
    print(f"[Receiver] Transfer Finished. Received {len(received_payloads)} frames.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', choices=['saw', 'gbn', 'sr'], default='saw')
    parser.add_argument('--window', type=int, default=4)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--timeout', type=float, default=None, help='Socket timeout in seconds')
    parser.add_argument('--total-frames', type=int, default=None, help='Exit after receiving N frames')
    parser.add_argument('--output', type=str, default=None, help='Output file to reconstruct transfer')
    args = parser.parse_args()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))
    if args.timeout:
        sock.settimeout(args.timeout)
    print(f"Receiver listening on {args.host}:{args.port} using protocol {args.protocol.upper()}")
    
    if args.protocol == 'saw':
        recv_stop_and_wait(sock, args.total_frames, args.output)
    elif args.protocol == 'gbn':
        recv_go_back_n(sock, args.window, args.total_frames, args.output)
    elif args.protocol == 'sr':
        recv_selective_repeat(sock, args.window, args.total_frames, args.output)
