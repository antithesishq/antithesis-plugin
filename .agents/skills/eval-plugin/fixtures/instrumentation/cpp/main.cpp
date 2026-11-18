#include <chrono>
#include <thread>
#include <vector>
#include "antithesis_instrumentation.h"
#include "antithesis_sdk.h"

static void spin(long x) {
  for (;;) {
    switch (x % 3) {
      case 0: x += 7; break;
      case 1: x *= 3; break;
      default: x -= 1;
    }
    x %= 100003;
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }
}

int main() {
  REACHABLE("cpp service started", {});
  std::vector<std::thread> threads;
  for (long i = 1; i < 4; i++) threads.emplace_back(spin, i);
  for (auto& t : threads) t.join();
}
