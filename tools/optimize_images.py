"""Compress the site's PNG and JPEG images in place, before they are committed.

    uv run python -m tools.optimize_images            # new or changed images
    uv run python -m tools.optimize_images --staged   # staged ones, re-staged
    uv run python -m tools.optimize_images FILE...    # just these
    uv run python -m tools.optimize_images --all      # every image under docs/

The --staged form is what .githooks/pre-commit runs, so with the hook enabled
(git config core.hooksPath .githooks) nothing needs to be run by hand.

This used to happen at build time through Material's "optimize" plugin. That
plugin has a thread race (it removes a file from MkDocs' collection after a
worker may already have renamed it) that intermittently killed the deploy, so
images are now compressed once, at the source, and the build just copies them.

The settings are the plugin's defaults, so the output matches what it shipped:
pngquant at speed 3 with metadata stripped, and JPEG at quality 60,
progressive. A result that is not smaller than the original is discarded.

Compression is lossy, so an image that already looks compressed is skipped:
a palette PNG (what pngquant writes) or a progressive JPEG (what this writes).
That makes every mode safe to repeat. --force compresses those anyway.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SUFFIXES = {".png", ".jpg", ".jpeg"}


def _git_paths(*args: str) -> list[Path]:
    out = subprocess.run(
        ["git", *args, "--", "docs"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    return [ROOT / line for line in out.splitlines() if line]


def _changed() -> list[Path]:
    """Images that are untracked, or differ from HEAD (staged or not)."""
    paths = _git_paths("ls-files", "--others", "--exclude-standard")
    paths += _git_paths("diff", "--name-only", "--diff-filter=AM", "HEAD")
    return sorted({p for p in paths if p.exists()})


def _staged() -> list[Path]:
    """Images added or modified in the index, i.e. in the commit being made."""
    paths = _git_paths("diff", "--cached", "--name-only", "--diff-filter=AM")
    return [p for p in paths if p.exists()]


def _already_compressed(path: Path) -> bool:
    with Image.open(path) as image:
        if image.format == "PNG":
            return image.mode in ("P", "PA")
        return bool(image.info.get("progressive"))


def _compress(src: Path, dst: Path) -> None:
    if src.suffix.lower() == ".png":
        # --skip-if-larger: pngquant writes nothing if it cannot do better
        subprocess.run(
            ["pngquant", "--force", "--skip-if-larger", "--speed", "3",
             "--strip", "--output", str(dst), str(src)],
            check=False,
        )
    else:
        with Image.open(src) as image:
            image.save(dst, "jpeg", quality=60, progressive=True)


def optimize(path: Path) -> tuple[int, int]:
    before = path.stat().st_size
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / path.name
        _compress(path, out)
        if out.exists() and out.stat().st_size < before:
            shutil.move(out, path)
    return before, path.stat().st_size


def _size(n: int) -> str:
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} kB"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--all", action="store_true",
                        help="every image under docs/, not just changed ones")
    parser.add_argument("--staged", action="store_true",
                        help="staged images only, and stage the result")
    parser.add_argument("--force", action="store_true",
                        help="also compress images that look compressed")
    args = parser.parse_args()

    if shutil.which("pngquant") is None:
        if args.staged:
            # From the pre-commit hook: warn, but never block a commit
            print("optimize_images: pngquant not found, images not compressed "
                  "(brew install pngquant)", file=sys.stderr)
            return 0
        sys.exit("pngquant not found: brew install pngquant")

    if args.files:
        paths = [p.resolve() for p in args.files]
    elif args.all:
        paths = sorted(DOCS.rglob("*"))
    elif args.staged:
        paths = _staged()
    else:
        paths = _changed()
    paths = [p for p in paths if p.suffix.lower() in SUFFIXES]
    if not args.force:
        paths = [p for p in paths if not _already_compressed(p)]

    total_before = total_after = 0
    for path in paths:
        before, after = optimize(path)
        total_before += before
        total_after += after
        saved = f"-{(1 - after / before) * 100:4.1f}%" if after < before else "   kept"
        print(f"{saved}  {path.relative_to(ROOT)}")

    if args.staged and paths:
        subprocess.run(["git", "add", "--", *map(str, paths)], cwd=ROOT, check=True)

    if paths:
        print(f"{_size(total_before)} -> {_size(total_after)}")
    elif not args.staged:
        print("No uncompressed images to optimize.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
