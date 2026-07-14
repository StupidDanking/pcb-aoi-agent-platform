from pathlib import Path


DATASET_DIR = Path("datasets/pcb_defect")

CLASS_NAMES = {
    0: "mouse_bite",
    1: "spur",
    2: "missing_hole",
    3: "short",
    4: "open_circuit",
    5: "spurious_copper",
}


def check_split(split: str):
    image_dir = DATASET_DIR / split / "images"
    label_dir = DATASET_DIR / split / "labels"

    image_files = sorted(
        list(image_dir.glob("*.jpg"))
        + list(image_dir.glob("*.jpeg"))
        + list(image_dir.glob("*.png"))
    )
    label_files = sorted(label_dir.glob("*.txt"))

    image_stems = {p.stem for p in image_files}
    label_stems = {p.stem for p in label_files}

    missing_labels = image_stems - label_stems
    extra_labels = label_stems - image_stems

    invalid_lines = []
    class_count = {class_id: 0 for class_id in CLASS_NAMES.keys()}

    for label_file in label_files:
        lines = label_file.read_text(encoding="utf-8").splitlines()

        for line_no, line in enumerate(lines, start=1):
            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) != 5:
                invalid_lines.append(
                    f"{label_file} line {line_no}: 字段数量不是 5"
                )
                continue

            try:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
            except ValueError:
                invalid_lines.append(
                    f"{label_file} line {line_no}: 存在无法解析的数字"
                )
                continue

            if class_id not in CLASS_NAMES:
                invalid_lines.append(
                    f"{label_file} line {line_no}: class_id={class_id} 不合法"
                )
                continue

            values = [x_center, y_center, width, height]
            if any(v < 0 or v > 1 for v in values):
                invalid_lines.append(
                    f"{label_file} line {line_no}: 坐标不在 0 到 1 范围内"
                )
                continue

            if width <= 0 or height <= 0:
                invalid_lines.append(
                    f"{label_file} line {line_no}: width 或 height 小于等于 0"
                )
                continue

            class_count[class_id] += 1

    return {
        "split": split,
        "images": len(image_files),
        "labels": len(label_files),
        "missing_labels": len(missing_labels),
        "extra_labels": len(extra_labels),
        "invalid_lines": invalid_lines,
        "class_count": class_count,
    }


def main():
    print("=" * 60)
    print("PCB Defect YOLO Dataset Check")
    print("=" * 60)

    total_images = 0
    total_labels = 0
    total_invalid = 0
    total_class_count = {class_id: 0 for class_id in CLASS_NAMES.keys()}

    for split in ["train", "val", "test"]:
        result = check_split(split)

        total_images += result["images"]
        total_labels += result["labels"]
        total_invalid += len(result["invalid_lines"])

        for class_id, count in result["class_count"].items():
            total_class_count[class_id] += count

        print(f"\n[{split}]")
        print(f"images: {result['images']}")
        print(f"labels: {result['labels']}")
        print(f"missing labels: {result['missing_labels']}")
        print(f"extra labels: {result['extra_labels']}")
        print(f"invalid lines: {len(result['invalid_lines'])}")

        if result["invalid_lines"]:
            print("前 10 个错误：")
            for error in result["invalid_lines"][:10]:
                print("  -", error)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"total images: {total_images}")
    print(f"total labels: {total_labels}")
    print(f"total invalid lines: {total_invalid}")

    print("\nClass distribution:")
    for class_id, class_name in CLASS_NAMES.items():
        print(f"{class_id} {class_name}: {total_class_count[class_id]}")

    if total_invalid == 0:
        print("\n检查结果：数据集格式正常，可以用于 YOLOv11 训练。")
    else:
        print("\n检查结果：数据集存在问题，请先修复标注。")


if __name__ == "__main__":
    main()
