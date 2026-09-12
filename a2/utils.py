import ctypes
import os
import random
import time

lib_path = os.path.join(os.path.dirname(__file__), 'bridge.so')
bridge = ctypes.CDLL(lib_path)

bridge.c_encodecrc.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
bridge.c_crck_ok.argtypes = [ctypes.c_char_p]
bridge.c_crck_ok.restype = ctypes.c_bool
bridge.c_injecterr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
bridge.c_frameline.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
bridge.c_parseframe.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
bridge.c_parseframe.restype = ctypes.c_bool
bridge.c_ackline.argtypes = [ctypes.c_int, ctypes.c_char_p]
bridge.c_parseack.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
bridge.c_parseack.restype = ctypes.c_bool
bridge.c_bytestobits.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p]
bridge.c_bitstowrite.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
bridge.c_bitstowrite.restype = ctypes.c_int

def make_frame(seq_no: int, payload: bytes) -> bytes:
    # Ethernet-like header: Dest MAC (6B) + Src MAC (6B) + Length (2B) + Seq No (1B) = 15 bytes
    header = b'\xaa'*6 + b'\xbb'*6 + len(payload).to_bytes(2, 'big') + (seq_no & 0xFF).to_bytes(1, 'big')
    data = header + payload
    
    # 1. Convert data bytes to bitstring via A1 C++ bridge
    bits_buf = ctypes.create_string_buffer(len(data) * 8 + 10)
    bridge.c_bytestobits(data, len(data), bits_buf)
    
    # 2. Compute and append CRC-32 via A1 C++ module
    crc_buf = ctypes.create_string_buffer(len(bits_buf.value) + 50)
    bridge.c_encodecrc(bits_buf.value, crc_buf)
    
    # 3. Pack bits back to network bytes
    byte_buf = ctypes.create_string_buffer(len(crc_buf.value) // 8 + 10)
    written = bridge.c_bitstowrite(crc_buf.value, byte_buf)
    return byte_buf.raw[:written]

def parse_frame(frame_bytes: bytes):
    if len(frame_bytes) < 19: # 15 header + 4 CRC
        return -1, b'', False
        
    bits_buf = ctypes.create_string_buffer(len(frame_bytes) * 8 + 10)
    bridge.c_bytestobits(frame_bytes, len(frame_bytes), bits_buf)
    
    # Check CRC validity using A1 C++ module
    is_valid = bridge.c_crck_ok(bits_buf.value)
    
    # Extract payload and sequence number
    orig_bits = bits_buf.value[:-32] if len(bits_buf.value) >= 32 else b''
    byte_buf = ctypes.create_string_buffer(len(orig_bits) // 8 + 10)
    written = bridge.c_bitstowrite(orig_bits, byte_buf)
    raw_data = byte_buf.raw[:written]
    
    if len(raw_data) < 15:
        return -1, b'', False
        
    length = int.from_bytes(raw_data[12:14], 'big')
    seq_no = raw_data[14]
    payload = raw_data[15:15+length]
    return seq_no, payload, is_valid

def channel_simulate(frame: bytes, loss_prob=0.1, err_prob=0.1, max_delay=0.5, force_drop=False, force_err=False):
    if force_drop or random.random() < loss_prob:
        return None
        
    delay = random.uniform(0, max_delay)
    time.sleep(delay)
    
    if force_err or random.random() < err_prob:
        # inject error using a1 C++ module 'random' mode
        bits_buf = ctypes.create_string_buffer(len(frame) * 8 + 10)
        bridge.c_bytestobits(frame, len(frame), bits_buf)
        
        err_buf = ctypes.create_string_buffer(len(bits_buf.value) + 10)
        bridge.c_injecterr(bits_buf.value, b"random", err_buf)
        
        byte_buf = ctypes.create_string_buffer(len(err_buf.value) // 8 + 10)
        written = bridge.c_bitstowrite(err_buf.value, byte_buf)
        return byte_buf.raw[:written]
        
    return frame

def make_ack(seq_no: int) -> bytes:
    out_buf = ctypes.create_string_buffer(500)
    bridge.c_ackline(seq_no, out_buf)
    line = out_buf.value
    
    bits_buf = ctypes.create_string_buffer(len(line) * 8 + 10)
    bridge.c_bytestobits(line, len(line), bits_buf)
    
    crc_buf = ctypes.create_string_buffer(len(bits_buf.value) + 50)
    bridge.c_encodecrc(bits_buf.value, crc_buf)
    
    byte_buf = ctypes.create_string_buffer(len(crc_buf.value) // 8 + 10)
    written = bridge.c_bitstowrite(crc_buf.value, byte_buf)
    return byte_buf.raw[:written]

def parse_ack(ack_bytes: bytes):
    bits_buf = ctypes.create_string_buffer(len(ack_bytes) * 8 + 10)
    bridge.c_bytestobits(ack_bytes, len(ack_bytes), bits_buf)
    
    is_valid = bridge.c_crck_ok(bits_buf.value)
    
    orig_bits = bits_buf.value[:-32] if len(bits_buf.value) >= 32 else b''
    byte_buf = ctypes.create_string_buffer(len(orig_bits) // 8 + 10)
    written = bridge.c_bitstowrite(orig_bits, byte_buf)
    line = byte_buf.raw[:written]
    
    no = ctypes.c_int()
    ok = bridge.c_parseack(line, ctypes.byref(no))
    if ok:
        return no.value, is_valid
    return -1, False
