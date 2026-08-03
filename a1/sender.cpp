#include "utils.hpp"
#include <chrono>
#include <iostream>

using namespace std;

int main(int argc, char* argv[]) {
    string host = "127.0.0.1";
    int port = 5000;
    string file = "sample.txt";
    string poly = "CRC-16";
    string error = "none";
    int payload = 64;
    unsigned seed = 7;

    for (int i = 1; i < argc; ++i) {
        string a = argv[i];
        if (a == "--host" && i + 1 < argc) host = argv[++i];
        else if (a == "--port" && i + 1 < argc) port = stoi(argv[++i]);
        else if (a == "--file" && i + 1 < argc) file = argv[++i];
        else if (a == "--poly" && i + 1 < argc) poly = argv[++i];
        else if (a == "--error" && i + 1 < argc) error = argv[++i];
        else if (a == "--payload" && i + 1 < argc) payload = stoi(argv[++i]);
        else if (a == "--seed" && i + 1 < argc) seed = (unsigned)stoul(argv[++i]);
    }

    try {
        vector<unsigned char> data = readbytes(file);
        auto frames = splitframes(data, payload);
        mt19937 rng = mkrng(seed);

        int sock = dial(host, port);
        if (sock < 0) {
            cerr << "Could not connect to " << host << ":" << port << "\n";
            return 1;
        }

        cout << "connected to " << host << ":" << port << "\n";
        cout << "frames: " << frames.size() << "\n";

        auto t1 = chrono::high_resolution_clock::now();
        long long tx_bits = 0;

        for (size_t i = 0; i < frames.size(); ++i) {
            string chosen = pickerror(error, rng);

            TxFrame f;
            f.no = (int)i + 1;
            f.poly = poly;
            f.payload = payload;
            f.error = chosen;

            string chk_bits = bytestobits(checksum_enc(frames[i]));
            string crc_bits = encodecrc(bytestobits(frames[i]), poly);

            chk_bits = injecterr(chk_bits, chosen, rng);
            crc_bits = injecterr(crc_bits, chosen, rng);

            f.checksum_bits = chk_bits;
            f.crc_bits = crc_bits;

            string line = frameline(f);
            if (!sendln(sock, line)) {
                cerr << "send failed\n";
                close(sock);
                return 1;
            }

            tx_bits += (long long)f.checksum_bits.size() + (long long)f.crc_bits.size();

            string ackline;
            if (!recvln(sock, ackline)) {
                cerr << "no ack\n";
                close(sock);
                return 1;
            }

            int no = 0;
            bool chk_ok = false, crc_ok = false;
            string cls;
            if (parseack(ackline, no, chk_ok, crc_ok, cls)) {
                cout << "frame " << no << " : "
                     << "checksum=" << (chk_ok ? "ACCEPT" : "REJECT")
                     << ", crc=" << (crc_ok ? "ACCEPT" : "REJECT")
                     << ", " << cls << "\n";
            } else {
                cout << "frame " << (i + 1) << " : bad ack format\n";
            }
        }

        sendln(sock, "END");

        auto t2 = chrono::high_resolution_clock::now();
        double ms = chrono::duration_cast<chrono::microseconds>(t2 - t1).count() / 1000.0;

        cout << "transmitted bits: " << tx_bits << "\n";
        cout << "time(ms): " << ms << "\n";
        close(sock);
    } catch (const exception& e) {
        cerr << "error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}