# Flow Control Assignment (Assignment 2) Guide

## 1. Overview of the Implementation
This project simulates the Data Link Layer's flow control mechanisms over UDP sockets to demonstrate real-world networking properties like transmission delay, packet loss, and corruption (bit errors).

### Key Files
- `utils.py`: The core simulation logic. It implements CRC-32 for error detection, frame struct packing (Header + Payload + Trailer), and a `channel_simulate()` function to inject random errors and losses.
- `sender.py`: Implements the sending side of three flow control protocols: Stop and Wait, Go-Back-N (GBN), and Selective Repeat (SR).
- `receiver.py`: Implements the receiving side, including cumulative ACKs (for GBN) and independent ACKs with an out-of-order buffer (for SR).

---

## 2. Testing Scenarios to Show the Professor
To effectively demonstrate this assignment, you should run the sender and receiver in separate terminals. Use the arguments `--loss` (packet loss probability) and `--err` (bit error probability) to show how different protocols react.

### Scenario A: Ideal Channel (No Loss, No Errors)
**Command:** `python3 a2/sender.py --protocol gbn --loss 0.0 --err 0.0`
**What to show:**
- Packets are sent and ACKed linearly.
- Explain that efficiency is highest here. Stop-and-Wait will be much slower than GBN and SR because it wastes RTT (Round Trip Time) waiting for each ACK.

### Scenario B: High Packet Loss (The Network is Dropping Packets)
**Command:** `python3 a2/sender.py --protocol gbn --loss 0.3 --err 0.0`
**What to show:**
- When a packet is lost in **GBN**, the receiver ignores any subsequent out-of-order packets. The sender's timeout triggers, and it retransmits the *entire window* starting from the lost packet. 
- **Compare this with Selective Repeat (SR)**: `python3 a2/sender.py --protocol sr --loss 0.3`. In SR, the receiver buffers the out-of-order packets. When the timeout triggers on the sender, it *only* retransmits the single lost packet, and the receiver's window jumps forward. This proves SR is more bandwidth-efficient on lossy links!

### Scenario C: High Bit Error Rate (Corruption)
**Command:** `python3 a2/sender.py --protocol saw --loss 0.0 --err 0.3`
**What to show:**
- The receiver gets the packet but the `check_crc32()` function detects corruption.
- The receiver drops the frame. The sender eventually times out and resends it.
- This demonstrates the robustness of the CRC algorithm integrated from Assignment 1.

### Scenario D: Deterministic Error Injection (For Live Demonstration)
Instead of relying on random probabilities, you can use the `--inject` flag on the sender to intentionally trigger exactly one error during a live presentation.

**Commands to run:**
1. Drop a specific Data Frame (e.g., frame 2):
   `python3 a2/sender.py --protocol gbn --loss 0.0 --err 0.0 --inject drop_2`
   *(Shows: Sender explicitly drops packet 2, receiver receives 3 out-of-order, sender times out and resends 2, 3, 4)*

2. Corrupt a specific Data Frame (e.g., frame 3):
   `python3 a2/sender.py --protocol sr --loss 0.0 --err 0.0 --inject corr_3`
   *(Shows: Frame 3 is corrupted. Receiver drops it, but buffers frame 4, 5, 6 and sends independent ACKs. Sender only retransmits 3.)*

3. Drop a specific ACK (e.g., ACK 1):
   `python3 a2/sender.py --protocol saw --loss 0.0 --err 0.0 --inject drop_ack_1`
   *(Shows: Sender sends frame 1. Receiver gets it and sends ACK 1. Sender intentionally ignores ACK 1. Sender times out and resends frame 1. Receiver detects it's a duplicate and re-ACKs without re-processing.)*

---

## 3. Potential Questions & Answers (VIVA Prep)

**Q1: Why did you use UDP instead of TCP for this simulation?**
**Answer:** TCP already has built-in flow control (sliding window) and error recovery. If we used TCP, the OS would handle retransmissions for us automatically, defeating the purpose of the assignment. UDP is connectionless and unreliable, making it the perfect "blank canvas" to build our own Data Link Layer flow control on top.

**Q2: How does the frame structure map to your code?**
**Answer:** In `utils.py`, `make_frame()` builds a 15-byte header using `struct.pack("!6s6sHB", src, dst, length, seq_no)`. This perfectly matches the assignment's requirements (MAC addresses, Length, and Sequence Number). The CRC-32 is appended at the very end as a 4-byte trailer.

**Q3: How does Go-Back-N differ from Selective Repeat in your implementation?**
**Answer:** 
- **GBN Receiver** only has a window of size 1. If it expects packet 3 and gets packet 4, it drops packet 4 and sends an ACK for 2 (or just drops it). When the sender times out on 3, it resends 3, 4, 5, etc.
- **SR Receiver** has a window of size N. If it expects 3 and gets 4, it places 4 in a dictionary (buffer). It sends an independent ACK for 4. When 3 eventually arrives, it delivers both 3 and 4 to the application layer.

**Q4: What is the sequence number limit in your GBN/SR implementation?**
**Answer:** Sequence numbers wrap around using modulo arithmetic. For 1-byte sequence numbers, the modulo is 256. A critical requirement for GBN and SR is that the sequence number space must be at least 2 × WindowSize to prevent the receiver from confusing a retransmission of an old window with a new window.

**Q5: How do you simulate delay and errors?**
**Answer:** The `channel_simulate()` function intercepts the packet before it goes into the socket. It uses Python's `random.random()` to conditionally return `None` (simulating packet loss), or it flips a random bit using XOR (simulating corruption).

**Q6: What happens if an ACK is lost?**
**Answer:** In GBN, cumulative ACKs solve this naturally. If ACK 2 is lost but ACK 3 arrives, the sender knows packet 2 was also received successfully. In Stop-and-Wait or SR, a lost ACK will cause the sender to time out and retransmit the packet. The receiver will recognize it as a duplicate (via sequence numbers) and simply re-ACK it without passing it to the application layer twice.
