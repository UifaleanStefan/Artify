"""
Copy the last 15 files from user Downloads into static/landing/styles/modern-abstract/
and rename to modern-abstract-01.jpg, ..., modern-abstract-15.jpg (or .png when source is PNG).
Run from project root: python scripts/setup_modern_abstract_pack.py
"""
import os
import shutil
from pathlib import Path

DOWNLOADS = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
TARGET_DIR = Path(__file__).resolve().parent.parent / "static" / "landing" / "styles" / "modern-abstract"

# Last 15 files by modification time (most recent first)
def get_last_15_files():
    if not DOWNLOADS.exists():
        raise SystemExit("Downloads folder not found")
    files = [f for f in DOWNLOADS.iterdir() if f.is_file()]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files[:15]

def main():
    target = TARGET_DIR
    target.mkdir(parents=True, exist_ok=True)
    sources = get_last_15_files()
    if len(sources) < 15:
        raise SystemExit(f"Only {len(sources)} files in Downloads; need 15")
    for i, src in enumerate(sources, start=1):
        ext = src.suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"):
            ext = ".jpg"
        dest_name = f"modern-abstract-{i:02d}{ext}"
        dest = target / dest_name
        shutil.copy2(src, dest)
        print(f"  {src.name} -> {dest_name}")
    print(f"Done. {len(sources)} files in {target}")

if __name__ == "__main__":
    main()
