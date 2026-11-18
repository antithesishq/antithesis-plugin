public class JavaService {
  static void spin(long x) {
    while (true) {
      if (x % 3 == 0) x += 7; else if (x % 3 == 1) x *= 3; else x -= 1;
      x %= 100003;
      try { Thread.sleep(50); } catch (InterruptedException e) { return; }
    }
  }

  public static void main(String[] args) throws Exception {
    Thread[] threads = new Thread[3];
    for (int i = 0; i < 3; i++) {
      final long id = i + 1;
      threads[i] = new Thread(() -> spin(id));
      threads[i].start();
    }
    for (Thread t : threads) t.join();
  }
}
