"""
Copy the last 15 files from user Downloads into static/landing/styles/royalty-portraits/
and rename to royalty-portraits-01.* through royalty-portraits-15.* in the correct order:
- The OLDEST of the 15 (first downloaded) -> royalty-portraits-01 (Napoleon Crossing the Alps)
- The NEWEST of the 15 (last downloaded)  -> royalty-portraits-15 (Portrait of Empress Catherine II)

Order (oldest to newest in Downloads):
  01 Napoleon Crossing the Alps
  02 Portrait of Louis XIV
  03 Portrait of Henry VIII
  04 Queen Elizabeth I Armada Portrait
  05 Equestrian Portrait of Charles I
  06 Portrait of Pope Innocent X
  07 Philip IV in Brown and Silver
  08 Portrait of Madame de Pompadour
  09 The Blue Boy
  10 Portrait of the Duke of Wellington
  11 Self-Portrait as a Nobleman
  12 Portrait of Emperor Rudolf II as Vertumnus
  13 Emperor Qianlong in Court Dress
  14 Shah Jahan on a Terrace
  15 Portrait of Empress Catherine II

Run from project root: python scripts/setup_royalty_portraits_pack.py
"""
import os
import shutil
from pathlib import Path

DOWNLOADS = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
TARGET_DIR = Path(__file__).resolve().parent.parent / "static" / "landing" / "styles" / "royalty-portraits"

# Last 15 files by modification time (newest first), then reverse so oldest = 01
def get_last_15_oldest_first():
    if not DOWNLOADS.exists():
        raise SystemExit("Downloads folder not found")
    files = [f for f in DOWNLOADS.iterdir() if f.is_file()]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)  # newest first
    last15 = files[:15]
    last15.reverse()  # oldest first -> first in list = royalty-portraits-01
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
        dest_name = f"royalty-portraits-{i:02d}{ext}"
        dest = target / dest_name
        shutil.copy2(src, dest)
        print(f"  {src.name} -> {dest_name}")
    print(f"Done. {len(sources)} files in {target}")
    print("Order: 01 = first downloaded (oldest), 15 = last downloaded (newest).")


if __name__ == "__main__":
    main()
