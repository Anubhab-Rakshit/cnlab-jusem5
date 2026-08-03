// utils.hpp – helpers for CRC, checksums, frame splitting, sockets
// part of the cnlab noisy-transmission simulator
#ifndef UTILS_HPP
#define UTILS_HPP

#include <algorithm>
#include <arpa/inet.h>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <netdb.h>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <unistd.h>
#include <vector>

using namespace std;

// transmitted frame bookkeeping
struct TxFrame {
  int no = 0;
  string poly;
  int payload = 64;
  string error, checksum_bits, crc_bits;
};

// CRC polynomials by name
inline vector<int> polyexps(const string &name) {
  if (name == "CRC-8")
    return {8, 7, 6, 4, 2, 0};
  if (name == "CRC-10")
    return {10, 9, 5, 4, 1, 0};
  if (name == "CRC-16")
    return {16, 15, 2, 0};
  if (name == "CRC-32")
    return {32, 26, 23, 22, 16, 12, 11, 10, 8, 7, 5, 4, 2, 1, 0};
  throw runtime_error("unknown CRC: " + name);
}
inline string polybits(const string &name) {
  vector<int> e = polyexps(name);
  int d = *max_element(e.begin(), e.end());
  string g(d + 1, '0');
  for (int v : e)
    g[d - v] = '1';
  return g;
}

// file I/O
inline vector<unsigned char> readbytes(const string &path) {
  ifstream f(path, ios::binary);
  if (!f)
    throw runtime_error("file not found: " + path);
  return vector<unsigned char>((istreambuf_iterator<char>(f)),
                               istreambuf_iterator<char>());
}

// split byte stream into Ethernet-like frames
inline vector<vector<unsigned char>>
splitframes(const vector<unsigned char> &data, int payload) {
  payload = max(46, min(1500, payload));
  vector<vector<unsigned char>> frames;
  for (size_t i = 0; i < data.size(); i += payload) {
    auto end = data.begin() + min(data.size(), i + (size_t)payload);
    vector<unsigned char> f(data.begin() + i, end);
    if ((int)f.size() < 46)
      f.resize(46, 0); // pad short frames
    frames.push_back(move(f));
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

// one's complement checksum
inline uint16_t onesadd(uint16_t a, uint16_t b) {
  uint32_t s = (uint32_t)a + (uint32_t)b;
  return (s & 0xFFFFu) + (s >> 16);
}
inline vector<unsigned char> checksum_enc(const vector<unsigned char> &data) {
  vector<unsigned char> x = data;
  if (x.size() & 1)
    x.push_back(0);
  uint16_t s = 0;
  for (size_t i = 0; i < x.size(); i += 2) {
    uint16_t w = ((uint16_t)x[i] << 8) | x[i + 1];
    s = onesadd(s, w);
  }
  uint16_t c = ~s;
  x.push_back((c >> 8) & 0xFF);
  x.push_back(c & 0xFF);
  return x;
}
inline bool checksum_ok(const vector<unsigned char> &pkt) {
  vector<unsigned char> x = pkt;
  if (x.size() & 1)
    x.push_back(0);
  uint16_t s = 0;
  for (size_t i = 0; i < x.size(); i += 2) {
    uint16_t w = ((uint16_t)x[i] << 8) | x[i + 1];
    s = onesadd(s, w);
  }
  return s == 0xFFFFu;
}

// CRC — polynomial long division over GF(2)
inline string encodecrc(const string &bits, const string &poly) {
  string g = polybits(poly);
  int r = g.size() - 1;
  vector<int> work(bits.size() + r), gen(g.size());
  for (size_t i = 0; i < bits.size(); ++i)
    work[i] = bits[i] == '1';
  for (size_t i = 0; i < gen.size(); ++i)
    gen[i] = g[i] == '1';
  for (size_t i = 0; i < bits.size(); ++i)
    if (work[i])
      for (size_t j = 0; j < gen.size(); ++j)
        work[i + j] ^= gen[j];
  string rem;
  for (size_t i = bits.size(); i < work.size(); ++i)
    rem.push_back(work[i] ? '1' : '0');
  return bits + rem;
}
inline bool crck_ok(const string &bits, const string &poly) {
  string g = polybits(poly);
  int r = g.size() - 1;
  if (bits.size() < (size_t)r)
    return false;
  vector<int> work(bits.size()), gen(g.size());
  for (size_t i = 0; i < bits.size(); ++i)
    work[i] = bits[i] == '1';
  for (size_t i = 0; i < gen.size(); ++i)
    gen[i] = g[i] == '1';
  for (size_t i = 0; i + gen.size() <= work.size(); ++i)
    if (work[i])
      for (size_t j = 0; j < gen.size(); ++j)
        work[i + j] ^= gen[j];
  for (size_t i = work.size() - r; i < work.size(); ++i)
    if (work[i])
      return false;
  return true;
}

// error injection for simulating noisy links
inline string pickerror(const string &kind, mt19937 &rng) {
  if (kind != "random")
    return kind;
  const char *opts[] = {"single", "two", "odd", "burst"};
  uniform_int_distribution<int> d(0, 3);
  return opts[d(rng)];
}
inline string injecterr(string bits, const string &kind, mt19937 &rng) {
  int n = (int)bits.size();
  if (kind == "none" || n == 0)
    return bits;
  auto flip = [&](int i) { bits[i] = (bits[i] == '0') ? '1' : '0'; };
  if (kind == "single") {
    uniform_int_distribution<int> d(0, n - 1);
    flip(d(rng));
  } else if (kind == "two") {
    if (n == 1)
      flip(0);
    else {
      uniform_int_distribution<int> d(0, n - 1);
      int i = d(rng), j;
      do {
        j = d(rng);
      } while (j == i);
      flip(i);
      flip(j);
    }
  } else if (kind == "odd") {
    int k = n >= 3 ? 3 : 1;
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    shuffle(idx.begin(), idx.end(), rng);
    for (int i = 0; i < k; ++i)
      flip(idx[i]);
  } else if (kind == "burst") {
    int m = min(8, n);
    if (m < 2)
      flip(0);
    else {
      uniform_int_distribution<int> len(2, m);
      int l = len(rng);
      uniform_int_distribution<int> off(0, n - l);
      int o = off(rng);
      for (int i = o; i < o + l; ++i)
        flip(i);
    }
  }
  return bits;
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
inline bool parseack(const string &s, int &no, bool &chk, bool &crc,
                     string &cls) {
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

// socket helpers
inline bool sendall(int sock, const string &data) {
  const char *p = data.c_str();
  size_t left = data.size();
  while (left > 0) {
    ssize_t n = send(sock, p, left, 0);
    if (n <= 0)
      return false;
    p += n;
    left -= (size_t)n;
  }
  return true;
}
inline bool sendln(int sock, const string &line) {
  return sendall(sock, line + "\n");
}
inline bool recvln(int sock, string &out) {
  out.clear();
  char c;
  while (recv(sock, &c, 1, 0) > 0) {
    if (c == '\n')
      break;
    if (c != '\r')
      out.push_back(c);
  }
  return true;
}
inline int dial(const string &host, int port) {
  addrinfo hint{}, *res;
  hint.ai_family = AF_UNSPEC;
  hint.ai_socktype = SOCK_STREAM;
  if (getaddrinfo(host.c_str(), to_string(port).c_str(), &hint, &res) != 0)
    return -1;
  int s = -1;
  for (addrinfo *rp = res; rp; rp = rp->ai_next) {
    s = socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
    if (s < 0)
      continue;
    if (connect(s, rp->ai_addr, rp->ai_addrlen) == 0)
      break;
    close(s);
    s = -1;
  }
  freeaddrinfo(res);
  return s;
}
inline int mkserver(int port) {
  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock < 0)
    return -1;

  int opt = 1;
  setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = INADDR_ANY;
  addr.sin_port = htons(port);

  socklen_t addrlen = sizeof(addr);
  if (::bind(sock, (sockaddr *)&addr, addrlen) != 0) {
    close(sock);
    return -1;
  }

  if (listen(sock, SOMAXCONN) != 0) {
    close(sock);
    return -1;
  }
  return sock;
}
inline mt19937 mkrng(unsigned seed = random_device{}()) {
  return mt19937(seed);
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