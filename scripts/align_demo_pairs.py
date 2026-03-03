"""
Align each demo pair so before/after show the same size and aspect ratio
(pixel-to-pixel, no stretching). The original image is the reference. We crop
the styled image to the original's aspect ratio (centered), then resize to the
original's exact dimensions. Output: styledN_aligned.jpg.

Requires: pip install Pillow

Run from repo root: python scripts/align_demo_pairs.py
"""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Pillow required. Run: pip install Pillow")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "static" / "landing" / "demo"


def center_crop_to_ratio(img: Image.Image, target_ratio: float) -> Image.Image:
    """
    Return the largest centered crop of img with aspect ratio target_ratio (w/h).
    No stretching; only cropping.
    """
    sw, sh = img.size
    # Try full width: height would be sw / target_ratio
    crop_h_from_width = sw / target_ratio
    if crop_h_from_width <= sh:
        crop_w = sw
        crop_h = int(round(crop_h_from_width))
    else:
        crop_h = sh
        crop_w = int(round(sh * target_ratio))
    left = (sw - crop_w) // 2
    top = (sh - crop_h) // 2
    return img.crop((left, top, left + crop_w, top + crop_h))


def main() -> None:
    for n in (1, 2, 3):
        orig_path = DEMO_DIR / f"original{n}.jpg"
        styled_path = DEMO_DIR / f"styled{n}.jpg"
        out_path = DEMO_DIR / f"styled{n}_aligned.jpg"
        if not orig_path.exists():
            print(f"Skip pair {n}: {orig_path.name} not found")
            continue
        if not styled_path.exists():
            print(f"Skip pair {n}: {styled_path.name} not found")
            continue

        with Image.open(orig_path) as orig:
            orig.load()
            ow, oh = orig.size
        with Image.open(styled_path) as styled:
            styled.load()

        target_ratio = ow / oh
        cropped = center_crop_to_ratio(styled, target_ratio)
        aligned = cropped.resize((ow, oh), Image.Resampling.LANCZOS)
        aligned.save(out_path, "JPEG", quality=92)
        print(f"Pair {n}: saved {out_path.name} ({ow}x{oh}), aligned to original{n}.jpg")


if __name__ == "__main__":
    main()
