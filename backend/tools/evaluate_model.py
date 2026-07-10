"""
PCB AOI YOLOv11 模型评估工具

功能：
1. 加载训练完成的 best.pt 或 last.pt
2. 在 val / test / train 数据集上执行 model.val()
3. 输出整体 Precision、Recall、mAP50、mAP50-95
4. 输出每个 PCB 缺陷类别的 AP 指标
5. 生成 eval_report.json
6. 生成 confusion_matrix.png、PR_curve.png、F1_curve.png 等评估图

使用方式：
cd D:/shixi/rsod-agent-platform/backend

python tools/evaluate_model.py ^
  --weights runs/train/task_xxxxxxxx/weights/best.pt ^
  --data ../datasets/pcb_defect/data.yaml ^
  --split val ^
  --device 0
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ultralytics import YOLO


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_DATA_YAML = PROJECT_ROOT / "datasets" / "pcb_defect" / "data.yaml"


def parse_results(results, class_names: dict[int, str]) -> dict[str, Any]:
    """
    解析 Ultralytics model.val() 返回结果。
    """

    overall = {
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
        "map50": float(results.box.map50),
        "map50_95": float(results.box.map),
    }

    per_class = {}

    try:
        ap50_list = results.box.ap50
        ap_list = results.box.ap

        for class_id, class_name in class_names.items():
            ap50 = float(ap50_list[class_id]) if class_id < len(ap50_list) else 0.0
            ap50_95 = float(ap_list[class_id]) if class_id < len(ap_list) else 0.0

            per_class[class_name] = {
                "class_id": class_id,
                "ap50": round(ap50, 4),
                "ap50_95": round(ap50_95, 4),
            }

    except Exception as exc:
        per_class["error"] = f"每类 AP 解析失败：{exc}"

    return {
        "overall": overall,
        "per_class": per_class,
    }


def print_report(report: dict[str, Any]) -> None:
    """
    在终端打印评估报告。
    """

    overall = report["overall"]
    per_class = report["per_class"]

    print("\n" + "=" * 70)
    print("PCB AOI YOLOv11 模型评估报告")
    print("=" * 70)

    print("\n[整体指标]")
    print(f"Precision : {overall['precision']:.4f}")
    print(f"Recall    : {overall['recall']:.4f}")
    print(f"mAP50     : {overall['map50']:.4f}")
    print(f"mAP50-95  : {overall['map50_95']:.4f}")

    print("\n[每类 AP]")
    print(f"{'类别':<20} {'AP50':>10} {'AP50-95':>10}")
    print("-" * 45)

    if isinstance(per_class, dict):
        for class_name, item in per_class.items():
            if not isinstance(item, dict):
                continue

            ap50 = item.get("ap50", 0)
            ap50_95 = item.get("ap50_95", 0)
            print(f"{class_name:<20} {ap50:>10.4f} {ap50_95:>10.4f}")

    weak_classes = []

    for class_name, item in per_class.items():
        if isinstance(item, dict) and item.get("ap50", 1) < 0.5:
            weak_classes.append(class_name)

    if weak_classes:
        print("\n[弱势类别]")
        print("AP50 < 0.5 的类别：", ", ".join(weak_classes))
        print("建议：检查这些类别的标注质量，或增加对应类别样本。")
    else:
        print("\n[弱势类别]")
        print("暂无 AP50 < 0.5 的类别。")

    print("\n" + "=" * 70 + "\n")


def run_evaluation(
    weights_path: Path,
    data_yaml: Path,
    split: str,
    device: str,
    imgsz: int,
    conf: float,
    iou: float,
    output_dir: Path | None,
) -> dict[str, Any]:
    """
    执行模型评估。
    """

    if not weights_path.exists():
        raise FileNotFoundError(f"权重文件不存在：{weights_path}")

    if not data_yaml.exists():
        raise FileNotFoundError(f"data.yaml 不存在：{data_yaml}")

    if output_dir is None:
        output_dir = weights_path.parents[1] / "eval"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n开始模型评估：")
    print(f"权重文件：{weights_path}")
    print(f"数据配置：{data_yaml}")
    print(f"评估数据：{split}")
    print(f"设备：{device}")
    print(f"输出目录：{output_dir}")

    model = YOLO(str(weights_path))

    results = model.val(
        data=str(data_yaml),
        split=split,
        imgsz=imgsz,
        device=device,
        conf=conf,
        iou=iou,
        plots=True,
        save_json=True,
        project=str(output_dir),
        name="val",
        exist_ok=True,
        verbose=True,
    )

    class_names = {
        int(class_id): class_name
        for class_id, class_name in model.names.items()
    }

    parsed = parse_results(results, class_names)

    report = {
        "model": {
            "weights": str(weights_path),
            "data_yaml": str(data_yaml),
            "split": split,
            "device": device,
            "imgsz": imgsz,
            "conf": conf,
            "iou": iou,
        },
        "overall": parsed["overall"],
        "per_class": parsed["per_class"],
        "generated_files": {
            "output_dir": str(output_dir / "val"),
            "eval_report": str(output_dir / "eval_report.json"),
            "confusion_matrix": str(output_dir / "val" / "confusion_matrix.png"),
            "normalized_confusion_matrix": str(output_dir / "val" / "confusion_matrix_normalized.png"),
            "pr_curve": str(output_dir / "val" / "PR_curve.png"),
            "f1_curve": str(output_dir / "val" / "F1_curve.png"),
        },
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
    }

    report_path = output_dir / "eval_report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print_report(report)
    print(f"评估报告已保存：{report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="PCB AOI YOLOv11 模型评估工具")

    parser.add_argument(
        "--weights",
        "-w",
        required=True,
        type=str,
        help="模型权重路径，例如 runs/train/task_xxxxxxxx/weights/best.pt",
    )

    parser.add_argument(
        "--data",
        "-d",
        default=str(DEFAULT_DATA_YAML),
        type=str,
        help="data.yaml 路径，默认 ../datasets/pcb_defect/data.yaml",
    )

    parser.add_argument(
        "--split",
        "-s",
        default="val",
        choices=["train", "val", "test"],
        help="评估数据划分：train / val / test",
    )

    parser.add_argument(
        "--device",
        default="0",
        type=str,
        help="评估设备，GPU 用 0，CPU 用 cpu",
    )

    parser.add_argument(
        "--imgsz",
        default=640,
        type=int,
        help="图像尺寸",
    )

    parser.add_argument(
        "--conf",
        default=0.001,
        type=float,
        help="置信度阈值",
    )

    parser.add_argument(
        "--iou",
        default=0.6,
        type=float,
        help="NMS IoU 阈值",
    )

    parser.add_argument(
        "--output",
        "-o",
        default=None,
        type=str,
        help="评估输出目录",
    )

    args = parser.parse_args()

    weights_path = Path(args.weights).resolve()
    data_yaml = Path(args.data).resolve()
    output_dir = Path(args.output).resolve() if args.output else None

    run_evaluation(
        weights_path=weights_path,
        data_yaml=data_yaml,
        split=args.split,
        device=args.device,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()