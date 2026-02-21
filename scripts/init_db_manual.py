"""
Manual DB initialization script.

Use this when needed (e.g. after first deploy), instead of doing DB init at app startup.
"""
import sys

from database import init_db


def main() -> int:
    try:
        init_db()
        print("Database initialized successfully.")
        return 0
    except Exception as e:
        print(f"Database init failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
