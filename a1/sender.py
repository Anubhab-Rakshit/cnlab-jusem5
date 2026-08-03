import argparse
import random
import time
from error_utils import *

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--scheme", choices=["checksum", "crc"], default="checksum")
    ap.add_argument("--poly", choices=["CRC-8", "CRC-10", "CRC-16", "CRC-32"], default="CRC-16")
    ap.add_argument("--error", choices=["none", "single", "two", "odd", "burst", "random"], default="none")
    ap.add_argument("--payload", type=int, default=64)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="tx.txt")
    args = ap.parse_args()

    data = read_bytes(args.file)
    frames = split_frames(data, args.payload)
    rng = random.Random(args.seed)
    gen = poly_bits(args.poly) if args.scheme == "crc" else ""

    tx_frames = []
    t1 = time.perf_counter()

    for fr in frames:
        bits = bytes_to_bits(fr)
        if args.scheme == "checksum":
            bits = checksum_send(bits)
        else:
            bits = crc_send(bits, gen)

        bits = inject_bits(bits, args.error, rng)
        tx_frames.append(bits)

    save_tx(args.out, args.scheme, args.poly, args.payload, args.error, tx_frames)

    t2 = time.perf_counter()
    print("saved:", args.out)
    print("frames:", len(tx_frames))
    print("time(ms):", round((t2 - t1) * 1000, 3))

if __name__ == "__main__":
    main()