#ifndef ERROR_INJECTION_HPP
#define ERROR_INJECTION_HPP

#include <algorithm>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using namespace std;

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
  } else if (kind == "checksum_miss") {

    int found = 0;
    for (int i = 0; i < n - 16 && !found; ++i) {
      if (bits[i] != bits[i + 16]) {
        flip(i);
        flip(i + 16);
        found = 1;
      }
    }
  } else if (kind == "crc_miss") {

    string g = "11000000000000101";
    for (size_t i = 0; i < g.size() && i < (size_t)n; ++i) {
      if (g[i] == '1')
        flip(i);
    }
  }
  return bits;
}

#endif
