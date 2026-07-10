"""
YOLOv11 训练服务封装

功能：
1. 启动 PCB AOI 缺陷检测模型训练
2. 管理训练任务状态
3. 解析 Ultralytics 生成的 results.csv
4. 查询训练进度、指标和模型权重路径
"""

import csv
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