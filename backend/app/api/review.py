"""
缺陷复核 API

用途：
- 对检测结果中的每个缺陷框做人工判定
- 支持：确认缺陷 / 误报 / 不确定 + 备注
- 绑定 history_records.id（检测历史任务）
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.api.history import (
    ensure_history_records_table,
    get_user_id,
    row_to_dict,
)


router = APIRouter(prefix="/api/review", tags=["缺陷复核"])

VerdictType = Literal["confirmed", "false_positive", "unsure"]


class ReviewItemIn(BaseModel):
    detection_index: int = Field(..., ge=0)
    verdict: VerdictType
    comment: Optional[str] = ""
    class_name: Optional[str] = None
    confidence: Optional[float] = None
    bbox: Optional[list[float]] = None
    source_label: Optional[str] = None


class ReviewBatchSave(BaseModel):
    items: list[ReviewItemIn]


def ensure_defect_reviews_table(db: Session):
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS defect_reviews (
                id SERIAL PRIMARY KEY,
                history_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                detection_index INTEGER NOT NULL,
                verdict VARCHAR(32) NOT NULL,
                comment TEXT,
                class_name VARCHAR(100),
                confidence DOUBLE PRECISION,
                bbox TEXT,
                source_label VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (history_id, detection_index)
            )
            """
        )
    )
    db.commit()


def _parse_payload(raw: Any) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def flatten_detections(payload: dict) -> list[dict[str, Any]]:
    """
    Normalize single / batch / zip / video payloads into a flat review list.
    Each item has: detection_index, class_name, confidence, bbox, source_label, preview_base64?
    """
    items: list[dict[str, Any]] = []

    if not payload:
        return items

    result_type = payload.get("type")

    if result_type == "single" or (
        "detections" in payload and result_type not in {"batch", "zip", "video"}
    ):
        for idx, det in enumerate(payload.get("detections") or []):
            items.append(
                {
                    "detection_index": idx,
                    "class_id": det.get("class_id"),
                    "class_name": det.get("class_name"),
                    "confidence": det.get("confidence"),
                    "bbox": det.get("bbox"),
                    "source_label": payload.get("image_name") or "single",
                    "preview_base64": payload.get("annotated_image_base64"),
                }
            )
        return items

    if result_type in {"batch", "zip"} or payload.get("results"):
        offset = 0
        for result in payload.get("results") or []:
            if not result.get("success", True):
                continue
            image_name = result.get("image_name") or f"image_{offset}"
            preview = result.get("annotated_image_base64")
            for det in result.get("detections") or []:
                items.append(
                    {
                        "detection_index": offset,
                        "class_id": det.get("class_id"),
                        "class_name": det.get("class_name"),
                        "confidence": det.get("confidence"),
                        "bbox": det.get("bbox"),
                        "source_label": image_name,
                        "preview_base64": preview,
                    }
                )
                offset += 1
        return items

    if result_type == "video" or payload.get("key_frames"):
        offset = 0
        for frame in payload.get("key_frames") or []:
            label = f"frame_{frame.get('frame_index', offset)}"
            preview = frame.get("annotated_image_base64")
            for det in frame.get("detections") or []:
                items.append(
                    {
                        "detection_index": offset,
                        "class_id": det.get("class_id"),
                        "class_name": det.get("class_name"),
                        "confidence": det.get("confidence"),
                        "bbox": det.get("bbox"),
                        "source_label": label,
                        "preview_base64": preview,
                    }
                )
                offset += 1
        return items

    return items


def _get_owned_history(db: Session, history_id: int, user_id: int) -> dict:
    ensure_history_records_table(db)
    row = db.execute(
        text(
            """
            SELECT *
            FROM history_records
            WHERE id = :history_id
              AND user_id = :user_id
              AND record_type = 'detection'
            """
        ),
        {"history_id": history_id, "user_id": user_id},
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="检测历史不存在或无权限访问")

    return row_to_dict(row)


@router.get("/tasks", summary="待复核/已复核检测任务列表")
def list_review_tasks(
    limit: int = Query(default=30, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_history_records_table(db)
    ensure_defect_reviews_table(db)
    user_id = get_user_id(current_user)

    rows = db.execute(
        text(
            """
            SELECT
                h.id,
                h.title,
                h.summary,
                h.meta,
                h.created_at,
                h.result_payload,
                COALESCE(r.reviewed_count, 0) AS reviewed_count
            FROM history_records h
            LEFT JOIN (
                SELECT history_id, COUNT(*) AS reviewed_count
                FROM defect_reviews
                WHERE user_id = :user_id
                GROUP BY history_id
            ) r ON r.history_id = h.id
            WHERE h.user_id = :user_id
              AND h.record_type = 'detection'
            ORDER BY h.created_at DESC
            LIMIT :limit
            """
        ),
        {"user_id": user_id, "limit": limit},
    ).mappings().all()

    data = []
    for row in rows:
        payload = _parse_payload(row["result_payload"])
        detections = flatten_detections(payload)
        total = len(detections)
        reviewed = int(row["reviewed_count"] or 0)
        data.append(
            {
                "history_id": row["id"],
                "title": row["title"],
                "summary": row["summary"],
                "meta": row["meta"],
                "created_at": row["created_at"],
                "total_defects": total,
                "reviewed_count": reviewed,
                "pending_count": max(total - reviewed, 0),
                "status": (
                    "done"
                    if total > 0 and reviewed >= total
                    else ("partial" if reviewed > 0 else "pending")
                ),
                "detect_mode": payload.get("detect_mode") or payload.get("type") or "single",
            }
        )

    return {"code": 200, "message": "ok", "data": data}


@router.get("/task/{history_id}", summary="获取检测任务与复核状态")
def get_review_task(
    history_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_defect_reviews_table(db)
    user_id = get_user_id(current_user)
    history = _get_owned_history(db, history_id, user_id)
    payload = _parse_payload(history.get("result_payload"))
    detections = flatten_detections(payload)

    review_rows = db.execute(
        text(
            """
            SELECT *
            FROM defect_reviews
            WHERE history_id = :history_id
              AND user_id = :user_id
            ORDER BY detection_index ASC
            """
        ),
        {"history_id": history_id, "user_id": user_id},
    ).mappings().all()

    reviews_by_index = {}
    for row in review_rows:
        item = dict(row)
        if item.get("bbox") and isinstance(item["bbox"], str):
            try:
                item["bbox"] = json.loads(item["bbox"])
            except Exception:
                pass
        reviews_by_index[int(item["detection_index"])] = item

    merged = []
    for det in detections:
        idx = int(det["detection_index"])
        review = reviews_by_index.get(idx)
        merged.append(
            {
                **det,
                "verdict": review.get("verdict") if review else None,
                "comment": review.get("comment") if review else "",
                "reviewed": bool(review),
                "review_id": review.get("id") if review else None,
                "updated_at": review.get("updated_at") if review else None,
            }
        )

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "history_id": history_id,
            "title": history.get("title"),
            "summary": history.get("summary"),
            "created_at": history.get("created_at"),
            "result_payload": payload,
            "items": merged,
            "stats": {
                "total": len(merged),
                "reviewed": sum(1 for item in merged if item["reviewed"]),
                "confirmed": sum(1 for item in merged if item.get("verdict") == "confirmed"),
                "false_positive": sum(
                    1 for item in merged if item.get("verdict") == "false_positive"
                ),
                "unsure": sum(1 for item in merged if item.get("verdict") == "unsure"),
            },
        },
    }


@router.put("/task/{history_id}/items", summary="保存缺陷复核结果")
def save_review_items(
    history_id: int,
    body: ReviewBatchSave,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_defect_reviews_table(db)
    user_id = get_user_id(current_user)
    history = _get_owned_history(db, history_id, user_id)
    payload = _parse_payload(history.get("result_payload"))
    detections = flatten_detections(payload)
    max_index = len(detections) - 1

    if not body.items:
        raise HTTPException(status_code=400, detail="items 不能为空")

    now = datetime.now()
    saved = 0

    for item in body.items:
        if item.detection_index > max_index:
            raise HTTPException(
                status_code=400,
                detail=f"detection_index 超出范围：{item.detection_index}",
            )

        source = detections[item.detection_index]
        class_name = item.class_name or source.get("class_name")
        confidence = (
            item.confidence
            if item.confidence is not None
            else source.get("confidence")
        )
        bbox = item.bbox or source.get("bbox")
        source_label = item.source_label or source.get("source_label")
        bbox_text = json.dumps(bbox, ensure_ascii=False) if bbox is not None else None

        db.execute(
            text(
                """
                INSERT INTO defect_reviews (
                    history_id, user_id, detection_index, verdict, comment,
                    class_name, confidence, bbox, source_label, created_at, updated_at
                ) VALUES (
                    :history_id, :user_id, :detection_index, :verdict, :comment,
                    :class_name, :confidence, :bbox, :source_label, :created_at, :updated_at
                )
                ON CONFLICT (history_id, detection_index)
                DO UPDATE SET
                    verdict = EXCLUDED.verdict,
                    comment = EXCLUDED.comment,
                    class_name = EXCLUDED.class_name,
                    confidence = EXCLUDED.confidence,
                    bbox = EXCLUDED.bbox,
                    source_label = EXCLUDED.source_label,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "history_id": history_id,
                "user_id": user_id,
                "detection_index": item.detection_index,
                "verdict": item.verdict,
                "comment": (item.comment or "").strip(),
                "class_name": class_name,
                "confidence": confidence,
                "bbox": bbox_text,
                "source_label": source_label,
                "created_at": now,
                "updated_at": now,
            },
        )
        saved += 1

    db.commit()

    return {
        "code": 200,
        "message": f"已保存 {saved} 条复核结果",
        "data": {
            "history_id": history_id,
            "saved": saved,
        },
    }


@router.get("/stats", summary="复核统计概览")
def get_review_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_defect_reviews_table(db)
    ensure_history_records_table(db)
    user_id = get_user_id(current_user)

    counts = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_reviews,
                COUNT(*) FILTER (WHERE verdict = 'confirmed') AS confirmed,
                COUNT(*) FILTER (WHERE verdict = 'false_positive') AS false_positive,
                COUNT(*) FILTER (WHERE verdict = 'unsure') AS unsure
            FROM defect_reviews
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()

    return {
        "code": 200,
        "message": "ok",
        "data": dict(counts or {}),
    }
