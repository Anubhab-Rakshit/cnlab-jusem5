#ifndef CHECKSUM_HPP
#define CHECKSUM_HPP

#include <cstdint>
#include <vector>

using namespace std;

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

#endif
