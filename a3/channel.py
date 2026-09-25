import socket
import argparse
import time
import json
import threading
import sys
import os
from datetime import datetime

# Import framing parser from a2 if available
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'a2')))
try:
    from utils import parse_frame
except Exception:
    parse_frame = None

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

class Channel:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        self.sock.bind((self.host, self.port))
        
        # Mapping: station_id -> { 'start_time': float, 'collided': bool, 'pos': float, 'payload': str }
        self.active_transmissions = {}
        
        # Metrics
        self.total_collisions = 0
        self.total_success = 0
        
        self.lock = threading.Lock()
        self.running = True
        self.start_time = time.time()
        
        # Clear/Create trace log file
        with open("trace_log.txt", "w") as f:
            f.write(f"--- CSMA Channel Emulation Trace Started at {datetime.now()} ---\n")
            f.write(f"{'Time':<10} | {'Event':<12} | {'Details'}\n")
            f.write("-" * 80 + "\n")
            
    def log_event(self, event_type, message, color_code=""):
        elapsed = time.time() - self.start_time
        # Write formatted row to log file
        with open("trace_log.txt", "a") as f:
            f.write(f"[{elapsed:7.3f}s] | {event_type:<12} | {message}\n")
            
        # Live colored terminal output for all events
        if not color_code:
            if event_type == "COLLISION": color_code = Colors.RED
            elif event_type == "SUCCESS": color_code = Colors.GREEN
            elif event_type == "TX_START": color_code = Colors.CYAN
            elif event_type == "TX_ABORT": color_code = Colors.YELLOW
            else: color_code = Colors.RESET
            
        print(f"[{elapsed:7.3f}s] {color_code}[{event_type:<10}]{Colors.RESET} {message}")

    def decode_payload_preview(self, hex_payload):
        if not hex_payload or hex_payload == "EMPTY":
            return "EMPTY"
        try:
            raw_bytes = bytes.fromhex(hex_payload)
            if parse_frame:
                seq, payload_data, valid = parse_frame(raw_bytes)
                if valid:
                    clean_text = payload_data.decode(errors='replace').replace('\n', ' ')
                    if len(clean_text) > 40:
                        clean_text = clean_text[:37] + "..."
                    return f"[Seq: {seq}] \"{clean_text}\""
            # Fallback to direct ascii decode
            clean_text = raw_bytes.decode(errors='replace').replace('\n', ' ')
            if len(clean_text) > 40:
                clean_text = clean_text[:37] + "..."
            return f"\"{clean_text}\""
        except Exception:
            return f"Hex({hex_payload[:16]}...)"
        
    def get_state_with_propagation(self, sense_pos):
        with self.lock:
            # Cleanup stale transmissions
            now = time.time()
            stale_keys = [sid for sid, data in self.active_transmissions.items() if now - data['start_time'] > 1.0]
            for sid in stale_keys:
                del self.active_transmissions[sid]
                
            # Calculate how many signals have physically reached this position
            signal_speed = 50000.0  # simulated speed m/s
            active_signals = 0
            
            for sid, data in self.active_transmissions.items():
                distance = abs(sense_pos - data['pos'])
                propagation_time = distance / signal_speed
                if (now - data['start_time']) >= propagation_time:
                    active_signals += 1
                    
            if active_signals == 0:
                return "IDLE"
            elif active_signals == 1:
                return "BUSY"
            else:
                return "COLLISION"

    def handle_request(self, data, addr):
        msg = data.decode().strip().split()
        if not msg:
            return
        
        cmd = msg[0]
        
        if cmd == "SENSE":
            if len(msg) < 3: return
            sense_pos = float(msg[2])
            state = self.get_state_with_propagation(sense_pos)
            self.sock.sendto(state.encode(), addr)
            
        elif cmd == "TX_START":
            if len(msg) < 3: return
            station_id = msg[1]
            pos = float(msg[2])
            payload = " ".join(msg[3:]) if len(msg) > 3 else "EMPTY"
            preview = self.decode_payload_preview(payload)
            
            with self.lock:
                self.active_transmissions[station_id] = {
                    'start_time': time.time(),
                    'pos': pos,
                    'collided': False,
                    'payload': payload
                }
                
                # If adding this transmission caused a collision (now > 1 active globally on wire)
                if len(self.active_transmissions) > 1:
                    # Mark all currently active as collided
                    for sid in self.active_transmissions:
                        if not self.active_transmissions[sid]['collided']:
                            self.active_transmissions[sid]['collided'] = True
                    self.total_collisions += 1
                    active_ids = list(self.active_transmissions.keys())
                    self.log_event("COLLISION", f"Stations {active_ids} collided on wire! (Active signals interfered)", Colors.RED)
                else:
                    self.log_event("TX_START", f"Station {station_id:<4} (pos: {pos:6.1f}m) started transmitting: {preview}", Colors.CYAN)
            self.sock.sendto("ACK".encode(), addr)
            
        elif cmd == "TX_END":
            if len(msg) < 2: return
            station_id = msg[1]
            status = "SUCCESS"
            with self.lock:
                if station_id in self.active_transmissions:
                    if self.active_transmissions[station_id]['collided']:
                        status = "COLLISION"
                        self.log_event("TX_ABORT", f"Station {station_id:<4} aborted/ended due to collision.", Colors.YELLOW)
                    else:
                        self.total_success += 1
                        self.log_event("SUCCESS", f"Station {station_id:<4} transmission delivered cleanly.", Colors.GREEN)
                    del self.active_transmissions[station_id]
            self.sock.sendto(status.encode(), addr)
            
        elif cmd == "GET_METRICS":
            with self.lock:
                res = json.dumps({
                    "collisions": self.total_collisions,
                    "success": self.total_success
                })
            self.sock.sendto(res.encode(), addr)
            
        elif cmd == "STOP":
            self.running = False
            self.sock.sendto("ACK".encode(), addr)

    def run(self):
        print(f"{Colors.BOLD}{Colors.GREEN}[Channel] Online and listening on {self.host}:{self.port}{Colors.RESET}")
        print(f"[Channel] Emulating 1000m Shared Bus (Signal Speed: 50,000 m/s)")
        print("-" * 80)
        self.sock.settimeout(0.5)
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                self.handle_request(data, addr)
            except socket.timeout:
                pass
            except Exception as e:
                pass
        
        self.sock.close()
        print(f"{Colors.BOLD}{Colors.YELLOW}[Channel] Stopped. Total Success: {self.total_success}, Collisions: {self.total_collisions}{Colors.RESET}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    
    channel = Channel(args.host, args.port)
    channel.run()

