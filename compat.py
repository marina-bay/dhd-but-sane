import sys

PY3 = sys.version_info[0] == 3

if not PY3:
    range = xrange
