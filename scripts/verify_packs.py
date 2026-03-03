"""
Utility script to print and check alignment between:
- PACK_PATHS (image URLs)
- PACK_LABELS (painting title, artist)
- PACK_PROMPTS (style transfer prompts)

Run with:
    python -m scripts.verify_packs

This does not modify any data; it only prints a human-readable table so you
can visually compare each entry against the actual JPGs in static/landing/styles/.
"""

from __future__ import annotations

from textwrap import shorten

from main import (  # type: ignore
    ANCIENT_WORLDS_PACK_LABELS,
    ANCIENT_WORLDS_PACK_PATHS,
    ANCIENT_WORLDS_PACK_PROMPTS,
    EVOLUTION_PORTRAITS_PACK_LABELS,
    EVOLUTION_PORTRAITS_PACK_PATHS,
    EVOLUTION_PORTRAITS_PACK_PROMPTS,
    IMPRESSION_COLOR_PACK_LABELS,
    IMPRESSION_COLOR_PACK_PATHS,
    IMPRESSION_COLOR_PACK_PROMPTS,
    MASTERS_PACK_LABELS,
    MASTERS_PACK_PATHS,
    MASTERS_PACK_PROMPTS,
    MODERN_ABSTRACT_PACK_LABELS,
    MODERN_ABSTRACT_PACK_PATHS,
    MODERN_ABSTRACT_PACK_PROMPTS,
    ROYALTY_PORTRAITS_PACK_LABELS,
    ROYALTY_PORTRAITS_PACK_PATHS,
    ROYALTY_PORTRAITS_PACK_PROMPTS,
)


def _print_pack(name: str, paths: list[str], labels: list[tuple[str, str]], prompts: list[str]) -> None:
    print("=" * 80)
    print(f"PACK: {name}  (entries={len(paths)})")
    print("-" * 80)
    print(f"{'Idx':>3}  {'File':<40}  {'Title':<35}  {'Author':<25}  {'Prompt (start)':<40}")
    print("-" * 80)

    n = len(paths)
    for i in range(n):
        file_name = (paths[i] or "").rsplit("/", 1)[-1]
        title, author = labels[i]
        prompt_start = shorten(prompts[i].split("Preserve", 1)[0].strip(), width=60, placeholder="…")
        print(
            f"{i:>3}  {file_name:<40}  {shorten(title, 35):<35}  "
            f"{shorten(author, 25):<25}  {prompt_start:<40}"
        )


def main() -> None:
    packs = [
        ("Masters", MASTERS_PACK_PATHS, MASTERS_PACK_LABELS, MASTERS_PACK_PROMPTS),
        ("Impression & Color", IMPRESSION_COLOR_PACK_PATHS, IMPRESSION_COLOR_PACK_LABELS, IMPRESSION_COLOR_PACK_PROMPTS),
        ("Modern & Abstract", MODERN_ABSTRACT_PACK_PATHS, MODERN_ABSTRACT_PACK_LABELS, MODERN_ABSTRACT_PACK_PROMPTS),
        ("Ancient Worlds", ANCIENT_WORLDS_PACK_PATHS, ANCIENT_WORLDS_PACK_LABELS, ANCIENT_WORLDS_PACK_PROMPTS),
        ("Evolution of Portraits", EVOLUTION_PORTRAITS_PACK_PATHS, EVOLUTION_PORTRAITS_PACK_LABELS, EVOLUTION_PORTRAITS_PACK_PROMPTS),
        ("Royalty & Power", ROYALTY_PORTRAITS_PACK_PATHS, ROYALTY_PORTRAITS_PACK_LABELS, ROYALTY_PORTRAITS_PACK_PROMPTS),
    ]
    for name, paths, labels, prompts in packs:
        if not (len(paths) == len(labels) == len(prompts)):
            print(
                f"[ERROR] Pack '{name}' misaligned: "
                f"paths={len(paths)} labels={len(labels)} prompts={len(prompts)}"
            )
        _print_pack(name, paths, labels, prompts)


if __name__ == "__main__":
    main()

