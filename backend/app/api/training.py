"""
训练相关 API 路由

接口列表：
1. POST /api/training/start          启动训练任务
2. GET  /api/training/tasks          获取训练任务列表
3. GET  /api/training/status/{id}    获取任务状态和最新指标
4. GET  /api/training/metrics/{id}   获取训练指标历史
5. POST /api/training/stop/{id}      标记停止训练任务
6. GET  /api/training/results/{id}   下载 results.csv
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.training.training_service import training_service


router = APIRouter(prefix="/api/training", tags=["模型训练"])


class TrainingStartRequest(BaseModel):
    data_yaml: str | None = Field(
        default=None,
        description="data.yaml 路径；为空时使用 settings.DATASET_BASE_DIR/data.yaml",
    )
    model_name: str | None = Field(
        default=None,
        description="模型名称或模型路径，例如 yolo11n.pt",
    )
    epochs: int = Field(default=5, ge=1, le=300, description="训练轮数")
    imgsz: int = Field(default=640, ge=320, le=1280, description="输入图像尺寸")
    batch: int = Field(default=8, ge=1, le=64, description="batch size")
    device: str = Field(default="0", description="训练设备，GPU 用 0，CPU 用 cpu")


class ApiResponse(BaseModel):
    code: int = 200
    message: str = "ok"
    data: Any = None


@router.post("/start", summary="启动训练任务")
def start_training(request: TrainingStartRequest):
    """
    创建并启动一个 YOLOv11 训练任务。
    """

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
        raise HTTPException(status_code=500, detail=f"启动训练失败：{exc}")


@router.get("/tasks", summary="获取训练任务列表")
def list_training_tasks():
    """
    获取当前进程内保存的训练任务列表。
    """

    return {
        "code": 200,
        "message": "ok",
        "data": training_service.list_tasks(),
    }


@router.get("/status/{task_id}", summary="获取训练任务状态")
def get_training_status(task_id: str):
    """
    获取单个训练任务状态，并返回最新一轮训练指标。
    """

    task = training_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")

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


@router.get("/metrics/{task_id}", summary="获取训练指标历史")
def get_training_metrics(task_id: str):
    """
    获取 results.csv 中的所有 epoch 指标。
    """

    task = training_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    metrics = training_service.get_metrics(task_id)

    return {
        "code": 200,
        "message": "ok",
        "data": metrics,
    }


@router.post("/stop/{task_id}", summary="停止训练任务")
def stop_training(task_id: str):
    """
    标记训练任务为 stopped。

    说明：
    当前 TrainingService 使用线程方式启动 Ultralytics 训练，
    暂不强制杀死底层训练进程。
    该接口主要用于前端状态控制和后续扩展。
    """

    task = training_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")

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
    """
    下载某个训练任务的 results.csv 文件。
    """

    task = training_service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    output_dir = Path(task["output_dir"])
    results_csv = output_dir / "results.csv"

    if not results_csv.exists():
        raise HTTPException(status_code=404, detail="results.csv 尚未生成")

    return FileResponse(
        path=str(results_csv),
        filename=f"{task_id}_results.csv",
        media_type="text/csv",
    )