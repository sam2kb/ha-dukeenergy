"""Build the Chrome extension zip attached to GitHub releases."""

from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "chrome-extension"
OUTPUT = ROOT / "dist" / "chrome-extension.zip"
SKIP_NAMES = frozenset({".DS_Store", "README.md"})


def main() -> None:
    """Zip the unpacked extension into dist/chrome-extension.zip."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path
        for path in SOURCE.rglob("*")
        if path.is_file() and path.name not in SKIP_NAMES
    )
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(SOURCE))
    sys.stdout.write(
        f"wrote {OUTPUT.relative_to(ROOT)} "
        f"({OUTPUT.stat().st_size} bytes, {len(files)} files)\n"
    )


if __name__ == "__main__":
    main()
