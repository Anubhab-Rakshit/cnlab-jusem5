import socket
import argparse
from utils import parse_frame, make_ack, channel_simulate

def recv_stop_and_wait(sock):
    expected_seq = 0
    seq_mod = 2
    
    while True:
        data, addr = sock.recvfrom(1024)
        seq, payload, is_valid = parse_frame(data)
        
        if is_valid:
            if seq == expected_seq:
                print(f"[Receiver] Got frame {seq}")
                expected_seq = (expected_seq + 1) % seq_mod
            else:
                print(f"[Receiver] Got duplicate frame {seq}")
            
            ack = make_ack(expected_seq)
            sock.sendto(ack, addr)
            print(f"[Receiver] Sent ACK {expected_seq}")
        else:
            print("[Receiver] Corrupt frame dropped")

def recv_go_back_n(sock, window_size):
    seq_mod = 256
    expected_seq = 0
    
    while True:
        data, addr = sock.recvfrom(1024)
        seq, payload, is_valid = parse_frame(data)
        
        if is_valid:
            if seq == expected_seq:
                print(f"[Receiver] Got expected frame {seq}")
                expected_seq = (expected_seq + 1) % seq_mod
            else:
                print(f"[Receiver] Got out-of-order frame {seq}, expected {expected_seq}")
            
            # Send cumulative ACK for next expected seq
            ack = make_ack(expected_seq)
            sock.sendto(ack, addr)
            print(f"[Receiver] Sent cumulative ACK {expected_seq}")
        else:
            print("[Receiver] Corrupt frame dropped")

def recv_selective_repeat(sock, window_size):
    seq_mod = 256
    base = 0
    buffer = {}
    
    while True:
        data, addr = sock.recvfrom(1024)
        seq, payload, is_valid = parse_frame(data)
        
        if is_valid:
            print(f"[Receiver] Got frame {seq}")
            # ACK the received frame directly (Independent ACK)
            ack = make_ack(seq)
            sock.sendto(ack, addr)
            print(f"[Receiver] Sent ACK {seq}")
            
            # Determine if seq is within current window
            # using modular arithmetic distance
            dist = (seq - base) % seq_mod
            if dist < window_size:
                buffer[seq] = payload
                
                # Advance window if base is in buffer
                while base in buffer:
                    del buffer[base]
                    base = (base + 1) % seq_mod
                print(f"[Receiver] Window base is now {base}")
        else:
            print("[Receiver] Corrupt frame dropped")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', choices=['saw', 'gbn', 'sr'], default='saw')
    parser.add_argument('--window', type=int, default=4)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))
    print(f"Receiver listening on {args.host}:{args.port} using protocol {args.protocol.upper()}")
    
    if args.protocol == 'saw':
        recv_stop_and_wait(sock)
    elif args.protocol == 'gbn':
        recv_go_back_n(sock, args.window)
    elif args.protocol == 'sr':
        recv_selective_repeat(sock, args.window)
