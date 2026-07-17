"""
Download / verify YOLO weights for local demo.

Usage (from project root):
  python scripts/download_models.py
  python scripts/download_models.py --force
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "backend" / "models"

# Prefer the upstream / fork raw URLs (weights are ~5.2 MB each).
DEFAULT_SOURCES = {
    "pcb_aoi_v1.0.0": [
        "https://raw.githubusercontent.com/StupidDanking/pcb-aoi-agent-platform/main/backend/models/pcb_aoi_v1.0.0/best.pt",
        "https://raw.githubusercontent.com/Fayz677/pcb-aoi-agent-platform/main/backend/models/pcb_aoi_v1.0.0/best.pt",
    ],
    "pcb_aoi_v1.1.0": [
        "https://raw.githubusercontent.com/StupidDanking/pcb-aoi-agent-platform/main/backend/models/pcb_aoi_v1.1.0/best.pt",
        "https://raw.githubusercontent.com/Fayz677/pcb-aoi-agent-platform/main/backend/models/pcb_aoi_v1.1.0/best.pt",
    ],
}

MIN_BYTES = 1_000_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")

    print(f"  downloading: {url}")
    urllib.request.urlretrieve(url, tmp)

    size = tmp.stat().st_size
    if size < MIN_BYTES:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"file too small ({size} bytes), download likely failed")

    tmp.replace(dest)
    print(f"  saved: {dest} ({size} bytes)")
    print(f"  sha256: {sha256_file(dest)}")


def ensure_model(version: str, urls: list[str], force: bool) -> bool:
    dest = MODELS_DIR / version / "best.pt"

    if dest.exists() and not force and dest.stat().st_size >= MIN_BYTES:
        print(f"[ok] {version}/best.pt already present ({dest.stat().st_size} bytes)")
        return True

    print(f"[get] {version}/best.pt")
    errors: list[str] = []

    for url in urls:
        try:
            download(url, dest)
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, RuntimeError) as exc:
            errors.append(f"{url} -> {exc}")
            print(f"  failed: {exc}")

    print(f"[fail] could not download {version}/best.pt")
    for item in errors:
        print(f"  - {item}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Download PCB AOI model weights")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if best.pt already exists",
    )
    parser.add_argument(
        "--version",
        action="append",
        choices=sorted(DEFAULT_SOURCES.keys()),
        help="Only download specific version(s). Default: all.",
    )
    args = parser.parse_args()

    versions = args.version or list(DEFAULT_SOURCES.keys())
    ok = True

    for version in versions:
        if not ensure_model(version, DEFAULT_SOURCES[version], force=args.force):
            ok = False

    active = MODELS_DIR / "active_model.json"
    if ok and not active.exists():
        active.write_text('{\n  "model_name": "pcb_aoi_v1.1.0"\n}\n', encoding="utf-8")
        print(f"[ok] wrote {active.relative_to(ROOT)}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
