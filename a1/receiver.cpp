#include "crc.hpp"
#include "checksum.hpp"
#include "error_injection.hpp"
#include "framing.hpp"
#include "network_utils.hpp"
#include <chrono>
#include <iostream>
#include <map>

using namespace std;

int main(int argc, char* argv[]) {
    int port = 5000;

    for (int i = 1; i < argc; ++i) {
        string a = argv[i];
        if (a == "--port" && i + 1 < argc) port = stoi(argv[++i]);
    }

    try {
        int srv = mkserver(port);
        if (srv < 0) {
            cerr << "Could not start server on port " << port << "\n";
            return 1;
        }

        cout << "listening on port " << port << "\n";

        sockaddr_in cli{};
        socklen_t len = sizeof(cli);
        int conn = accept(srv, (sockaddr*)&cli, &len);
        if (conn < 0) {
            cerr << "accept failed\n";
            close(srv);
            return 1;
        }

        cout << "client connected\n";

        int chk_good = 0, chk_bad = 0;
        int crc_good = 0, crc_bad = 0;
        map<string, int> cls_count;

        auto t1 = chrono::high_resolution_clock::now();

        while (true) {
            string line;
            if (!recvln(conn, line)) break;
            if (line == "END") break;

            TxFrame f;
            if (!parseframe(line, f)) {
                sendln(conn, ackline(-1, false, false, "BAD_FRAME"));
                continue;
            }

            bool chk_ok = checksum_ok(bitstowrite(f.checksum_bits));
            bool crc_ok = crck_ok(f.crc_bits, f.poly);
            string cls = classify(chk_ok, crc_ok);

            if (chk_ok) chk_good++; else chk_bad++;
            if (crc_ok) crc_good++; else crc_bad++;
            cls_count[cls]++;

            cout << "frame " << f.no << " : "
                 << "checksum=" << (chk_ok ? "ACCEPT" : "REJECT")
                 << ", crc=" << (crc_ok ? "ACCEPT" : "REJECT")
                 << ", " << cls << "\n";

            sendln(conn, ackline(f.no, chk_ok, crc_ok, cls));
        }

        auto t2 = chrono::high_resolution_clock::now();
        double ms = chrono::duration_cast<chrono::microseconds>(t2 - t1).count() / 1000.0;

        cout << "checksum_accept: " << chk_good << "\n";
        cout << "checksum_reject: " << chk_bad << "\n";
        cout << "crc_accept: " << crc_good << "\n";
        cout << "crc_reject: " << crc_bad << "\n";
        cout << "both_detected: " << cls_count["BOTH_DETECTED"] << "\n";
        cout << "checksum_only: " << cls_count["CHECKSUM_ONLY"] << "\n";
        cout << "crc_only: " << cls_count["CRC_ONLY"] << "\n";
        cout << "no_error_detected: " << cls_count["NO_ERROR_DETECTED"] << "\n";
        cout << "time(ms): " << ms << "\n";

        close(conn);
        close(srv);
    } catch (const exception& e) {
        cerr << "error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}