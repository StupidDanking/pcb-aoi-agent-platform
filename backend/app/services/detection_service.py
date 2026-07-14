import base64
import json
import uuid
import zipfile
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO

from app.config.settings import settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

UPLOAD_DIR = BACKEND_ROOT / "runs" / "detection" / "uploads"
OUTPUT_DIR = BACKEND_ROOT / "runs" / "detection" / "outputs"
ZIP_EXTRACT_DIR = BACKEND_ROOT / "runs" / "detection" / "zip_extract"
VIDEO_FRAME_DIR = BACKEND_ROOT / "runs" / "detection" / "video_frames"

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}


class DetectionService:
    def __init__(self):
        self._model_cache: dict[str, YOLO] = {}

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ZIP_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
        VIDEO_FRAME_DIR.mkdir(parents=True, exist_ok=True)

    def _find_model_path(self) -> str:
        """
        优先读取 backend/models/active_model.json 中指定的当前模型。
        如果没有设置 active_model，则回退到 v1.0.0，再回退到 models 下最新 best.pt。
        """
        active_model_file = BACKEND_ROOT / "models" / "active_model.json"

        if active_model_file.exists():
            try:
                active_data = json.loads(active_model_file.read_text(encoding="utf-8"))
                active_model_name = active_data.get("model_name")

                if active_model_name:
                    active_best = BACKEND_ROOT / "models" / active_model_name / "best.pt"

                    if active_best.exists():
                        return str(active_best)
            except Exception:
                pass

        candidates = [
            BACKEND_ROOT / "models" / "pcb_aoi_v1.0.0" / "best.pt",
        ]

        models_dir = BACKEND_ROOT / "models"
        if models_dir.exists():
            candidates.extend(
                sorted(
                    models_dir.glob("**/best.pt"),
                    key=lambda p: p.stat().st_mtime if p.exists() else 0,
                    reverse=True,
                )
            )

        train_dir = BACKEND_ROOT / settings.TRAIN_OUTPUT_DIR
        if train_dir.exists():
            candidates.extend(
                sorted(
                    train_dir.glob("**/weights/best.pt"),
                    key=lambda p: p.stat().st_mtime if p.exists() else 0,
                    reverse=True,
                )
            )

        for path in candidates:
            if path.exists():
                return str(path)

        return "yolo11n.pt"

    def _get_model(self) -> YOLO:
        model_path = self._find_model_path()

        if model_path not in self._model_cache:
            self._model_cache[model_path] = YOLO(model_path)

        return self._model_cache[model_path]

    def _image_to_base64(self, image_path: Path) -> str:
        with open(image_path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode("utf-8")

        return f"data:image/jpeg;base64,{encoded}"

    def _build_class_stats(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        stats: dict[str, int] = {}

        for item in detections:
            class_name = item.get("class_name", "unknown")
            stats[class_name] = stats.get(class_name, 0) + 1

        return [
            {
                "class_name": class_name,
                "count": count,
            }
            for class_name, count in stats.items()
        ]

    def _merge_class_stats(self, stats_list: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        counter: dict[str, int] = {}

        for stats in stats_list:
            for item in stats:
                class_name = item.get("class_name", "unknown")
                count = int(item.get("count", 0))
                counter[class_name] = counter.get(class_name, 0) + count

        return [
            {
                "class_name": class_name,
                "count": count,
            }
            for class_name, count in counter.items()
        ]

    def detect_single(
        self,
        image_path: str | Path,
        conf: float = 0.25,
        iou: float = 0.45,
        device: str = "0",
    ) -> dict[str, Any]:
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"图片不存在：{image_path}")

        if image_path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            raise ValueError(f"不支持的图片格式：{image_path.suffix}")

        model = self._get_model()

        run_id = uuid.uuid4().hex[:8]
        output_subdir = OUTPUT_DIR / f"single_{run_id}"
        output_subdir.mkdir(parents=True, exist_ok=True)

        results = model.predict(
            source=str(image_path),
            conf=conf,
            iou=iou,
            device=device,
            verbose=False,
        )

        result = results[0]
        names = result.names

        detections = []

        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            xyxy = box.xyxy[0].tolist()

            detections.append({
                "class_id": class_id,
                "class_name": names.get(class_id, str(class_id)),
                "confidence": confidence,
                "bbox": [round(float(v), 2) for v in xyxy],
            })

        annotated_image = result.plot()
        annotated_filename = f"{image_path.stem}_annotated.jpg"
        annotated_path = output_subdir / annotated_filename

        cv2.imwrite(str(annotated_path), annotated_image)

        return {
            "type": "single",
            "image_name": image_path.name,
            "image_path": str(image_path),
            "annotated_image_path": str(annotated_path),
            "annotated_image_base64": self._image_to_base64(annotated_path),
            "detections": detections,
            "class_stats": self._build_class_stats(detections),
            "total_objects": len(detections),
            "conf": conf,
            "iou": iou,
        }

    def detect_batch(
        self,
        image_paths: list[str | Path],
        conf: float = 0.25,
        iou: float = 0.45,
        device: str = "0",
    ) -> dict[str, Any]:
        results = []

        for image_path in image_paths:
            try:
                result = self.detect_single(
                    image_path=image_path,
                    conf=conf,
                    iou=iou,
                    device=device,
                )

                results.append({
                    "success": True,
                    **result,
                })
            except Exception as exc:
                results.append({
                    "success": False,
                    "image_path": str(image_path),
                    "image_name": Path(image_path).name,
                    "error": str(exc),
                })

        total_images = len(results)
        success_images = len([item for item in results if item.get("success")])
        total_objects = sum(item.get("total_objects", 0) for item in results)

        class_stats = self._merge_class_stats([
            item.get("class_stats", [])
            for item in results
        ])

        return {
            "type": "batch",
            "total_images": total_images,
            "success_images": success_images,
            "failed_images": total_images - success_images,
            "total_objects": total_objects,
            "class_stats": class_stats,
            "results": results,
            "conf": conf,
            "iou": iou,
        }

    def detect_zip(
        self,
        zip_path: str | Path,
        conf: float = 0.25,
        iou: float = 0.45,
        device: str = "0",
    ) -> dict[str, Any]:
        zip_path = Path(zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP 文件不存在：{zip_path}")

        if zip_path.suffix.lower() != ".zip":
            raise ValueError("请上传 ZIP 文件")

        run_id = uuid.uuid4().hex[:8]
        extract_dir = ZIP_EXTRACT_DIR / f"zip_{run_id}"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_file:
            zip_file.extractall(extract_dir)

        image_paths = [
            path
            for path in extract_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_SUFFIXES
        ]

        batch_result = self.detect_batch(
            image_paths=image_paths,
            conf=conf,
            iou=iou,
            device=device,
        )

        return {
            "type": "zip",
            "zip_name": zip_path.name,
            "extract_dir": str(extract_dir),
            **batch_result,
        }

    def detect_video(
        self,
        video_path: str | Path,
        conf: float = 0.25,
        iou: float = 0.45,
        frame_sample_rate: int = 5,
        max_frames: int = 50,
        device: str = "0",
    ) -> dict[str, Any]:
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在：{video_path}")

        if video_path.suffix.lower() not in ALLOWED_VIDEO_SUFFIXES:
            raise ValueError(f"不支持的视频格式：{video_path.suffix}")

        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件：{video_path}")

        model = self._get_model()

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        duration_seconds = round(total_frames / fps, 2) if fps > 0 else 0

        frame_sample_rate = max(1, int(frame_sample_rate))
        max_frames = max(1, int(max_frames))

        run_id = uuid.uuid4().hex[:8]
        output_subdir = VIDEO_FRAME_DIR / f"video_{run_id}"
        output_subdir.mkdir(parents=True, exist_ok=True)

        key_frames = []
        all_frame_stats = []
        processed_frames = 0
        frame_index = 0
        total_inference_time = 0.0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            should_process = frame_index % frame_sample_rate == 0

            if should_process:
                results = model.predict(
                    source=frame,
                    conf=conf,
                    iou=iou,
                    device=device,
                    verbose=False,
                )

                result = results[0]
                names = result.names
                detections = []

                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    confidence = float(box.conf[0].item())
                    xyxy = box.xyxy[0].tolist()

                    detections.append({
                        "class_id": class_id,
                        "class_name": names.get(class_id, str(class_id)),
                        "confidence": confidence,
                        "bbox": [round(float(v), 2) for v in xyxy],
                    })

                annotated_image = result.plot()
                inference_time = float(result.speed.get("inference", 0))
                total_inference_time += inference_time

                class_stats = self._build_class_stats(detections)
                all_frame_stats.append(class_stats)

                frame_filename = f"frame_{frame_index}_annotated.jpg"
                frame_path = output_subdir / frame_filename
                cv2.imwrite(str(frame_path), annotated_image)

                key_frames.append({
                    "frame_index": frame_index,
                    "timestamp": round(frame_index / fps, 2) if fps > 0 else 0,
                    "annotated_image_base64": self._image_to_base64(frame_path),
                    "detections": detections,
                    "class_stats": class_stats,
                    "object_count": len(detections),
                    "inference_time": round(inference_time, 2),
                })

                processed_frames += 1

                if processed_frames >= max_frames:
                    break

            frame_index += 1

        cap.release()

        class_stats = self._merge_class_stats(all_frame_stats)
        total_objects = sum(item.get("count", 0) for item in class_stats)

        return {
            "type": "video",
            "video_name": video_path.name,
            "video_path": str(video_path),
            "total_frames": total_frames,
            "processed_frames": processed_frames,
            "frame_sample_rate": frame_sample_rate,
            "max_frames": max_frames,
            "fps": round(fps, 2),
            "duration_seconds": duration_seconds,
            "video_resolution": {
                "width": width,
                "height": height,
            },
            "total_objects": total_objects,
            "class_stats": class_stats,
            "class_counts": {
                item["class_name"]: item["count"]
                for item in class_stats
            },
            "key_frames": key_frames,
            "total_inference_time": round(total_inference_time, 2),
            "conf": conf,
            "iou": iou,
        }


detection_service = DetectionService()