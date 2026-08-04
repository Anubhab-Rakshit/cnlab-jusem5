#ifndef NETWORK_UTILS_HPP
#define NETWORK_UTILS_HPP

#include <string>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <random>

using namespace std;

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

#endif
