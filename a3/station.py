import socket
import argparse
import time
import random

class Station:
    def __init__(self, station_id, host, port, strategy, p, total_frames):
        self.station_id = station_id
        self.channel_addr = (host, port)
        self.strategy = strategy
        self.p = p
        self.total_frames = total_frames
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)
        
        self.slot_time = 0.01
        self.tx_time_base = 0.1  # Base frame duration
        self.max_backoff_attempts = 10
        
        self.collisions = 0
        self.successful_tx = 0
        self.start_time = 0
        self.end_time = 0
        
    def send_to_channel(self, msg):
        try:
            self.sock.sendto(msg.encode(), self.channel_addr)
            data, _ = self.sock.recvfrom(1024)
            return data.decode().strip()
        except socket.timeout:
            return "TIMEOUT"

    def sense(self):
        return self.send_to_channel("SENSE")
        
    def tx_start(self):
        return self.send_to_channel(f"TX_START {self.station_id}")
        
    def tx_end(self):
        return self.send_to_channel(f"TX_END {self.station_id}")
        
    def backoff(self, attempt):
        k = min(attempt, self.max_backoff_attempts)
        r = random.randint(0, (2**k) - 1)
        time.sleep(r * self.slot_time)
        
    def run(self):
        self.start_time = time.time()
        frames_sent = 0
        
        while frames_sent < self.total_frames:
            attempt = 0
            success = False
            
            while not success:
                if self.strategy == "non-persistent":
                    state = self.sense()
                    if state in ["BUSY", "COLLISION"]:
                        self.backoff(attempt + 1)
                        continue
                        
                elif self.strategy == "1-persistent":
                    while True:
                        state = self.sense()
                        if state == "IDLE":
                            break
                        time.sleep(self.slot_time)
                        
                elif self.strategy == "p-persistent":
                    while True:
                        state = self.sense()
                        if state == "IDLE":
                            if random.random() <= self.p:
                                break
                            else:
                                time.sleep(self.slot_time)
                        else:
                            time.sleep(self.slot_time)
                            
                elif self.strategy == "csmacd":
                    # 1-persistent sensing
                    while True:
                        state = self.sense()
                        if state == "IDLE":
                            break
                        time.sleep(self.slot_time)
                
                # Transmit
                # Variable frame size (takes between 50% to 150% of base tx_time)
                current_tx_time = self.tx_time_base * random.uniform(0.5, 1.5)
                self.tx_start()
                
                if self.strategy == "csmacd":
                    # CSMA/CD: Transmit and sense for collision simultaneously
                    collision_detected = False
                    steps = int(current_tx_time / self.slot_time)
                    for _ in range(steps):
                        time.sleep(self.slot_time)
                        if self.sense() == "COLLISION":
                            collision_detected = True
                            break
                            
                    if collision_detected:
                        self.tx_end() # Abort
                        self.collisions += 1
                        attempt += 1
                        self.backoff(attempt)
                        continue
                    else:
                        res = self.tx_end()
                        if res == "COLLISION":
                            self.collisions += 1
                            attempt += 1
                            self.backoff(attempt)
                            continue
                        else:
                            success = True
                else:
                    # Non-CD: transmit fully, then check result
                    time.sleep(current_tx_time)
                    res = self.tx_end()
                    
                    if res == "COLLISION":
                        self.collisions += 1
                        attempt += 1
                        self.backoff(attempt)
                    else:
                        success = True
            
            frames_sent += 1
            self.successful_tx += 1
            # Brief delay before next frame
            time.sleep(self.slot_time * random.randint(1, 5))
            
        self.end_time = time.time()
        
        # Report metrics back to a collector if needed, but we can just print
        delay = (self.end_time - self.start_time) / self.total_frames if self.total_frames > 0 else 0
        print(f"Station {self.station_id} finished. Frames: {self.total_frames}, Collisions: {self.collisions}, Avg Delay: {delay:.3f}s")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=str, required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--strategy', choices=['non-persistent', '1-persistent', 'p-persistent', 'csmacd'], required=True)
    parser.add_argument('--p', type=float, default=0.5)
    parser.add_argument('--frames', type=int, default=10)
    args = parser.parse_args()
    
    # clamp p between 0 and 1
    args.p = max(0.0, min(1.0, args.p))
    
    station = Station(args.id, args.host, args.port, args.strategy, args.p, args.frames)
    station.run()
