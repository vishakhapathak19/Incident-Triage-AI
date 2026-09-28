"""Live monitoring: tails a log file and re-runs triage on a rolling window.  python monitor.py app.log 10"""
import os
import sys
import time
from collections import deque

from core import service, store


def run(path, interval=10, window=500):
    store.init()
    pos, buf = 0, deque(maxlen=window)
    while True:
        if os.path.exists(path):
            if os.path.getsize(path) < pos:  # log rotated
                pos = 0
            with open(path, errors="ignore") as f:
                f.seek(pos)
                new = f.readlines()
                pos = f.tell()
            if new:
                buf.extend(new)
                print(time.strftime("%H:%M:%S"), service.process(list(buf)))
        time.sleep(interval)


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10)
