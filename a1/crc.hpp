#ifndef CRC_HPP
#define CRC_HPP

#include <vector>
#include <string>
#include <algorithm>
#include <stdexcept>

using namespace std;

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

#endif
