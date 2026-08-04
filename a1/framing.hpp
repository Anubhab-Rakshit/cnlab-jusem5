#ifndef FRAMING_HPP
#define FRAMING_HPP

#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <utility>

using namespace std;

// transmitted frame bookkeeping
struct TxFrame {
  int no = 0;
  string poly;
  int payload = 64;
  string error, checksum_bits, crc_bits;
};

// file I/O
inline vector<unsigned char> readbytes(const string &path) {
  ifstream f(path, ios::binary);
  if (!f)
    throw runtime_error("file not found: " + path);
  return vector<unsigned char>((istreambuf_iterator<char>(f)),
                               istreambuf_iterator<char>());
}

// split byte stream into Ethernet-like frames
inline vector<vector<unsigned char>> splitframes(const vector<unsigned char> &data, int payload) {
  payload = max(46, min(1500, payload));
  vector<vector<unsigned char>> frames;
  for (size_t i = 0; i < data.size(); i += payload) {
    auto end = data.begin() + min(data.size(), i + (size_t)payload);
    vector<unsigned char> f(data.begin() + i, end);
    if ((int)f.size() < 46)
      f.resize(46, 0); // pad short frames
    frames.push_back(std::move(f));
  }
  if (frames.empty())
    frames.push_back(vector<unsigned char>(46, 0));
  return frames;
}

inline string bytestobits(const vector<unsigned char> &data) {
  string bits;
  bits.reserve(data.size() * 8);
  for (unsigned char b : data)
    for (int i = 7; i >= 0; --i)
      bits.push_back(((b >> i) & 1) ? '1' : '0');
  return bits;
}

inline vector<unsigned char> bitstowrite(const string &bits) {
  string x = bits;
  if (x.size() % 8)
    x.append(8 - (x.size() % 8), '0');
  vector<unsigned char> out;
  out.reserve(x.size() / 8);
  for (size_t i = 0; i < x.size(); i += 8) {
    unsigned char v = 0;
    for (int j = 0; j < 8; ++j)
      v = (v << 1) | (x[i + j] == '1');
    out.push_back(v);
  }
  return out;
}

// frame line serialization – pipe-delimited
inline string frameline(const TxFrame &f) {
  return to_string(f.no) + "|" + f.poly + "|" + to_string(f.payload) + "|" +
         f.error + "|" + f.checksum_bits + "|" + f.crc_bits;
}

inline bool parseframe(const string &s, TxFrame &f) {
  vector<string> p;
  string tmp;
  istringstream iss(s);
  while (getline(iss, tmp, '|'))
    p.push_back(tmp);
  if (p.size() != 6)
    return false;
  try {
    f.no = stoi(p[0]);
    f.poly = p[1];
    f.payload = stoi(p[2]);
    f.error = p[3];
    f.checksum_bits = p[4];
    f.crc_bits = p[5];
    return true;
  } catch (...) {
    return false;
  }
}

inline string ackline(int no, bool chk, bool crc, const string &cls) {
  return "ACK|" + to_string(no) + "|" + (chk ? "1" : "0") + "|" +
         (crc ? "1" : "0") + "|" + cls;
}

inline bool parseack(const string &s, int &no, bool &chk, bool &crc, string &cls) {
  vector<string> p;
  string tmp;
  istringstream iss(s);
  while (getline(iss, tmp, '|'))
    p.push_back(tmp);
  if (p.size() != 5 || p[0] != "ACK")
    return false;
  try {
    no = stoi(p[1]);
    chk = p[2] == "1";
    crc = p[3] == "1";
    cls = p[4];
    return true;
  } catch (...) {
    return false;
  }
}

// tag a frame as detected/none by checksum + crc
inline string classify(bool chk, bool crc) {
  if (chk && crc)
    return "NO_ERROR_DETECTED";
  if (!chk && !crc)
    return "BOTH_DETECTED";
  return chk ? "CRC_ONLY" : "CHECKSUM_ONLY";
}

#endif
