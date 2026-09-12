import random
import struct
import binascii
import time

def crc32(data: bytes) -> bytes:
    crc = binascii.crc32(data) & 0xffffffff
    return struct.pack("!I", crc)

def check_crc32(data_with_crc: bytes) -> bool:
    if len(data_with_crc) < 4: return False
    data = data_with_crc[:-4]
    expected_crc = data_with_crc[-4:]
    return crc32(data) == expected_crc

def make_frame(seq_no: int, payload: bytes) -> bytes:
    src = b'\xaa' * 6
    dst = b'\xbb' * 6
    length = len(payload)
    header = struct.pack("!6s6sHB", src, dst, length, seq_no)
    data = header + payload
    trailer = crc32(data)
    return data + trailer

def parse_frame(frame: bytes):
    if len(frame) < 19:
        return None, b'', False
    is_valid = check_crc32(frame)
    header = frame[:15]
    src, dst, length, seq_no = struct.unpack("!6s6sHB", header)
    payload = frame[15:-4]
    return seq_no, payload, is_valid

def channel_simulate(frame: bytes, loss_prob=0.1, err_prob=0.1, max_delay=0.5, force_drop=False, force_err=False):
    if force_drop or random.random() < loss_prob:
        return None 
    
    delay = random.uniform(0, max_delay)
    time.sleep(delay)
    
    if force_err or random.random() < err_prob:
        idx = random.randint(0, len(frame)-1)
        frame = bytearray(frame)
        frame[idx] ^= 1
        frame = bytes(frame)
        
    return frame

def make_ack(seq_no: int) -> bytes:
    return struct.pack("!B", seq_no) + crc32(struct.pack("!B", seq_no))

def parse_ack(ack: bytes):
    if len(ack) < 5: return None, False
    is_valid = check_crc32(ack)
    seq_no = struct.unpack("!B", ack[:1])[0]
    return seq_no, is_valid
