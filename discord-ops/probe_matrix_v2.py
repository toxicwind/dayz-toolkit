import sys
import os
import time

def probe(fd, name):
    start = time.time_ns()
    msg = f"🔮 PROBE[{name}] TS={start}\n"
    try:
        os.write(fd, msg.encode())
        end = time.time_ns()
        duration = (end - start) / 1000000.0
        # Log to stderr (usually visible) for correlation
        sys.stderr.write(f"   ⏱️  {name:<10}: {duration:.3f}ms (Success)\n")
    except OSError as e:
        sys.stderr.write(f"   ❌ {name:<10}: FAILED ({e})\n")

print(f"--- MATRIX START: MODE={os.environ.get('AIS_SHELL_MODE', 'UNSET')} ---", file=sys.stderr)

# 1. Standard Streams
probe(1, "STDOUT")
probe(2, "STDERR")

# 2. FD3 (often used for signaling)
probe(3, "FD3")

# 3. Direct TTY (bypasses pipes?)
try:
    with open("/dev/tty", "w") as tty:
        probe(tty.fileno(), "DEV_TTY")
except Exception:
    sys.stderr.write("   ❌ DEV_TTY   : FAILED (No TTY)\n")

print("--- MATRIX END ---", file=sys.stderr)
