"""
Copy the last 15 files from user Downloads into static/landing/styles/ancient-worlds/
and rename to ancient-worlds-01.* through ancient-worlds-15.* in the correct order:
- The OLDEST of the 15 (first downloaded) -> ancient-worlds-01 (Nebamun Hunting...)
- The NEWEST of the 15 (last downloaded)  -> ancient-worlds-15 (Han Dynasty...)
Run from project root: python scripts/setup_ancient_worlds_pack.py
"""
import os
import shutil
from pathlib import Path

DOWNLOADS = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
TARGET_DIR = Path(__file__).resolve().parent.parent / "static" / "landing" / "styles" / "ancient-worlds"

# Last 15 files by modification time (newest first), then we reverse so oldest = 01
def get_last_15_oldest_first():
    if not DOWNLOADS.exists():
        raise SystemExit("Downloads folder not found")
    files = [f for f in DOWNLOADS.iterdir() if f.is_file()]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)  # newest first
    last15 = files[:15]
    last15.reverse()  # oldest first -> first in list = ancient-worlds-01
    return last15


def main():
    target = TARGET_DIR
    target.mkdir(parents=True, exist_ok=True)
    sources = get_last_15_oldest_first()
    if len(sources) < 15:
        raise SystemExit(f"Only {len(sources)} files in Downloads; need 15")
    for i, src in enumerate(sources, start=1):
        ext = src.suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"):
            ext = ".jpg"
        dest_name = f"ancient-worlds-{i:02d}{ext}"
        dest = target / dest_name
        shutil.copy2(src, dest)
        print(f"  {src.name} -> {dest_name}")
    print(f"Done. {len(sources)} files in {target}")
    print("Order: 01 = first downloaded (oldest), 15 = last downloaded (newest).")


if __name__ == "__main__":
    main()
