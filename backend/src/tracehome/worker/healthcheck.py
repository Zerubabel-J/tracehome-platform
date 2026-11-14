"""Container health check for the worker, which has no port to probe.

The loop touches a file before every long poll (at most 20 s apart). If the file is older than
60 s, the loop is stuck, and the container is reported unhealthy so it can be replaced.
"""

import sys
import time

from tracehome.worker.__main__ import HEARTBEAT

try:
    age = time.time() - HEARTBEAT.stat().st_mtime
except FileNotFoundError:
    sys.exit(1)
sys.exit(0 if age < 60 else 1)
