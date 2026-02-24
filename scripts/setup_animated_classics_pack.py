"""
Copy the last 15 image files from user Downloads into static/landing/styles/animated-classics/
and rename to animated-classics-01.* through animated-classics-15.* in this exact label order:

  01 = Toy Story
  02 = Frozen
  ...
  11 = Beauty and the Beast
  12 = The Simpsons Movie
  13 = Despicable Me
  14 = Hotel Transylvania
  15 = Aladdin (replacement image – must be the last/newest file)

Before running: place your 15 images in Downloads so that the OLDEST (first downloaded) is
Toy Story and the NEWEST (last) is Aladdin. Then run from project root:

  python scripts/setup_animated_classics_pack.py
"""
import os
import shutil
from pathlib import Path

DOWNLOADS = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", ""))) / "Downloads"
TARGET_DIR = Path(__file__).resolve().parent.parent / "static" / "landing" / "styles" / "animated-classics"

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")


def get_last_15_images_oldest_first():
    if not DOWNLOADS.exists():
        raise SystemExit("Downloads folder not found")
    files = [f for f in DOWNLOADS.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXT]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)  # newest first
    last15 = files[:15]
    last15.reverse()  # oldest first -> 01 = first in list
    return last15


def main():
    target = TARGET_DIR
    target.mkdir(parents=True, exist_ok=True)
    sources = get_last_15_images_oldest_first()
    if len(sources) < 15:
        raise SystemExit(f"Only {len(sources)} image files in Downloads; need 15")
    labels = [
        "Toy Story", "Frozen", "The Incredibles", "Shrek", "Tangled",
        "How to Train Your Dragon", "Spider-Man: Into the Spider-Verse", "The Lego Movie",
        "The Mitchells vs. the Machines", "The Lion King", "Beauty and the Beast",
        "The Simpsons Movie", "Despicable Me", "Hotel Transylvania", "Aladdin",
    ]
    for i, src in enumerate(sources, start=1):
        # Always use .jpg so backend and frontend paths match
        dest_name = f"animated-classics-{i:02d}.jpg"
        dest = target / dest_name
        shutil.copy2(src, dest)
        print(f"  {i:02d} {src.name} -> {dest_name}  ({labels[i-1]})")
    print(f"Done. {len(sources)} files in {target}")
    print("Order: 01 = Toy Story … 15 = Aladdin.")


if __name__ == "__main__":
    main()
