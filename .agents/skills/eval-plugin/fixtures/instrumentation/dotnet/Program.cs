using System.Threading;

static void Spin(long x)
{
    while (true)
    {
        if (x % 3 == 0) x += 7; else if (x % 3 == 1) x *= 3; else x -= 1;
        x %= 100003;
        Thread.Sleep(50);
    }
}

var threads = new Thread[3];
for (int i = 0; i < 3; i++) { long id = i + 1; threads[i] = new Thread(() => Spin(id)); threads[i].Start(); }
foreach (var t in threads) t.Join();
