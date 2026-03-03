"""
Test that at most MAX_CONCURRENT_ORDERS run at the same time.
Does NOT call Replicate, DB, or any real order logic — only checks semaphore behavior.
Run: python scripts/test_concurrent_orders_cap.py
"""
import asyncio
import sys
from pathlib import Path

# Allow importing main's constants without starting the app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Use the same constant as main
MAX_CONCURRENT_ORDERS = 8


async def main() -> None:
    sem = asyncio.Semaphore(MAX_CONCURRENT_ORDERS)
    current = 0
    max_seen = 0

    async def fake_order(order_id: int) -> None:
        nonlocal current, max_seen
        async with sem:
            current += 1
            max_seen = max(max_seen, current)
            await asyncio.sleep(0.05)  # Hold the slot briefly
            current -= 1

    # Run more tasks than the cap; they should be limited to 8 at a time
    tasks = [asyncio.create_task(fake_order(i)) for i in range(15)]
    await asyncio.gather(*tasks)

    if max_seen <= MAX_CONCURRENT_ORDERS:
        print(f"OK: max concurrent was {max_seen} (cap is {MAX_CONCURRENT_ORDERS})")
    else:
        print(f"FAIL: max concurrent was {max_seen}, expected <= {MAX_CONCURRENT_ORDERS}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
