import socket
import threading
import struct
import argparse
import sys
import numpy as np

def generate_walsh(n):
    if n == 1:
        return np.array([[1]])
    half = generate_walsh(n // 2)
    return np.vstack((np.hstack((half, half)), np.hstack((half, -half))))

class Channel:
    def __init__(self, port, max_stations, noise_level):
        self.port = port
        self.max_stations = max_stations
        
        # Find next power of 2 for Walsh matrix
        self.walsh_size = 1
        while self.walsh_size < max_stations:
            self.walsh_size *= 2
            
        self.noise_level = noise_level
        self.clients = []
        self.lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", port))
        self.server.listen(max_stations)
        self.barrier = threading.Barrier(max_stations)
        
        # Buffer to hold current round's data
        self.current_chips = [None] * max_stations
        
        print(f"\033[96m[CHANNEL] Started on port {port}. Waiting for {max_stations} stations...\033[0m")
        print(f"\033[90m[CHANNEL] Walsh Matrix size: {self.walsh_size}x{self.walsh_size}\033[0m")
        if noise_level > 0:
            print(f"\033[93m[CHANNEL] AWGN Noise enabled (sigma={noise_level})\033[0m")
            
    def handle_client(self, conn, addr, idx):
        # Send initial config: ID, Walsh size
        conn.sendall(struct.pack("!II", idx, self.walsh_size))
        
        try:
            while True:
                # Read payload length
                len_buf = conn.recv(4)
                if not len_buf: break
                msg_len = struct.unpack("!I", len_buf)[0]
                
                # Read payload
                data = b""
                while len(data) < msg_len:
                    packet = conn.recv(msg_len - len(data))
                    if not packet: break
                    data += packet
                if not data: break
                
                # Convert to numpy array of float32
                chips = np.frombuffer(data, dtype=np.float32)
                
                # Store for summing
                self.current_chips[idx] = chips
                
                # Wait for all stations to submit their chips
                self.barrier.wait()
                
                # Only station 0 performs the sum and broadcast to avoid duplicate work
                if idx == 0:
                    summed = np.zeros_like(chips)
                    for c in self.current_chips:
                        if c is not None:
                            summed += c
                            
                    # Add channel noise if configured
                    if self.noise_level > 0:
                        noise = np.random.normal(0, self.noise_level, summed.shape)
                        summed += noise
                        
                    self.summed_buffer = summed.tobytes()
                    
                    # Reset buffers for next round
                    for i in range(self.max_stations):
                        self.current_chips[i] = None
                        
                # Wait for station 0 to finish summing
                self.barrier.wait()
                
                # Send back the summed signal
                out_data = self.summed_buffer
                conn.sendall(struct.pack("!I", len(out_data)))
                conn.sendall(out_data)
                
        except Exception as e:
            print(f"\033[91m[CHANNEL] Station {idx} disconnected unexpectedly: {e}\033[0m")
        finally:
            conn.close()

    def run(self):
        try:
            for i in range(self.max_stations):
                conn, addr = self.server.accept()
                self.clients.append(conn)
                print(f"\033[92m[CHANNEL] Station {i} connected from {addr}\033[0m")
                threading.Thread(target=self.handle_client, args=(conn, addr, i), daemon=True).start()
            
            print("\033[96m[CHANNEL] All stations connected. CDMA Channel active.\033[0m")
            while True:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            print("\n\033[91m[CHANNEL] Shutting down...\033[0m")
            for c in self.clients: c.close()
            self.server.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--stations", type=int, default=4, help="Number of stations expected")
    parser.add_argument("--noise", type=float, default=0.0, help="AWGN standard deviation (e.g. 0.5)")
    args = parser.parse_args()
    
    Channel(args.port, args.stations, args.noise).run()
