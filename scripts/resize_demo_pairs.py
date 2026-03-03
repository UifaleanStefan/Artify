"""
Resize each demo styled image to match its original's dimensions so the
before/after comparison slider displays them aligned.

Requires: pip install Pillow

Run from repo root: python scripts/resize_demo_pairs.py
"""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Pillow required. Run: pip install Pillow")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "static" / "landing" / "demo"


def main() -> None:
    for n in (1, 2, 3):
        orig_path = DEMO_DIR / f"original{n}.jpg"
        styled_path = DEMO_DIR / f"styled{n}.jpg"
        if not orig_path.exists():
            print(f"Skip pair {n}: {orig_path.name} not found")
            continue
        if not styled_path.exists():
            print(f"Skip pair {n}: {styled_path.name} not found")
            continue

        with Image.open(orig_path) as orig:
            target_size = orig.size  # (width, height)
        with Image.open(styled_path) as styled:
            if styled.size == target_size:
                print(f"Pair {n}: already {target_size[0]}x{target_size[1]}, skip")
                continue
            resized = styled.resize(target_size, Image.Resampling.LANCZOS)
            resized.save(styled_path, "JPEG", quality=92)
        print(f"Pair {n}: resized {styled_path.name} to {target_size[0]}x{target_size[1]}")


if __name__ == "__main__":
    main()
