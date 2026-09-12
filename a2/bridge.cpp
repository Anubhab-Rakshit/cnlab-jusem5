#include "../a1/framing.hpp"
#include "../a1/crc.hpp"
#include "../a1/error_injection.hpp"
#include <string>
#include <cstring>
#include <vector>
#include <random>

extern "C" {
    void c_encodecrc(const char* bits_in, char* out) {
        std::string bits = bits_in;
        std::string res = encodecrc(bits, "CRC-32");
        std::strcpy(out, res.c_str());
    }
    
    bool c_crck_ok(const char* bits_in) {
        return crck_ok(bits_in, "CRC-32");
    }
    
    void c_injecterr(const char* bits_in, const char* kind, char* out) {
        std::string bits = bits_in;
        std::mt19937 rng(std::random_device{}());
        std::string res = injecterr(bits, kind, rng);
        std::strcpy(out, res.c_str());
    }

    // framing wrappers
    void c_frameline(int no, int payload_size, char* out) {
        TxFrame f;
        f.no = no;
        f.poly = "CRC-32";
        f.payload = payload_size;
        f.error = "NONE";
        f.checksum_bits = "0";
        f.crc_bits = "0";
        std::string res = frameline(f);
        std::strcpy(out, res.c_str());
    }

    bool c_parseframe(const char* line, int* no, int* payload_size) {
        TxFrame f;
        if (parseframe(line, f)) {
            *no = f.no;
            *payload_size = f.payload;
            return true;
        }
        return false;
    }

    void c_ackline(int no, char* out) {
        std::string res = ackline(no, true, true, "OK");
        std::strcpy(out, res.c_str());
    }

    bool c_parseack(const char* line, int* no) {
        bool chk, crc; std::string cls;
        return parseack(line, *no, chk, crc, cls);
    }
    
    // bit conversions
    void c_bytestobits(const unsigned char* data, int len, char* out) {
        std::vector<unsigned char> vec(data, data + len);
        std::string res = bytestobits(vec);
        std::strcpy(out, res.c_str());
    }
    
    int c_bitstowrite(const char* bits, unsigned char* out) {
        std::string b = bits;
        std::vector<unsigned char> res = bitstowrite(b);
        std::memcpy(out, res.data(), res.size());
        return res.size();
    }
}
