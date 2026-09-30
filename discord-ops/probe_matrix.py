import sys
import os
import time
import fcntl

def write_probe(fd, name):
    try:
        start = time.time_ns()
        msg = f"🔮 PROBE[{name}] TS={start}\n"
        os.write(fd, msg.encode())
        end = time.time_ns()
        duration = (end - start) / 1000000.0 # ms
        # Write metadata to actual stderr (fd 2) so we can see timing even if target fd is swallowed
        sys.stderr.write(f"   ⏱️  {name:<10}: {duration:.3f}ms\n")
    except OSError as e:
        sys.stderr.write(f"   ❌ {name:<10}: FAILED ({e})\n")

print(f"--- PROBE MATRIX: MODE={os.environ.get('AIS_SHELL_MODE', 'UNSET')} ---", file=sys.stderr)

# 1. Standard Streams
write_probe(1, "STDOUT")
write_probe(2, "STDERR")

# 2. File Descriptors (Common usage)
write_probe(3, "FD3")

# 3. Direct Device Access
try:
    with open("/dev/tty", "w") as tty:
        write_probe(tty.fileno(), "DEV_TTY")
except Exception:
    sys.stderr.write("   ❌ DEV_TTY   : FAILED (No TTY)\n")

