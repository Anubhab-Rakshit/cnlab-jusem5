from pathlib import Path
import random

POLY = {
    "CRC-8":  [8, 7, 6, 4, 2, 0],
    "CRC-10": [10, 9, 5, 4, 1, 0],
    "CRC-16": [16, 15, 2, 0],
    "CRC-32": [32, 26, 23, 22, 16, 12, 11, 10, 8, 7, 5, 4, 2, 1, 0]
}

def read_bytes(name):
    p = Path(name)
    if not p.exists():
        raise FileNotFoundError(name)
    return p.read_bytes()

def split_frames(data, payload):
    payload = max(46, min(1500, payload))
    arr = []
    for i in range(0, len(data), payload):
        x = data[i:i + payload]
        if len(x) < 46:
            x += b"\x00" * (46 - len(x))
        arr.append(x)
    if not arr:
        arr = [b"\x00" * 46]
    return arr

def bytes_to_bits(data):
    return "".join(f"{b:08b}" for b in data)

def ones_add(a, b):
    s = a + b
    return (s & 0xFFFF) + (s >> 16)

def checksum_send(bits):
    s = 0
    for i in range(0, len(bits), 16):
        s = ones_add(s, int(bits[i:i + 16], 2))
    c = (~s) & 0xFFFF
    return bits + f"{c:016b}"

def checksum_check(bits):
    s = 0
    for i in range(0, len(bits), 16):
        s = ones_add(s, int(bits[i:i + 16], 2))
    return s == 0xFFFF

def poly_bits(name):
    exps = POLY[name]
    d = max(exps)
    g = ["0"] * (d + 1)
    for e in exps:
        g[d - e] = "1"
    return "".join(g)

def crc_div(bits, gen):
    work = [1 if c == "1" else 0 for c in bits] + [0] * (len(gen) - 1)
    g = [1 if c == "1" else 0 for c in gen]
    for i in range(len(bits)):
        if work[i] == 1:
            for j in range(len(g)):
                work[i + j] ^= g[j]
    rem = work[-(len(gen) - 1):]
    return "".join("1" if x else "0" for x in rem)

def crc_send(bits, gen):
    return bits + crc_div(bits, gen)

def crc_check(bits, gen):
    r = len(gen) - 1
    work = [1 if c == "1" else 0 for c in bits]
    g = [1 if c == "1" else 0 for c in gen]
    for i in range(len(bits) - r):
        if work[i] == 1:
            for j in range(len(g)):
                work[i + j] ^= g[j]
    return all(x == 0 for x in work[-r:])

def real_error(kind, rng):
    if kind == "random":
        return rng.choice(["single", "two", "odd", "burst"])
    return kind

def inject_bits(bits, kind, rng):
    kind = real_error(kind, rng)
    if kind == "none" or not bits:
        return bits

    a = list(bits)
    n = len(a)

    def flip(p):
        a[p] = "1" if a[p] == "0" else "0"

    if kind == "single":
        flip(rng.randrange(n))

    elif kind == "two":
        if n == 1:
            flip(0)
        else:
            p1 = rng.randrange(n)
            p2 = rng.randrange(n)
            while p2 == p1:
                p2 = rng.randrange(n)
            flip(p1)
            flip(p2)

    elif kind == "odd":
        k = 3 if n >= 3 else 1
        for p in rng.sample(range(n), k):
            flip(p)

    elif kind == "burst":
        m = min(8, n)
        if m < 2:
            flip(0)
        else:
            ln = rng.randint(2, m)
            st = rng.randint(0, n - ln)
            for i in range(st, st + ln):
                flip(i)

    return "".join(a)

def save_tx(path, scheme, poly, payload, error, frames):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"scheme={scheme}\n")
        f.write(f"poly={poly}\n")
        f.write(f"payload={payload}\n")
        f.write(f"error={error}\n")
        f.write(f"frames={len(frames)}\n")
        for x in frames:
            f.write(f"frame={x}\n")

def load_tx(path):
    meta = {}
    frames = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("frame="):
                frames.append(line[6:])
            else:
                k, v = line.split("=", 1)
                meta[k] = v
    meta["payload"] = int(meta.get("payload", "64"))
    meta["frames"] = int(meta.get("frames", str(len(frames))))
    return meta, frames