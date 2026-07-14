import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal
from app.services.detection_service import detection_service


router = APIRouter(prefix="/api/detection", tags=["目标检测"])

BACKEND_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BACKEND_ROOT / "runs" / "detection" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_upload_file(file: UploadFile) -> Path:
    suffix = Path(file.filename or "").suffix

    if not suffix:
        suffix = ".jpg"

    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = UPLOAD_DIR / filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return save_path


@router.post("/single")
def detect_single_image(
    file: UploadFile = File(...),
    conf: float = Form(0.25),
    iou: float = Form(0.45),
    device: str = Form("0"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        image_path = save_upload_file(file)

        result = detection_service.detect_single(
            image_path=image_path,
            conf=conf,
            iou=iou,
            device=device,
        )

        return {
            "code": 200,
            "message": "单图检测成功",
            "data": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"单图检测失败：{exc}")


@router.post("/batch")
def detect_batch_images(
    files: List[UploadFile] = File(...),
    conf: float = Form(0.25),
    iou: float = Form(0.45),
    device: str = Form("0"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        image_paths = [
            save_upload_file(file)
            for file in files
        ]

        result = detection_service.detect_batch(
            image_paths=image_paths,
            conf=conf,
            iou=iou,
            device=device,
        )

        return {
            "code": 200,
            "message": "批量检测成功",
            "data": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"批量检测失败：{exc}")


@router.post("/zip")
def detect_zip_images(
    file: UploadFile = File(...),
    conf: float = Form(0.25),
    iou: float = Form(0.45),
    device: str = Form("0"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        zip_path = save_upload_file(file)

        result = detection_service.detect_zip(
            zip_path=zip_path,
            conf=conf,
            iou=iou,
            device=device,
        )

        return {
            "code": 200,
            "message": "ZIP 检测成功",
            "data": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ZIP 检测失败：{exc}")


@router.post("/video")
def detect_video_file(
    file: UploadFile = File(...),
    conf: float = Form(0.25),
    iou: float = Form(0.45),
    frame_sample_rate: int = Form(5),
    max_frames: int = Form(50),
    device: str = Form("0"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    视频检测接口。

    当前版本是同步返回结果：
    上传视频 -> 后端采样关键帧 -> YOLO 检测 -> 返回关键帧检测结果。
    """

    try:
        video_path = save_upload_file(file)

        result = detection_service.detect_video(
            video_path=video_path,
            conf=conf,
            iou=iou,
            frame_sample_rate=frame_sample_rate,
            max_frames=max_frames,
            device=device,
        )

        return {
            "code": 200,
            "message": "视频检测成功",
            "data": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"视频检测失败：{exc}")