from __future__ import annotations

import sys
import time

from db import check_db_connection


def main() -> int:
    timeout_seconds = 60
    start = time.monotonic()
    while time.monotonic() - start < timeout_seconds:
        if check_db_connection():
            print("Database is reachable.")
            return 0
        time.sleep(2)
    print("Database is not reachable within timeout.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
