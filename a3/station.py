import socket
import argparse
import time
import random
import sys
import os

# Import framing/CRC module from a2 (which uses a1 C++ bridge)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'a2')))
try:
    from utils import make_frame
except Exception:
    make_frame = None

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    \
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def load_file_chunks(filename, max_frames=None, chunk_size=46):
    """Reads a real file and breaks it into payload chunks."""
    resolved_path = None
    candidates = [
        filename,
        os.path.join(os.path.dirname(__file__), filename if filename else ""),
        os.path.join(os.path.dirname(__file__), "sample.txt"),
        os.path.join(os.path.dirname(__file__), "..", "sample.txt"),
        "sample.txt"
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.path.isfile(c):
            resolved_path = c
            break
            
    chunks = []
    if resolved_path:
        with open(resolved_path, "rb") as f:
            data = f.read()
        if len(data) == 0:
            data = b"Default fallback data for CSMA transmission."
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    else:
        # Fallback dummy chunks
        num = max_frames if max_frames else 5
        chunks = [f"DataChunk_{i+1}_From_Station".encode() for i in range(num)]
        
    # If max_frames specified, adjust chunk list
    if max_frames and max_frames > 0:
        if len(chunks) < max_frames:
            # Repeat chunks to fulfill max_frames requirement
            multiplier = (max_frames // len(chunks)) + 1
            chunks = (chunks * multiplier)[:max_frames]
        else:
            chunks = chunks[:max_frames]
            
    return chunks, resolved_path

class Station:
    def __init__(self, station_id, host, port, strategy, p, total_frames, distance, filename="sample.txt", payload_size=46):
        self.station_id = station_id
        self.channel_addr = (host, port)
        self.strategy = strategy
        self.p = p
        self.distance = distance
        
        # Load and chunk real file data
        self.chunks, self.filepath = load_file_chunks(filename, max_frames=total_frames, chunk_size=payload_size)
        self.total_frames = len(self.chunks)
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)
        
        self.slot_time = 0.01
        self.tx_time_base = 0.1  # Base frame duration
        self.max_backoff_attempts = 10
        
        self.collisions = 0
        self.successful_tx = 0
        self.start_time = 0
        self.end_time = 0
        
    def log(self, tag, message, color=Colors.RESET):
        print(f"{Colors.BOLD}[Station {self.station_id:<4}]{Colors.RESET} {color}[{tag:<10}]{Colors.RESET} {message}")
        
    def send_to_channel(self, msg):
        try:
            self.sock.sendto(msg.encode(), self.channel_addr)
            data, _ = self.sock.recvfrom(1024)
            return data.decode().strip()
        except socket.timeout:
            return "TIMEOUT"

    def get_frame_payload(self, seq_no, raw_chunk):
        if make_frame:
            # Encapsulate in 15B Ethernet header (Dest MAC, Src MAC, Length, Seq) + Payload + 4B CRC-32
            frame_bytes = make_frame(seq_no % 256, raw_chunk)
            return frame_bytes.hex()
        return raw_chunk.hex()

    def sense(self):
        return self.send_to_channel(f"SENSE {self.station_id} {self.distance}")
        
    def tx_start(self, payload_hex):
        return self.send_to_channel(f"TX_START {self.station_id} {self.distance} {payload_hex}")
        
    def tx_end(self):
        return self.send_to_channel(f"TX_END {self.station_id}")
        
    def backoff(self, attempt):
        k = min(attempt, self.max_backoff_attempts)
        r = random.randint(0, (2**k) - 1)
        wait_duration = r * self.slot_time
        self.log("BACKOFF", f"Collision #{attempt} (k={k}) -> Backing off for {wait_duration:.3f}s (r={r} slots)", Colors.YELLOW)
        time.sleep(wait_duration)
        
    def run(self):
        file_info = f"'{self.filepath}'" if self.filepath else "Generated Data"
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== Starting Station {self.station_id} ==={Colors.RESET}")
        print(f"Strategy: {self.strategy} | Pos: {self.distance}m | File: {file_info} ({self.total_frames} chunks)")
        print("-" * 75)
        
        self.start_time = time.time()
        frames_sent = 0
        
        while frames_sent < self.total_frames:
            chunk_data = self.chunks[frames_sent]
            chunk_preview = chunk_data.decode(errors='replace').replace('\n', ' ')
            if len(chunk_preview) > 35:
                chunk_preview = chunk_preview[:32] + "..."
                
            attempt = 0
            success = False
            
            while not success:
                # 1. CARRIER SENSING STAGE
                if self.strategy == "non-persistent":
                    state = self.sense()
                    if state in ["BUSY", "COLLISION"]:
                        self.log("SENSE", f"Frame {frames_sent+1}/{self.total_frames} -> Channel is {state}. Non-persistent backoff...", Colors.YELLOW)
                        self.backoff(attempt + 1)
                        continue
                    else:
                        self.log("SENSE", f"Frame {frames_sent+1}/{self.total_frames} -> Channel is IDLE. Preparing transmission.", Colors.GREEN)
                        
                elif self.strategy == "1-persistent":
                    self.log("SENSE", f"Frame {frames_sent+1}/{self.total_frames} -> 1-Persistent sensing...", Colors.BLUE)
                    while True:
                        state = self.sense()
                        if state == "IDLE":
                            break
                        time.sleep(self.slot_time)
                    self.log("SENSE", f"Frame {frames_sent+1}/{self.total_frames} -> Channel is IDLE. Transmitting immediately (p=1.0).", Colors.GREEN)
                        
                elif self.strategy == "p-persistent":
                    self.log("SENSE", f"Frame {frames_sent+1}/{self.total_frames} -> p-Persistent sensing (p={self.p})...", Colors.BLUE)
                    while True:
                        state = self.sense()
                        if state == "IDLE":
                            if random.random() <= self.p:
                                self.log("SENSE", f"Frame {frames_sent+1}/{self.total_frames} -> Channel is IDLE and passed p-test. Transmitting.", Colors.GREEN)
                                break
                            else:
                                time.sleep(self.slot_time)
                        else:
                            time.sleep(self.slot_time)
                            
                elif self.strategy == "csmacd":
                    # CSMA/CD: 1-persistent sensing before transmission
                    self.log("SENSE", f"Frame {frames_sent+1}/{self.total_frames} -> CSMA/CD sensing carrier...", Colors.BLUE)
                    while True:
                        state = self.sense()
                        if state == "IDLE":
                            break
                        time.sleep(self.slot_time)
                    self.log("SENSE", f"Frame {frames_sent+1}/{self.total_frames} -> Carrier IDLE. Initiating listen-while-talk transmission.", Colors.GREEN)
                
                # 2. TRANSMISSION STAGE
                current_tx_time = self.tx_time_base * random.uniform(0.5, 1.5)
                payload_hex = self.get_frame_payload(frames_sent, chunk_data)
                
                self.log("TX_START", f"Frame {frames_sent+1}/{self.total_frames} (Size: {len(chunk_data)}B) -> \"{chunk_preview}\"", Colors.CYAN)
                self.tx_start(payload_hex)
                
                # 3. COLLISION DETECTION / CONFIRMATION
                if self.strategy == "csmacd":
                    collision_detected = False
                    steps = max(1, int(current_tx_time / self.slot_time))
                    for _ in range(steps):
                        time.sleep(self.slot_time)
                        if self.sense() == "COLLISION":
                            collision_detected = True
                            break
                            
                    if collision_detected:
                        self.tx_end()  # Abort early!
                        self.collisions += 1
                        attempt += 1
                        self.log("COLLISION", f"Collision detected during transmission! Aborted early.", Colors.RED)
                        self.backoff(attempt)
                        continue
                    else:
                        res = self.tx_end()
                        if res == "COLLISION":
                            self.collisions += 1
                            attempt += 1
                            self.log("COLLISION", f"Collision occurred on channel! Retrying...", Colors.RED)
                            self.backoff(attempt)
                            continue
                        else:
                            success = True
                            self.log("SUCCESS", f"Frame {frames_sent+1}/{self.total_frames} delivered cleanly.", Colors.GREEN)
                else:
                    # Non-CD: transmit fully, then check result
                    time.sleep(current_tx_time)
                    res = self.tx_end()
                    
                    if res == "COLLISION":
                        self.collisions += 1
                        attempt += 1
                        self.log("COLLISION", f"Collision on channel during full frame transmission!", Colors.RED)
                        self.backoff(attempt)
                    else:
                        success = True
                        self.log("SUCCESS", f"Frame {frames_sent+1}/{self.total_frames} delivered cleanly.", Colors.GREEN)
            
            frames_sent += 1
            self.successful_tx += 1
            # Inter-frame gap
            time.sleep(self.slot_time * random.randint(1, 4))
            
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        delay = total_time / self.total_frames if self.total_frames > 0 else 0
        efficiency = self.total_frames / total_time if total_time > 0 else 0
        
        print("-" * 75)
        print(f"Station {self.station_id} finished. Frames: {self.total_frames}, Collisions: {self.collisions}, Avg Delay: {delay:.3f}s, Efficiency: {efficiency:.2f} frames/s")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=str, required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--strategy', choices=['non-persistent', '1-persistent', 'p-persistent', 'csmacd'], required=True)
    parser.add_argument('--p', type=float, default=0.5)
    parser.add_argument('--frames', type=int, default=None, help="Optional frame limit (default: send all chunks in file)")
    parser.add_argument('--distance', type=float, default=0.0)
    parser.add_argument('--file', type=str, default="sample.txt", help="Path to real file to chunk and transmit")
    parser.add_argument('--payload-size', type=int, default=46, help="Payload size per chunk (default: 46)")
    args = parser.parse_args()
    
    # clamp p between 0 and 1
    args.p = max(0.0, min(1.0, args.p))
    
    station = Station(
        station_id=args.id,
        host=args.host,
        port=args.port,
        strategy=args.strategy,
        p=args.p,
        total_frames=args.frames,
        distance=args.distance,
        filename=args.file,
        payload_size=getattr(args, 'payload_size', 46)
    )
    station.run()

