import socket
import struct
import argparse
import sys
import threading
import queue
import time
import numpy as np

def generate_walsh(n):
    if n == 1:
        return np.array([[1]])
    half = generate_walsh(n // 2)
    return np.vstack((np.hstack((half, half)), np.hstack((half, -half))))

class Station:
    def __init__(self, host, port, file_path=None):
        self.host = host
        self.port = port
        self.file_path = file_path
        self.frame_size = 64 # bytes per frame
        self.q = queue.Queue()
        
        # Connect to channel
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"\033[93m[STATION] Connecting to CDMA Channel at {host}:{port}...\033[0m")
        self.sock.connect((host, port))
        
        # Receive setup info
        setup_data = self.sock.recv(8)
        self.idx, self.walsh_size = struct.unpack("!II", setup_data)
        
        self.walsh_matrix = generate_walsh(self.walsh_size)
        self.walsh_code = self.walsh_matrix[self.idx]
        
        print(f"\033[92m[STATION] Connected! Assigned ID: {self.idx}, Walsh Size: {self.walsh_size}\033[0m")
        print(f"\033[96m[STATION] My Walsh Code: {self.walsh_code}\033[0m")
        
        # Output buffers for file reconstruction
        self.output_files = {}

    def encode(self, data_bytes):
        N = self.walsh_size
        chips = np.zeros(self.frame_size * 8 * N, dtype=np.float32)
        
        if data_bytes:
            bits = np.unpackbits(np.frombuffer(data_bytes, dtype=np.uint8))
            mapped = np.where(bits == 0, -1, 1).astype(np.float32)
            encoded_data = np.kron(mapped, self.walsh_code)
            chips[:len(encoded_data)] = encoded_data
            
        return chips

    def decode(self, chips, target_walsh_code):
        N = self.walsh_size
        reshaped = chips.reshape(-1, N)
        decoded_values = np.dot(reshaped, target_walsh_code) / N
        
        bits = np.where(decoded_values > 0, 1, 0)
        decoded_bytes = np.packbits(bits).tobytes()
        
        # Remove null bytes (silence)
        return decoded_bytes.replace(b'\x00', b'')

    def input_thread(self):
        if self.file_path:
            with open(self.file_path, 'rb') as f:
                while True:
                    chunk = f.read(self.frame_size)
                    if not chunk: break
                    self.q.put(chunk)
            print(f"\033[93m[STATION] Finished loading {self.file_path} into memory. Sending...\033[0m")
        else:
            print("\033[95m[STATION] Interactive Chat Mode. Type messages below:\033[0m")
            while True:
                msg = sys.stdin.readline()
                if not msg: break
                msg_bytes = msg.encode()
                # Chunk it
                for i in range(0, len(msg_bytes), self.frame_size):
                    self.q.put(msg_bytes[i:i+self.frame_size])

    def run(self):
        threading.Thread(target=self.input_thread, daemon=True).start()
        
        try:
            while True:
                # 1. Get data to send
                try:
                    data_chunk = self.q.get_nowait()
                except queue.Empty:
                    data_chunk = b""
                
                # 2. Encode and send
                chips = self.encode(data_chunk)
                out_buf = chips.tobytes()
                self.sock.sendall(struct.pack("!I", len(out_buf)))
                self.sock.sendall(out_buf)
                
                # 3. Receive summed chips from channel
                len_buf = self.sock.recv(4)
                if not len_buf: break
                msg_len = struct.unpack("!I", len_buf)[0]
                
                in_buf = b""
                while len(in_buf) < msg_len:
                    packet = self.sock.recv(msg_len - len(in_buf))
                    if not packet: break
                    in_buf += packet
                if not in_buf: break
                
                summed_chips = np.frombuffer(in_buf, dtype=np.float32)
                
                # 4. Decode all stations (including ourselves, for confirmation)
                for i in range(self.walsh_size):
                    if i == self.idx: continue # Skip ourselves (we know what we sent)
                    
                    target_code = self.walsh_matrix[i]
                    decoded_bytes = self.decode(summed_chips, target_code)
                    
                    if decoded_bytes:
                        if self.file_path:
                            # Write to file
                            fname = f"output_st{self.idx}_from_{i}.txt"
                            with open(fname, "ab") as f:
                                f.write(decoded_bytes)
                            sys.stdout.write(f"\033[92m[RECV st_{i}] {len(decoded_bytes)} bytes written to {fname}\033[0m\r")
                            sys.stdout.flush()
                        else:
                            # Chat mode
                            text = decoded_bytes.decode(errors='replace').strip()
                            if text:
                                print(f"\033[94m[Station {i}]:\033[0m {text}")
                                
                # Throttle slightly to avoid blowing up CPU when idle
                if not data_chunk:
                    time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\033[91m[STATION] Disconnecting...\033[0m")
        except Exception as e:
            print(f"\n\033[91m[STATION] Error: {e}\033[0m")
        finally:
            self.sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--file", help="File to send (if omitted, starts interactive chat)")
    args = parser.parse_args()
    
    Station(args.host, args.port, args.file).run()
