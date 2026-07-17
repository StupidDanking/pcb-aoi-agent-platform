"""
Build a small demo PCB defect dataset (YOLO format).

What it does:
1. Downloads public demo PCB images (PKU Tiny-Defect-Detection demos)
2. Auto-labels them with local backend/models/*/best.pt
3. Writes train / val / test splits under datasets/pcb_defect/

This sample is for smoke tests and first-run demos.
For real training, replace it with the full PKU PCB dataset.

Usage (from project root):
  python scripts/download_models.py
  python scripts/prepare_sample_dataset.py
  python scripts/check_yolo_dataset.py
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets" / "pcb_defect"
RAW_DIR = ROOT / "datasets" / "raw" / "pcb_demo_images"

CLASS_NAMES = {
    0: "mouse_bite",
    1: "spur",
    2: "missing_hole",
    3: "short",
    4: "open_circuit",
    5: "spurious_copper",
}

# Public demo images from Tiny-Defect-Detection-for-PCB (PKU PCB defect taxonomy).
_BASE = "https://raw.githubusercontent.com/Ixiaohuihuihui/Tiny-Defect-Detection-for-PCB/master"
DEMO_IMAGE_URLS = [
    f"{_BASE}/tools/demos/m13.jpg",
    f"{_BASE}/tools/demos/s14.jpg",
    f"{_BASE}/tools/demos/spurs%20(12).jpg",
    f"{_BASE}/tools/demos_backup/01_missing_hole_01.jpg",
    f"{_BASE}/tools/demos_backup/01_mouse_bite_05.jpg",
    f"{_BASE}/tools/demos_backup/01_open_circuit_12.jpg",
    f"{_BASE}/tools/demos_backup/01_spurious_copper_11.jpg",
    f"{_BASE}/tools/demos_backup/04_missing_hole_01.jpg",
    f"{_BASE}/tools/demos_backup/04_mouse_bite_10.jpg",
    f"{_BASE}/tools/demos_backup/04_open_circuit_10.jpg",
    f"{_BASE}/tools/demos_backup/04_spurious_copper_04.jpg",
    f"{_BASE}/tools/demos_backup/07_missing_hole_01.jpg",
    f"{_BASE}/tools/demos_backup/07_mouse_bite_08.jpg",
    f"{_BASE}/tools/demos_backup/07_open_circuit_09.jpg",
    f"{_BASE}/tools/demos_backup/07_spurious_copper_07.jpg",
    f"{_BASE}/tools/demos_backup/08_missing_hole_07.jpg",
    f"{_BASE}/tools/demos_backup/08_open_circuit_06.jpg",
    f"{_BASE}/tools/demos_backup/08_spur_07.jpg",
    f"{_BASE}/tools/demos_backup/09_missing_hole_05.jpg",
    f"{_BASE}/tools/demos_backup/10_missing_hole_03.jpg",
    f"{_BASE}/tools/demos_backup/10_mouse_bite_03.jpg",
    f"{_BASE}/tools/demos_backup/10_open_circuit_04.jpg",
    f"{_BASE}/tools/demos_backup/10_short_02.jpg",
    f"{_BASE}/tools/demos_backup/10_spur_03.jpg",
    f"{_BASE}/tools/demos_backup/11_missing_hole_06.jpg",
    f"{_BASE}/tools/demos_backup/11_mouse_bite_05.jpg",
    f"{_BASE}/tools/demos_backup/11_open_circuit_07.jpg",
    f"{_BASE}/tools/demos_backup/11_short_05.jpg",
    f"{_BASE}/tools/demos_backup/12_missing_hole_04.jpg",
    f"{_BASE}/tools/demos_backup/12_mouse_bite_02.jpg",
    f"{_BASE}/tools/demos_backup/12_open_circuit_06.jpg",
    f"{_BASE}/tools/demos_backup/12_short_02.jpg",
    f"{_BASE}/tools/demos_backup/12_spur_02.jpg",
]


DATA_YAML = """# Relative to this file's directory. Works on any machine after clone.
path: .
train: train/images
val: val/images
test: test/images

names:
  0: mouse_bite
  1: spur
  2: missing_hole
  3: short
  4: open_circuit
  5: spurious_copper
"""


def find_best_pt() -> Path:
    candidates = [
        ROOT / "backend" / "models" / "pcb_aoi_v1.1.0" / "best.pt",
        ROOT / "backend" / "models" / "pcb_aoi_v1.0.0" / "best.pt",
    ]
    models_dir = ROOT / "backend" / "models"
    if models_dir.exists():
        candidates.extend(sorted(models_dir.glob("**/best.pt"), reverse=True))

    for path in candidates:
        if path.exists() and path.stat().st_size > 1_000_000:
            return path

    raise FileNotFoundError(
        "best.pt not found. Run: python scripts/download_models.py"
    )


def safe_name(url: str, index: int) -> str:
    name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
    name = name.replace(" ", "_").replace("(", "").replace(")", "")
    stem = Path(name).stem or f"demo_{index:02d}"
    suffix = Path(name).suffix.lower() or ".jpg"
    return f"{index:02d}_{stem}{suffix}"


def download_images(force: bool) -> list[Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    seen: set[str] = set()

    for index, url in enumerate(DEMO_IMAGE_URLS, start=1):
        filename = safe_name(url, index)
        if filename in seen:
            continue
        seen.add(filename)

        dest = RAW_DIR / filename
        if dest.exists() and not force and dest.stat().st_size > 1000:
            saved.append(dest)
            continue

        print(f"download image: {filename}")
        try:
            urllib.request.urlretrieve(url, dest)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f"  skip ({exc})")
            dest.unlink(missing_ok=True)
            continue

        if dest.stat().st_size < 1000:
            print("  skip (too small)")
            dest.unlink(missing_ok=True)
            continue

        saved.append(dest)

    if len(saved) < 12:
        raise RuntimeError(f"only downloaded {len(saved)} images, need more for a sample")

    return saved


def boxes_to_yolo_lines(result) -> list[str]:
    lines: list[str] = []
    if result.boxes is None or len(result.boxes) == 0:
        return lines

    for box in result.boxes:
        cls_id = int(box.cls.item())
        if cls_id not in CLASS_NAMES:
            continue

        # xywhn: normalized center_x, center_y, width, height
        x, y, w, h = box.xywhn[0].tolist()
        lines.append(f"{cls_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

    return lines


def auto_label(images: list[Path], conf: float, device: str) -> list[tuple[Path, list[str]]]:
    from ultralytics import YOLO

    model_path = find_best_pt()
    print(f"using model: {model_path}")
    model = YOLO(str(model_path))

    labeled: list[tuple[Path, list[str]]] = []
    empty = 0

    for image_path in images:
        results = model.predict(
            source=str(image_path),
            conf=conf,
            device=device,
            verbose=False,
        )
        lines = boxes_to_yolo_lines(results[0])
        if not lines:
            empty += 1
            print(f"  no boxes: {image_path.name}")
            continue

        labeled.append((image_path, lines))
        print(f"  labeled: {image_path.name} ({len(lines)} boxes)")

    print(f"labeled={len(labeled)} empty={empty}")
    if len(labeled) < 10:
        raise RuntimeError("too few labeled images for sample dataset")

    return labeled


def split_items(
    items: list[tuple[Path, list[str]]],
    seed: int,
) -> dict[str, list[tuple[Path, list[str]]]]:
    rng = random.Random(seed)
    shuffled = items[:]
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_val = max(2, n // 6)
    n_test = max(2, n // 6)
    n_train = n - n_val - n_test
    if n_train < 6:
        n_train = max(6, n - 4)
        n_val = max(2, (n - n_train) // 2)
        n_test = n - n_train - n_val

    return {
        "train": shuffled[:n_train],
        "val": shuffled[n_train:n_train + n_val],
        "test": shuffled[n_train + n_val:],
    }


def reset_split_dirs() -> None:
    for split in ("train", "val", "test"):
        for sub in ("images", "labels"):
            path = DATASET_DIR / split / sub
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)


def write_split(splits: dict[str, list[tuple[Path, list[str]]]]) -> None:
    reset_split_dirs()
    counts: dict[str, int] = {}

    for split, items in splits.items():
        counts[split] = len(items)
        for image_path, lines in items:
            stem = image_path.stem
            suffix = image_path.suffix.lower()
            dest_image = DATASET_DIR / split / "images" / f"{stem}{suffix}"
            dest_label = DATASET_DIR / split / "labels" / f"{stem}.txt"
            shutil.copy2(image_path, dest_image)
            dest_label.write_text("\n".join(lines) + "\n", encoding="utf-8")

    (DATASET_DIR / "data.yaml").write_text(DATA_YAML, encoding="utf-8")
    print("split counts:", counts)


def write_readme(total: int) -> None:
    readme = DATASET_DIR / "README.md"
    readme.write_text(
        f"""# PCB Defect Sample Dataset

Small demo dataset for first-run smoke tests (`train/val/test`, YOLO TXT labels).

- Images: public demos from [Tiny-Defect-Detection-for-PCB](https://github.com/Ixiaohuihuihui/Tiny-Defect-Detection-for-PCB)
- Labels: auto-generated with this project's `best.pt` (not manual gold labels)
- Size: ~{total} labeled images

## Rebuild

```bash
python scripts/download_models.py
python scripts/prepare_sample_dataset.py
python scripts/check_yolo_dataset.py
```

## Full dataset

For real training, use the full PKU PCB defect dataset (10k+ images) and place it here:

```text
datasets/pcb_defect/
  train/images + labels
  val/images + labels
  test/images + labels
  data.yaml
```

Keep `data.yaml` using relative `path: .`.
""",
        encoding="utf-8",
    )


def class_stats(splits: dict[str, list[tuple[Path, list[str]]]]) -> None:
    counter: dict[int, int] = defaultdict(int)
    for items in splits.values():
        for _, lines in items:
            for line in lines:
                class_id = int(line.split()[0])
                counter[class_id] += 1

    print("class box counts:")
    for class_id in sorted(CLASS_NAMES):
        print(f"  {class_id} {CLASS_NAMES[class_id]}: {counter.get(class_id, 0)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare PCB defect sample dataset")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--device", default=None, help="cpu / 0. Default: auto")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    device = args.device
    if device is None:
        try:
            import torch

            device = "0" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

    print(f"device={device}")
    images = download_images(force=args.force_download)
    print(f"images ready: {len(images)}")

    labeled = auto_label(images, conf=args.conf, device=device)
    splits = split_items(labeled, seed=args.seed)
    write_split(splits)
    write_readme(len(labeled))
    class_stats(splits)

    print(f"\nDone. Dataset root: {DATASET_DIR}")
    print("Next: python scripts/check_yolo_dataset.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
