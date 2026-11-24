import threading
import time


def spin(x):
    while True:
        if x % 3 == 0:
            x += 7
        elif x % 3 == 1:
            x *= 3
        else:
            x -= 1
        x %= 100003
        time.sleep(0.05)


for i in range(1, 4):
    threading.Thread(target=spin, args=(i,)).start()
