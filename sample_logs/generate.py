"""Creates sample_logs/app.log with normal traffic plus injected incidents."""
import datetime as dt
import random

random.seed(7)
svcs = ["auth-service", "payment-service", "order-api", "db-gateway"]
normal = [("INFO", "Request completed in {} ms"), ("INFO", "User {} logged in"),
          ("DEBUG", "Cache hit for key {}"), ("WARN", "Slow query took {} ms")]
start = dt.datetime(2026, 9, 28, 9, 0, 0)
rows = []
for i in range(1500):
    t = start + dt.timedelta(seconds=i * 2)
    lvl, m = random.choice(normal)
    rows.append((t, f"{t:%Y-%m-%d %H:%M:%S} {lvl} {random.choice(svcs)} {m.format(random.randint(5, 900))}"))
for k in range(12):
    t = start + dt.timedelta(seconds=800 + k * 3)
    rows.append((t, f"{t:%Y-%m-%d %H:%M:%S} ERROR payment-service Database connection timeout after {random.randint(10, 30)}s"))
for k in range(8):
    t = start + dt.timedelta(seconds=2000 + k * 5)
    rows.append((t, f"{t:%Y-%m-%d %H:%M:%S} ERROR auth-service Unauthorized access attempt from 10.0.0.{random.randint(2, 250)}"))
t = start + dt.timedelta(seconds=2500)
rows.append((t, f"{t:%Y-%m-%d %H:%M:%S} CRITICAL db-gateway Out of memory: killed process 4312"))
t = start + dt.timedelta(seconds=1500)
rows.append((t, f"{t:%Y-%m-%d %H:%M:%S} ERROR order-api Unhandled exception in checkout\nTraceback (most recent call last):\n  File \"orders.py\", line 88, in checkout\nKeyError: 'cart_id'"))
rows.sort(key=lambda r: r[0])
open("sample_logs/app.log", "w").write("\n".join(r[1] for r in rows) + "\n")
print("wrote sample_logs/app.log")
