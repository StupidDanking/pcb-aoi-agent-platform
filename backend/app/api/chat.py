import json
import shutil
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.agent.detection_agent import detection_agent
from app.api.auth import get_current_user


router = APIRouter(prefix="/api/chat", tags=["智能对话"])

BACKEND_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BACKEND_ROOT / "runs" / "chat" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_upload_file(file: UploadFile) -> Path:
    suffix = Path(file.filename or "").suffix

    if not suffix:
        suffix = ".jpg"

    safe_filename = file.filename or f"upload{suffix}"
    filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    save_path = UPLOAD_DIR / filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return save_path


def format_sse_event(data: dict) -> str:
    """
    SSE 格式：
    data: {...}

    """

    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(
    message: str = Form(""),
    files: Optional[List[UploadFile]] = File(None),
    conf: float = Form(0.25),
    iou: float = Form(0.45),
    device: str = Form("0"),
    current_user=Depends(get_current_user),
):
    """
    Day8 SSE 流式对话接口。

    支持：
    1. 纯文本问答
    2. 单图检测
    3. 批量图片检测
    4. ZIP 检测

    前端使用 fetch + ReadableStream 读取。
    """

    saved_paths = []

    if files:
        for file in files:
            saved_path = save_upload_file(file)
            saved_paths.append(str(saved_path))

    async def event_generator():
        async for event in detection_agent.chat_stream(
            message=message,
            file_paths=saved_paths,
            conf=conf,
            iou=iou,
            device=device,
        ):
            yield format_sse_event(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )