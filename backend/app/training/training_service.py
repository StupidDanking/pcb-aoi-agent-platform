"""
YOLOv11 训练服务封装

功能：
1. 启动 PCB AOI 缺陷检测模型训练
2. 管理训练任务状态
3. 解析 Ultralytics 生成的 results.csv
4. 查询训练进度、指标和模型权重路径
"""

import csv
import json
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ultralytics import YOLO

from app.config.settings import settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class TrainingService:
    def __init__(self):
        self.tasks: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def start_training(
        self,
        data_yaml: str | None = None,
        model_name: str | None = None,
        epochs: int = 5,
        imgsz: int = 640,
        batch: int = 8,
        device: str | int | None = None,
    ) -> dict[str, Any]:
        """
        启动一次 YOLOv11 训练任务。
        """

        task_id = f"task_{uuid.uuid4().hex[:8]}"

        data_yaml_path = self._resolve_data_yaml(data_yaml)
        model_path = model_name or settings.DEFAULT_YOLO_MODEL
        train_device = device if device is not None else settings.DEFAULT_TRAIN_DEVICE

        output_root = BACKEND_ROOT / settings.TRAIN_OUTPUT_DIR
        output_root.mkdir(parents=True, exist_ok=True)

        task_name = task_id

        task_info = {
            "task_id": task_id,
            "status": "pending",
            "message": "训练任务已创建",
            "data_yaml": str(data_yaml_path),
            "model_name": model_path,
            "epochs": epochs,
            "imgsz": imgsz,
            "batch": batch,
            "device": str(train_device),
            "output_dir": str(output_root / task_name),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "started_at": None,
            "finished_at": None,
            "error_message": None,
        }

        with self.lock:
            self.tasks[task_id] = task_info

        thread = threading.Thread(
            target=self._run_training,
            args=(
                task_id,
                model_path,
                str(data_yaml_path),
                epochs,
                imgsz,
                batch,
                train_device,
                output_root,
                task_name,
            ),
            daemon=True,
        )
        thread.start()

        return task_info

    def _run_training(
        self,
        task_id: str,
        model_path: str,
        data_yaml_path: str,
        epochs: int,
        imgsz: int,
        batch: int,
        device: str | int,
        output_root: Path,
        task_name: str,
    ) -> None:
        """
        后台线程中实际执行训练。
        """

        try:
            self._update_task(
                task_id,
                status="running",
                message="训练中",
                started_at=datetime.now().isoformat(timespec="seconds"),
            )

            model = YOLO(model_path)

            result = model.train(
                data=data_yaml_path,
                epochs=epochs,
                imgsz=imgsz,
                batch=batch,
                device=device,
                project=str(output_root),
                name=task_name,
                exist_ok=True,
                plots=True,
            )

            save_dir = Path(result.save_dir)

            self._update_task(
                task_id,
                status="success",
                message="训练完成",
                output_dir=str(save_dir),
                finished_at=datetime.now().isoformat(timespec="seconds"),
            )

        except Exception as exc:
            self._update_task(
                task_id,
                status="failed",
                message="训练失败",
                error_message=str(exc),
                finished_at=datetime.now().isoformat(timespec="seconds"),
            )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """
        获取单个训练任务信息。
        """

        with self.lock:
            task = self.tasks.get(task_id)

        if not task:
            return None

        task_copy = dict(task)
        task_copy["metrics"] = self.get_metrics(task_id)
        task_copy["weights"] = self.get_weights(task_id)

        return task_copy

    def list_tasks(self) -> list[dict[str, Any]]:
        """
        获取所有训练任务。
        """

        with self.lock:
            tasks = list(self.tasks.values())

        return sorted(tasks, key=lambda x: x["created_at"], reverse=True)

    def get_metrics(self, task_id: str) -> list[dict[str, Any]]:
        """
        读取 results.csv，返回训练指标列表。
        """

        task = self.tasks.get(task_id)

        if not task:
            return []

        output_dir = Path(task["output_dir"])
        results_csv = output_dir / "results.csv"

        if not results_csv.exists():
            return []

        metrics = []

        with open(results_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                clean_row = {}

                for key, value in row.items():
                    if key is None:
                        continue

                    clean_key = key.strip()

                    try:
                        clean_row[clean_key] = float(value)
                    except (TypeError, ValueError):
                        clean_row[clean_key] = value

                metrics.append(clean_row)

        return metrics

    def get_weights(self, task_id: str) -> dict[str, str | None]:
        """
        返回 best.pt 和 last.pt 路径。
        """

        task = self.tasks.get(task_id)

        if not task:
            return {
                "best": None,
                "last": None,
            }

        output_dir = Path(task["output_dir"])
        weights_dir = output_dir / "weights"

        best_path = weights_dir / "best.pt"
        last_path = weights_dir / "last.pt"

        return {
            "best": str(best_path) if best_path.exists() else None,
            "last": str(last_path) if last_path.exists() else None,
        }


    def get_model_path(self, task_id: str, weight_type: str = "best") -> Path | None:
        """
        获取某个训练任务的模型权重路径。

        weight_type:
        - best: 最优模型 best.pt
        - last: 最后一轮模型 last.pt
        """

        task = self.tasks.get(task_id)

        if task:
            output_dir = Path(task["output_dir"])
        else:
            output_dir = BACKEND_ROOT / settings.TRAIN_OUTPUT_DIR / task_id

        weights_dir = output_dir / "weights"

        if weight_type == "last":
            model_path = weights_dir / "last.pt"
        else:
            model_path = weights_dir / "best.pt"

        if model_path.exists():
            return model_path

        return None

    def validate_model(
        self,
        task_id: str,
        split: str = "val",
        conf: float = 0.001,
        iou: float = 0.6,
        imgsz: int = 640,
        device: str = "0",
    ) -> dict[str, Any]:
        """
        对训练完成的模型进行评估。

        功能：
        1. 加载 task_xxxxxxxx/weights/best.pt
        2. 在 val 或 test 集上执行 model.val()
        3. 生成混淆矩阵、PR 曲线、F1 曲线
        4. 保存 eval_report.json
        """

        model_path = self.get_model_path(task_id, weight_type="best")

        if not model_path:
            return {
                "error": f"未找到模型权重：{task_id}/weights/best.pt"
            }

        data_yaml_path = self._resolve_data_yaml(None)

        output_dir = model_path.parents[1]
        eval_dir = output_dir / "eval"
        eval_dir.mkdir(parents=True, exist_ok=True)

        try:
            model = YOLO(str(model_path))

            results = model.val(
                data=str(data_yaml_path),
                split=split,
                imgsz=imgsz,
                device=device,
                conf=conf,
                iou=iou,
                plots=True,
                save_json=True,
                project=str(eval_dir),
                name=split,
                exist_ok=True,
                verbose=True,
            )

            overall = {
                "precision": float(results.box.mp),
                "recall": float(results.box.mr),
                "map50": float(results.box.map50),
                "map50_95": float(results.box.map),
            }

            per_class = {}

            class_names = {
                int(class_id): class_name
                for class_id, class_name in model.names.items()
            }

            try:
                for class_id, class_name in class_names.items():
                    ap50 = (
                        float(results.box.ap50[class_id])
                        if class_id < len(results.box.ap50)
                        else 0.0
                    )
                    ap50_95 = (
                        float(results.box.ap[class_id])
                        if class_id < len(results.box.ap)
                        else 0.0
                    )

                    per_class[class_name] = {
                        "class_id": class_id,
                        "ap50": round(ap50, 4),
                        "ap50_95": round(ap50_95, 4),
                    }
            except Exception as exc:
                per_class["parse_error"] = str(exc)

            report = {
                "task_id": task_id,
                "weights": str(model_path),
                "data_yaml": str(data_yaml_path),
                "split": split,
                "overall": overall,
                "per_class": per_class,
                "generated_files": {
                    "eval_dir": str(eval_dir / split),
                    "eval_report": str(eval_dir / "eval_report.json"),
                    "confusion_matrix": str(eval_dir / split / "confusion_matrix.png"),
                    "confusion_matrix_normalized": str(eval_dir / split / "confusion_matrix_normalized.png"),
                    "box_pr_curve": str(eval_dir / split / "BoxPR_curve.png"),
                    "box_f1_curve": str(eval_dir / split / "BoxF1_curve.png"),
                    "box_p_curve": str(eval_dir / split / "BoxP_curve.png"),
                    "box_r_curve": str(eval_dir / split / "BoxR_curve.png"),
                    "predictions_json": str(eval_dir / split / "predictions.json"),
                },
                "evaluated_at": datetime.now().isoformat(timespec="seconds"),
            }

            report_path = eval_dir / "eval_report.json"

            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            if task_id in self.tasks:
                self._update_task(
                    task_id,
                    eval_report=str(report_path),
                    eval_overall=overall,
                )

            return report

        except Exception as exc:
            return {
                "error": f"模型评估失败：{exc}"
            }

    def export_model(
        self,
        task_id: str,
        version: str = "v1.0.0",
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        导出训练完成的模型为正式版本。

        导出内容：
        1. best.pt
        2. eval_report.json
        3. confusion_matrix.png
        4. confusion_matrix_normalized.png
        5. BoxPR_curve.png
        6. BoxF1_curve.png
        """

        model_path = self.get_model_path(task_id, weight_type="best")

        if not model_path:
            return {
                "error": f"未找到模型权重：{task_id}/weights/best.pt"
            }

        output_dir = model_path.parents[1]
        eval_dir = output_dir / "eval"

        export_dir = BACKEND_ROOT / "models" / f"pcb_aoi_{version}"
        export_dir.mkdir(parents=True, exist_ok=True)

        exported_model_path = export_dir / "best.pt"
        shutil.copy2(model_path, exported_model_path)

        eval_report_path = eval_dir / "eval_report.json"
        if eval_report_path.exists():
            shutil.copy2(eval_report_path, export_dir / "eval_report.json")

        plot_names = [
            "confusion_matrix.png",
            "confusion_matrix_normalized.png",
            "BoxPR_curve.png",
            "BoxF1_curve.png",
            "BoxP_curve.png",
            "BoxR_curve.png",
        ]

        # 默认使用 val 评估目录
        eval_val_dir = eval_dir / "val"

        for plot_name in plot_names:
            src = eval_val_dir / plot_name
            if src.exists():
                shutil.copy2(src, export_dir / plot_name)

        meta = {
            "task_id": task_id,
            "version": version,
            "description": description or "PCB AOI YOLOv11 模型导出版本",
            "model_path": str(exported_model_path),
            "export_dir": str(export_dir),
            "source_model": str(model_path),
            "exported_at": datetime.now().isoformat(timespec="seconds"),
        }

        with open(export_dir / "model_meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return {
            "task_id": task_id,
            "version": version,
            "model_path": str(exported_model_path),
            "export_dir": str(export_dir),
            "file_size": exported_model_path.stat().st_size,
            "message": f"模型已导出为版本 {version}",
        }

    def _resolve_data_yaml(self, data_yaml: str | None) -> Path:
        """
        解析 data.yaml 路径。
        """

        if data_yaml:
            path = Path(data_yaml)
        else:
            dataset_base = Path(settings.DATASET_BASE_DIR)

            if not dataset_base.is_absolute():
                dataset_base = BACKEND_ROOT / dataset_base

            path = dataset_base / "data.yaml"

        path = path.resolve()

        if not path.exists():
            raise FileNotFoundError(f"data.yaml 不存在：{path}")

        return path

    def _update_task(self, task_id: str, **kwargs) -> None:
        """
        更新任务状态。
        """

        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(kwargs)


training_service = TrainingService()