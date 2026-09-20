from __future__ import annotations

import sys
from contextlib import contextmanager

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


@contextmanager
def file_lock(handle):
    if sys.platform == "win32":
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        fcntl.flock(handle, fcntl.LOCK_EX)
    try:
        yield handle
    finally:
        if sys.platform == "win32":
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle, fcntl.LOCK_UN)
