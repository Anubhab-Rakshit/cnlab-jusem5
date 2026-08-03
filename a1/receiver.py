import argparse
import time
from error_utils import *

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txfile")
    args = ap.parse_args()

    meta, frames = load_tx(args.txfile)
    scheme = meta.get("scheme", "checksum")
    poly = meta.get("poly", "CRC-16")
    gen = poly_bits(poly) if scheme == "crc" else ""

    bad = 0
    t1 = time.perf_counter()

    for i, bits in enumerate(frames, 1):
        if scheme == "checksum":
            ok = checksum_check(bits)
        else:
            ok = crc_check(bits, gen)

        print("frame", i, ":", "ACCEPT" if ok else "REJECT")
        if not ok:
            bad += 1

    t2 = time.perf_counter()
    print("detected:", bad, "bad frame(s)")
    print("time(ms):", round((t2 - t1) * 1000, 3))

if __name__ == "__main__":
    main()