"""
Copy the last 15 files from user Downloads into static/landing/styles/evolution-portraits/
and rename to evolution-portraits-01.* through evolution-portraits-15.* in the correct order:
- The OLDEST of the 15 (first downloaded) -> evolution-portraits-01 (Fayum Mummy Portraits)
- The NEWEST of the 15 (last downloaded)  -> evolution-portraits-15 (Marilyn Diptych)

Order (oldest to newest in Downloads):
  01 Fayum Mummy Portraits
  02 Nefertari in the Tomb of Nefertari
  03 Portrait of a Young Woman (Medieval)
  04 Christ Pantocrator
  05 Mona Lisa
  06 Portrait of Baldassare Castiglione
  07 Self-Portrait (Renaissance)
  08 Girl with a Pearl Earring
  09 Self-Portrait with Two Circles
  10 Portrait of Madame X
  11 Self-Portrait with Bandaged Ear
  12 Les Demoiselles d'Avignon
  13 Portrait of Dora Maar
  14 Self-Portrait with Thorn Necklace and Hummingbird
  15 Marilyn Diptych

Run from project root: python scripts/setup_evolution_portraits_pack.py
"""
import os
import shutil
from pathlib import Path

DOWNLOADS = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
TARGET_DIR = Path(__file__).resolve().parent.parent / "static" / "landing" / "styles" / "evolution-portraits"

# Last 15 files by modification time (newest first), then reverse so oldest = 01
def get_last_15_oldest_first():
    if not DOWNLOADS.exists():
        raise SystemExit("Downloads folder not found")
    files = [f for f in DOWNLOADS.iterdir() if f.is_file()]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)  # newest first
    last15 = files[:15]
    last15.reverse()  # oldest first -> first in list = evolution-portraits-01
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
        dest_name = f"evolution-portraits-{i:02d}{ext}"
        dest = target / dest_name
        shutil.copy2(src, dest)
        print(f"  {src.name} -> {dest_name}")
    print(f"Done. {len(sources)} files in {target}")
    print("Order: 01 = first downloaded (oldest), 15 = last downloaded (newest).")


if __name__ == "__main__":
    main()
