"""
PCB AOI YOLO 数据集标注可视化工具

功能：
1. 随机抽样查看 YOLO 标注框
2. 支持指定 train / val / test 数据划分
3. 支持保存单张可视化图片
4. 支持生成多张图片的网格概览图
5. 适配本项目数据集结构：

datasets/pcb_defect/
├── train/
│   ├── images/
│   └── labels/
├── val/
│   ├── images/
│   └── labels/
├── test/
│   ├── images/
│   └── labels/
└── data.yaml
"""

import argparse
import random
from pathlib import Path

import cv2
import numpy as np
import yaml


# 当前文件位置：backend/tools/visualize_annotations.py
# 项目根目录：D:/shixi/rsod-agent-platform
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIR = PROJECT_ROOT / "datasets" / "pcb_defect"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "backend" / "runs" / "visualize_annotations"


COLORS = [
    (0, 255, 0),
    (255, 0, 0),
    (0, 0, 255),
    (255, 255, 0),
    (0, 255, 255),
    (255, 0, 255),
    (128, 255, 0),
    (255, 128, 0),
    (0, 128, 255),
    (128, 0, 255),
]


def load_class_names(dataset_dir: Path) -> dict[int, str]:
    """从 data.yaml 中读取类别名称。"""
    yaml_path = dataset_dir / "data.yaml"

    if not yaml_path.exists():
        print(f"[警告] 未找到 data.yaml：{yaml_path}")
        return {}

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    names = data.get("names", {})

    if isinstance(names, list):
        return {i: name for i, name in enumerate(names)}

    if isinstance(names, dict):
        return {int(k): v for k, v in names.items()}

    return {}


def collect_image_label_pairs(dataset_dir: Path, split: str) -> list[tuple[Path, Path]]:
    """收集某个 split 下的图像和标签文件配对。"""
    image_dir = dataset_dir / split / "images"
    label_dir = dataset_dir / split / "labels"

    if not image_dir.exists():
        raise FileNotFoundError(f"图像目录不存在：{image_dir}")

    if not label_dir.exists():
        raise FileNotFoundError(f"标签目录不存在：{label_dir}")

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    image_files = [
        p for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in image_exts
    ]

    pairs = []
    for image_path in image_files:
        label_path = label_dir / f"{image_path.stem}.txt"
        pairs.append((image_path, label_path))

    return pairs


def draw_yolo_boxes(image: np.ndarray, label_path: Path, class_names: dict[int, str]) -> np.ndarray:
    """在图像上绘制 YOLO 标注框。"""
    h, w = image.shape[:2]

    if not label_path.exists():
        return image

    with open(label_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) != 5:
            continue

        try:
            class_id = int(parts[0])
            x_center = float(parts[1])
            y_center = float(parts[2])
            box_w = float(parts[3])
            box_h = float(parts[4])
        except ValueError:
            continue

        x1 = int((x_center - box_w / 2) * w)
        y1 = int((y_center - box_h / 2) * h)
        x2 = int((x_center + box_w / 2) * w)
        y2 = int((y_center + box_h / 2) * h)

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w - 1))
        y2 = max(0, min(y2, h - 1))

        color = COLORS[class_id % len(COLORS)]
        class_name = class_names.get(class_id, f"class_{class_id}")

        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

        label_text = f"{class_id}: {class_name}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.55
        thickness = 1

        (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)

        label_bg_y1 = max(0, y1 - text_h - 8)
        label_bg_y2 = y1

        cv2.rectangle(
            image,
            (x1, label_bg_y1),
            (x1 + text_w + 6, label_bg_y2),
            color,
            -1,
        )

        cv2.putText(
            image,
            label_text,
            (x1 + 3, y1 - 5),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )

    return image


def visualize_samples(
    dataset_dir: Path,
    output_dir: Path,
    split: str,
    count: int,
    show: bool,
) -> None:
    """随机抽样可视化。"""
    class_names = load_class_names(dataset_dir)
    pairs = collect_image_label_pairs(dataset_dir, split)

    if not pairs:
        print(f"[错误] {split} 中没有找到图片")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    samples = random.sample(pairs, min(count, len(pairs)))

    print(f"[信息] 数据集目录：{dataset_dir}")
    print(f"[信息] split：{split}")
    print(f"[信息] 共找到图片：{len(pairs)}")
    print(f"[信息] 本次抽样：{len(samples)}")
    print(f"[信息] 输出目录：{output_dir}")

    for image_path, label_path in samples:
        image = cv2.imread(str(image_path))

        if image is None:
            print(f"[跳过] 无法读取图片：{image_path}")
            continue

        annotated = draw_yolo_boxes(image, label_path, class_names)

        cv2.putText(
            annotated,
            f"{split} | {image_path.name}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        output_path = output_dir / f"vis_{split}_{image_path.name}"
        cv2.imwrite(str(output_path), annotated)
        print(f"[保存] {output_path}")

        if show:
            cv2.imshow("YOLO Annotation", annotated)
            key = cv2.waitKey(0) & 0xFF
            cv2.destroyAllWindows()

            if key == ord("q"):
                break


def generate_grid(
    dataset_dir: Path,
    output_dir: Path,
    split: str,
    count: int,
    grid_cols: int,
) -> None:
    """生成多张图片拼接的网格概览图。"""
    class_names = load_class_names(dataset_dir)
    pairs = collect_image_label_pairs(dataset_dir, split)

    if not pairs:
        print(f"[错误] {split} 中没有找到图片")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    samples = random.sample(pairs, min(count, len(pairs)))

    thumb_w = 320
    thumb_h = 240
    grid_rows = int(np.ceil(len(samples) / grid_cols))

    grid_img = np.ones(
        (grid_rows * thumb_h, grid_cols * thumb_w, 3),
        dtype=np.uint8,
    ) * 255

    for idx, (image_path, label_path) in enumerate(samples):
        image = cv2.imread(str(image_path))

        if image is None:
            continue

        annotated = draw_yolo_boxes(image, label_path, class_names)
        annotated = cv2.resize(annotated, (thumb_w, thumb_h))

        row = idx // grid_cols
        col = idx % grid_cols

        y1 = row * thumb_h
        y2 = y1 + thumb_h
        x1 = col * thumb_w
        x2 = x1 + thumb_w

        grid_img[y1:y2, x1:x2] = annotated

        cv2.putText(
            grid_img,
            image_path.name[:28],
            (x1 + 5, y1 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

    output_path = output_dir / f"grid_{split}_{len(samples)}.jpg"
    cv2.imwrite(str(output_path), grid_img)

    print(f"[保存] 网格概览图：{output_path}")


def main():
    parser = argparse.ArgumentParser(description="PCB AOI YOLO 标注可视化工具")

    parser.add_argument(
        "--dataset",
        type=str,
        default=str(DEFAULT_DATASET_DIR),
        help="数据集根目录，默认 datasets/pcb_defect",
    )

    parser.add_argument(
        "--split",
        type=str,
        default="train",
        choices=["train", "val", "test"],
        help="数据划分：train / val / test",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=8,
        help="随机抽样数量",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="输出目录",
    )

    parser.add_argument(
        "--show",
        action="store_true",
        help="是否弹窗显示图片",
    )

    parser.add_argument(
        "--grid",
        action="store_true",
        help="是否生成网格概览图",
    )

    parser.add_argument(
        "--grid-cols",
        type=int,
        default=4,
        help="网格图每行列数",
    )

    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    output_dir = Path(args.output)

    if args.grid:
        generate_grid(
            dataset_dir=dataset_dir,
            output_dir=output_dir,
            split=args.split,
            count=args.count,
            grid_cols=args.grid_cols,
        )
    else:
        visualize_samples(
            dataset_dir=dataset_dir,
            output_dir=output_dir,
            split=args.split,
            count=args.count,
            show=args.show,
        )


if __name__ == "__main__":
    main()