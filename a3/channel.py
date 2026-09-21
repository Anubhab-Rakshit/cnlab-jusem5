import socket
import argparse
import time
import json
import threading

class Channel:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        
        # Mapping: station_id -> { 'start_time': float, 'collided': bool }
        self.active_transmissions = {}
        
        # Metrics
        self.total_collisions = 0
        self.total_success = 0
        
        self.lock = threading.Lock()
        self.running = True
        
    def get_state(self):
        with self.lock:
            # Cleanup stale transmissions (if a station crashed)
            now = time.time()
            stale_keys = [sid for sid, data in self.active_transmissions.items() if now - data['start_time'] > 1.0]
            for sid in stale_keys:
                del self.active_transmissions[sid]
                
            n = len(self.active_transmissions)
            if n == 0:
                return "IDLE"
            elif n == 1:
                return "BUSY"
            else:
                return "COLLISION"

    def handle_request(self, data, addr):
        msg = data.decode().strip().split()
        if not msg:
            return
        
        cmd = msg[0]
        
        if cmd == "SENSE":
            state = self.get_state()
            self.sock.sendto(state.encode(), addr)
            
        elif cmd == "TX_START":
            if len(msg) < 2: return
            station_id = msg[1]
            with self.lock:
                was_idle_or_busy = (len(self.active_transmissions) <= 1)
                self.active_transmissions[station_id] = {'start_time': time.time(), 'collided': False}
                
                # If adding this transmission caused a collision (now > 1 active)
                if len(self.active_transmissions) > 1:
                    # Mark all currently active as collided
                    for sid in self.active_transmissions:
                        if not self.active_transmissions[sid]['collided']:
                            self.active_transmissions[sid]['collided'] = True
                    self.total_collisions += 1
            self.sock.sendto("ACK".encode(), addr)
            
        elif cmd == "TX_END":
            if len(msg) < 2: return
            station_id = msg[1]
            status = "SUCCESS"
            with self.lock:
                if station_id in self.active_transmissions:
                    if self.active_transmissions[station_id]['collided']:
                        status = "COLLISION"
                    else:
                        self.total_success += 1
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
        print(f"[Channel] Started on {self.host}:{self.port}")
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
        print("[Channel] Stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    
    channel = Channel(args.host, args.port)
    channel.run()
