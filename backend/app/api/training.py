"""
训练相关 API 路由

Day6 接口：
1. POST /api/training/start          启动训练任务
2. GET  /api/training/tasks          获取训练任务列表
3. GET  /api/training/status/{id}    获取任务状态和最新指标
4. GET  /api/training/metrics/{id}   获取训练指标历史
5. POST /api/training/stop/{id}      标记停止训练任务
6. GET  /api/training/results/{id}   下载 results.csv

Day7 新增接口：
7. POST /api/training/validate/{id}  模型评估
8. POST /api/training/export/{id}    模型导出
9. GET  /api/training/download/{id}  下载 best.pt
10. POST /api/training/predict       上传测试图验证模型效果
"""

import shutil
import uuid
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from ultralytics import YOLO

from app.api.deps import require_developer
from app.training.training_service import BACKEND_ROOT, training_service


router = APIRouter(
    prefix="/api/training",
    tags=["模型训练"],
    dependencies=[Depends(require_developer)],
)


class TrainingStartRequest(BaseModel):
    data_yaml: str | None = Field(
        default=None,
        description="data.yaml 路径；为空时使用 settings.DATASET_BASE_DIR/data.yaml",
    )
    model_name: str | None = Field(
        default="yolo11n.pt",
        description="模型名称或模型路径，例如 yolo11n.pt",
    )
    epochs: int = Field(
        default=5,
        ge=1,
        le=300,
        description="训练轮数",
    )
    imgsz: int = Field(
        default=640,
        ge=320,
        le=1280,
        description="输入图像尺寸",
    )
    batch: int = Field(
        default=8,
        ge=1,
        le=64,
        description="batch size",
    )
    device: str = Field(
        default="0",
        description="训练设备，GPU 用 0，CPU 用 cpu",
    )


class ModelValidateRequest(BaseModel):
    split: str = Field(
        default="val",
        description="评估数据集划分：train / val / test",
    )
    conf: float = Field(
        default=0.001,
        ge=0,
        le=1,
        description="置信度阈值",
    )
    iou: float = Field(
        default=0.6,
        ge=0,
        le=1,
        description="NMS IoU 阈值",
    )
    imgsz: int = Field(
        default=640,
        ge=320,
        le=1280,
        description="图像尺寸",
    )
    device: str = Field(
        default="0",
        description="评估设备，GPU 用 0，CPU 用 cpu",
    )


class ModelExportRequest(BaseModel):
    version: str = Field(
        default="v1.0.0",
        description="模型版本号，例如 v1.0.0",
    )
    description: str | None = Field(
        default=None,
        description="版本说明",
    )


def _get_task_output_dir(task_id: str) -> Path:
    """
    获取训练任务输出目录。

    优先使用内存中的 task 信息；
    如果后端重启导致内存任务丢失，则回退到 runs/train/{task_id}。
    """

    task = training_service.get_task(task_id)

    if task and task.get("output_dir"):
        return Path(task["output_dir"])

    return BACKEND_ROOT / "runs" / "train" / task_id


@router.post("/start", summary="启动训练任务")
def start_training(request: TrainingStartRequest):
    try:
        task = training_service.start_training(
            data_yaml=request.data_yaml,
            model_name=request.model_name,
            epochs=request.epochs,
            imgsz=request.imgsz,
            batch=request.batch,
            device=request.device,
        )

        return {
            "code": 200,
            "message": "训练任务已启动",
            "data": task,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"启动训练失败：{exc}",
        )


@router.get("/tasks", summary="获取训练任务列表")
def list_training_tasks():
    return {
        "code": 200,
        "message": "ok",
        "data": training_service.list_tasks(),
    }


@router.get("/status/{task_id}", summary="获取训练任务状态")
def get_training_status(task_id: str):
    task = training_service.get_task(task_id)

    if task:
        metrics = task.get("metrics", [])
        latest_metric = metrics[-1] if metrics else None

        return {
            "code": 200,
            "message": "ok",
            "data": {
                "task": task,
                "latest_metric": latest_metric,
            },
        }

    output_dir = _get_task_output_dir(task_id)

    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="训练任务不存在",
        )

    metrics = training_service.get_metrics(task_id)
    weights = training_service.get_weights(task_id)

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "task": {
                "task_id": task_id,
                "status": "success" if (output_dir / "weights" / "best.pt").exists() else "unknown",
                "message": "该任务来自本地文件目录，后端重启后内存状态已丢失",
                "output_dir": str(output_dir),
                "metrics": metrics,
                "weights": weights,
            },
            "latest_metric": metrics[-1] if metrics else None,
        },
    }


@router.get("/metrics/{task_id}", summary="获取训练指标历史")
def get_training_metrics(task_id: str):
    output_dir = _get_task_output_dir(task_id)

    if not output_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="训练任务不存在",
        )

    return {
        "code": 200,
        "message": "ok",
        "data": training_service.get_metrics(task_id),
    }


@router.post("/stop/{task_id}", summary="停止训练任务")
def stop_training(task_id: str):
    task = training_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail="训练任务不存在或后端重启后任务状态已丢失",
        )

    if task["status"] in ["success", "failed", "stopped"]:
        return {
            "code": 200,
            "message": f"任务已经结束，当前状态：{task['status']}",
            "data": task,
        }

    training_service._update_task(
        task_id,
        status="stopped",
        message="训练任务已标记为停止",
    )

    return {
        "code": 200,
        "message": "训练任务已标记为停止",
        "data": training_service.get_task(task_id),
    }


@router.get("/results/{task_id}", summary="下载训练 results.csv")
def download_results_csv(task_id: str):
    output_dir = _get_task_output_dir(task_id)
    results_csv = output_dir / "results.csv"

    if not results_csv.exists():
        raise HTTPException(
            status_code=404,
            detail="results.csv 尚未生成",
        )

    return FileResponse(
        path=str(results_csv),
        filename=f"{task_id}_results.csv",
        media_type="text/csv",
    )


@router.post("/validate/{task_id}", summary="模型评估")
def validate_model(task_id: str, request: ModelValidateRequest):
    """
    对训练好的 best.pt 执行验证集或测试集评估。

    会生成：
    - eval_report.json
    - confusion_matrix.png
    - confusion_matrix_normalized.png
    - BoxPR_curve.png
    - BoxF1_curve.png
    - predictions.json
    """

    result = training_service.validate_model(
        task_id=task_id,
        split=request.split,
        conf=request.conf,
        iou=request.iou,
        imgsz=request.imgsz,
        device=request.device,
    )

    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"],
        )

    return {
        "code": 200,
        "message": "模型评估完成",
        "data": result,
    }


@router.post("/export/{task_id}", summary="模型导出")
def export_model(task_id: str, request: ModelExportRequest):
    """
    将训练好的 best.pt 导出为正式模型版本。
    """

    result = training_service.export_model(
        task_id=task_id,
        version=request.version,
        description=request.description,
    )

    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"],
        )

    return {
        "code": 200,
        "message": "模型导出完成",
        "data": result,
    }


@router.get("/download/{task_id}", summary="下载模型权重 best.pt")
def download_model(task_id: str):
    """
    下载某个训练任务对应的 best.pt。
    """

    model_path = training_service.get_model_path(task_id, weight_type="best")

    if not model_path:
        candidate = BACKEND_ROOT / "runs" / "train" / task_id / "weights" / "best.pt"

        if candidate.exists():
            model_path = candidate

    if not model_path or not Path(model_path).exists():
        raise HTTPException(
            status_code=404,
            detail="模型权重不存在",
        )

    return FileResponse(
        path=str(model_path),
        filename=f"{task_id}_best.pt",
        media_type="application/octet-stream",
    )


@router.post("/predict", summary="上传测试图验证模型效果")
async def predict_image(
    file: UploadFile = File(...),
    task_id: str | None = Form(default=None),
    conf: float = Form(default=0.25),
    device: str = Form(default="0"),
):
    """
    上传一张测试图片，用训练好的模型进行推理验证。

    模型查找优先级：
    1. 如果传入 task_id，优先使用 runs/train/{task_id}/weights/best.pt
    2. 如果没有传 task_id，优先使用 models/pcb_aoi_v1.0.0/best.pt
    3. 如果默认导出模型不存在，则自动搜索 models 目录下最新的 best.pt
    4. 如果 models 中也没有，则自动搜索 runs/train 下最新的 best.pt
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="文件名不能为空",
        )

    allowed_suffix = {".jpg", ".jpeg", ".png", ".bmp"}
    suffix = Path(file.filename).suffix.lower()

    if suffix not in allowed_suffix:
        raise HTTPException(
            status_code=400,
            detail="只支持 jpg/jpeg/png/bmp 图片",
        )

    model_path = None

    if task_id:
        task_id = task_id.strip()

    # 1. 优先使用 task_id 对应的训练模型
    if task_id:
        model_path = training_service.get_model_path(task_id, weight_type="best")

        if not model_path:
            candidate = BACKEND_ROOT / "runs" / "train" / task_id / "weights" / "best.pt"

            if candidate.exists():
                model_path = candidate

    # 2. 如果没有 task_id，使用默认导出模型
    if not model_path:
        default_model = BACKEND_ROOT / "models" / "pcb_aoi_v1.0.0" / "best.pt"

        if default_model.exists():
            model_path = default_model

    # 3. 如果默认导出模型不存在，搜索 models 目录
    if not model_path:
        models_dir = BACKEND_ROOT / "models"

        if models_dir.exists():
            model_candidates = list(models_dir.glob("**/best.pt"))

            if model_candidates:
                model_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                model_path = model_candidates[0]

    # 4. 如果 models 目录也没有，搜索 runs/train 目录
    if not model_path:
        train_dir = BACKEND_ROOT / "runs" / "train"

        if train_dir.exists():
            train_candidates = list(train_dir.glob("**/weights/best.pt"))

            if train_candidates:
                train_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                model_path = train_candidates[0]

    if not model_path or not Path(model_path).exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "模型文件不存在。请确认以下路径至少存在一个："
                "models/pcb_aoi_v1.0.0/best.pt 或 runs/train/{task_id}/weights/best.pt"
            ),
        )

    upload_dir = BACKEND_ROOT / "runs" / "predict" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{suffix}"
    image_path = upload_dir / unique_name

    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image = cv2.imread(str(image_path))

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="图片读取失败",
        )

    model = YOLO(str(model_path))

    predict_name = f"predict_{uuid.uuid4().hex[:8]}"

    results = model.predict(
        source=str(image_path),
        conf=conf,
        device=device,
        save=True,
        project=str(BACKEND_ROOT / "runs" / "predict"),
        name=predict_name,
        exist_ok=True,
    )

    detections = []

    if results:
        result = results[0]
        boxes = result.boxes

        if boxes is not None:
            for box in boxes:
                class_id = int(box.cls[0])
                class_name = model.names.get(class_id, f"class_{class_id}")
                confidence = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()

                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": round(confidence, 4),
                        "bbox": {
                            "x1": round(float(xyxy[0]), 2),
                            "y1": round(float(xyxy[1]), 2),
                            "x2": round(float(xyxy[2]), 2),
                            "y2": round(float(xyxy[3]), 2),
                        },
                    }
                )

    result_dir = BACKEND_ROOT / "runs" / "predict" / predict_name

    return {
        "code": 200,
        "message": "测试图验证完成",
        "data": {
            "task_id": task_id,
            "model_path": str(model_path),
            "input_image": str(image_path),
            "result_dir": str(result_dir),
            "detections": detections,
            "count": len(detections),
        },
    }