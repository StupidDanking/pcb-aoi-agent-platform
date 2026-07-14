import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import SessionLocal


router = APIRouter(prefix="/api/history", tags=["历史记录"])


class ChatSessionCreate(BaseModel):
    title: str = "新的对话"


class ChatMessageCreate(BaseModel):
    session_id: Optional[int] = None
    role: str
    content: str
    title: Optional[str] = None

    # 新增：用于把检测结果保存到聊天消息里
    tool_name: Optional[str] = None
    detect_mode: Optional[str] = None
    result_payload: Optional[dict] = None


class DetectionHistoryCreate(BaseModel):
    title: str
    image_name: Optional[str] = None
    model_version: Optional[str] = "pcb_aoi_v1.0.0"
    status: Optional[str] = "completed"
    result_count: Optional[int] = 0
    summary: Optional[str] = None
    result_payload: Optional[dict] = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_id(current_user) -> int:
    if isinstance(current_user, dict):
        return int(current_user.get("id"))

    return int(getattr(current_user, "id"))


def row_to_dict(row):
    if row is None:
        return None

    return dict(row._mapping)


def ensure_history_records_table(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS history_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            record_type VARCHAR(32) NOT NULL,
            source_id INTEGER,
            title TEXT NOT NULL,
            meta TEXT,
            icon VARCHAR(16),
            path TEXT,
            summary TEXT,
            result_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    db.execute(text("""
        ALTER TABLE history_records
        ADD COLUMN IF NOT EXISTS result_payload TEXT
    """))

    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_history_records_user_updated
        ON history_records(user_id, updated_at DESC)
    """))

    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_history_records_type
        ON history_records(record_type)
    """))

    db.commit()


def ensure_agent_chat_tables(db: Session):
    """
    智能问答历史专用表。

    不使用旧的 chat_sessions / chat_messages，
    避免和 Alembic 生成的业务表字段结构冲突。
    """

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS agent_chat_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS agent_chat_messages (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role VARCHAR(32) NOT NULL,
            content TEXT,
            tool_name VARCHAR(64),
            detect_mode VARCHAR(32),
            result_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # 给旧表补字段
    db.execute(text("""
        ALTER TABLE agent_chat_messages
        ADD COLUMN IF NOT EXISTS tool_name VARCHAR(64)
    """))

    db.execute(text("""
        ALTER TABLE agent_chat_messages
        ADD COLUMN IF NOT EXISTS detect_mode VARCHAR(32)
    """))

    db.execute(text("""
        ALTER TABLE agent_chat_messages
        ADD COLUMN IF NOT EXISTS result_payload TEXT
    """))

    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_agent_chat_sessions_user_updated
        ON agent_chat_sessions(user_id, updated_at DESC)
    """))

    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_agent_chat_messages_session
        ON agent_chat_messages(session_id, created_at ASC, id ASC)
    """))

    db.commit()


def upsert_chat_history_record(
    db: Session,
    user_id: int,
    session_id: int,
    title: str,
    summary: str = "",
):
    existing = db.execute(text("""
        SELECT id
        FROM history_records
        WHERE user_id = :user_id
          AND record_type = 'chat'
          AND source_id = :source_id
        LIMIT 1
    """), {
        "user_id": user_id,
        "source_id": session_id,
    }).fetchone()

    if existing:
        db.execute(text("""
            UPDATE history_records
            SET title = :title,
                summary = :summary,
                meta = '智能问答',
                icon = '✦',
                path = :path,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "id": existing[0],
            "title": title,
            "summary": summary,
            "path": f"/chat?session_id={session_id}",
        })
    else:
        db.execute(text("""
            INSERT INTO history_records (
                user_id,
                record_type,
                source_id,
                title,
                meta,
                icon,
                path,
                summary,
                created_at,
                updated_at
            )
            VALUES (
                :user_id,
                'chat',
                :source_id,
                :title,
                '智能问答',
                '✦',
                :path,
                :summary,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
        """), {
            "user_id": user_id,
            "source_id": session_id,
            "title": title,
            "path": f"/chat?session_id={session_id}",
            "summary": summary,
        })


@router.get("/recent")
def get_recent_histories(
    keyword: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_history_records_table(db)

    user_id = get_user_id(current_user)

    if keyword:
        rows = db.execute(text("""
            SELECT
                id,
                record_type,
                source_id,
                title,
                meta,
                icon,
                path,
                summary,
                created_at,
                updated_at
            FROM history_records
            WHERE user_id = :user_id
              AND (
                title ILIKE :keyword
                OR meta ILIKE :keyword
                OR summary ILIKE :keyword
              )
            ORDER BY updated_at DESC
            LIMIT :limit
        """), {
            "user_id": user_id,
            "keyword": f"%{keyword}%",
            "limit": limit,
        }).fetchall()
    else:
        rows = db.execute(text("""
            SELECT
                id,
                record_type,
                source_id,
                title,
                meta,
                icon,
                path,
                summary,
                created_at,
                updated_at
            FROM history_records
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
            LIMIT :limit
        """), {
            "user_id": user_id,
            "limit": limit,
        }).fetchall()

    items = []

    for row in rows:
        item = row_to_dict(row)

        items.append({
            "id": item["id"],
            "type": item["record_type"],
            "source_id": item["source_id"],
            "title": item["title"],
            "meta": item.get("meta") or "",
            "icon": item.get("icon") or "•",
            "path": item.get("path") or "",
            "summary": item.get("summary") or "",
            "created_at": str(item.get("created_at")),
            "updated_at": str(item.get("updated_at")),
        })

    return {
        "code": 200,
        "message": "获取最近记录成功",
        "data": items,
    }


@router.get("/search")
def search_histories(
    keyword: str = Query(...),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_recent_histories(
        keyword=keyword,
        limit=limit,
        db=db,
        current_user=current_user,
    )


@router.post("/chat/session")
def create_chat_session(
    data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_history_records_table(db)
    ensure_agent_chat_tables(db)

    user_id = get_user_id(current_user)
    title = data.title or "新的对话"

    row = db.execute(text("""
        INSERT INTO agent_chat_sessions (
            user_id,
            title,
            created_at,
            updated_at
        )
        VALUES (
            :user_id,
            :title,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        RETURNING id
    """), {
        "user_id": user_id,
        "title": title,
    }).fetchone()

    session_id = row[0]

    upsert_chat_history_record(
        db=db,
        user_id=user_id,
        session_id=session_id,
        title=title,
        summary="",
    )

    db.commit()

    return {
        "code": 200,
        "message": "创建对话成功",
        "data": {
            "session_id": session_id,
            "title": title,
        },
    }


@router.post("/chat/message")
def create_chat_message(
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_history_records_table(db)
    ensure_agent_chat_tables(db)

    user_id = get_user_id(current_user)
    title = data.title or data.content[:30] or "新的对话"

    if data.session_id:
        session_id = data.session_id

        session = db.execute(text("""
            SELECT id
            FROM agent_chat_sessions
            WHERE id = :session_id
              AND user_id = :user_id
            LIMIT 1
        """), {
            "session_id": session_id,
            "user_id": user_id,
        }).fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="对话不存在")

        db.execute(text("""
            UPDATE agent_chat_sessions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = :session_id
              AND user_id = :user_id
        """), {
            "session_id": session_id,
            "user_id": user_id,
        })
    else:
        row = db.execute(text("""
            INSERT INTO agent_chat_sessions (
                user_id,
                title,
                created_at,
                updated_at
            )
            VALUES (
                :user_id,
                :title,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            RETURNING id
        """), {
            "user_id": user_id,
            "title": title,
        }).fetchone()

        session_id = row[0]

    result_payload_text = None

    if data.result_payload is not None:
        result_payload_text = json.dumps(data.result_payload, ensure_ascii=False)

    message_row = db.execute(text("""
        INSERT INTO agent_chat_messages (
            session_id,
            user_id,
            role,
            content,
            tool_name,
            detect_mode,
            result_payload,
            created_at
        )
        VALUES (
            :session_id,
            :user_id,
            :role,
            :content,
            :tool_name,
            :detect_mode,
            :result_payload,
            CURRENT_TIMESTAMP
        )
        RETURNING id
    """), {
        "session_id": session_id,
        "user_id": user_id,
        "role": data.role,
        "content": data.content,
        "tool_name": data.tool_name,
        "detect_mode": data.detect_mode,
        "result_payload": result_payload_text,
    }).fetchone()

    upsert_chat_history_record(
        db=db,
        user_id=user_id,
        session_id=session_id,
        title=title,
        summary=data.content[:120] if data.content else "",
    )

    db.commit()

    return {
        "code": 200,
        "message": "保存消息成功",
        "data": {
            "session_id": session_id,
            "message_id": message_row[0],
        },
    }


@router.get("/chat/session/{session_id}")
def get_chat_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_agent_chat_tables(db)

    user_id = get_user_id(current_user)

    session_row = db.execute(text("""
        SELECT
            id,
            title,
            created_at,
            updated_at
        FROM agent_chat_sessions
        WHERE id = :session_id
          AND user_id = :user_id
        LIMIT 1
    """), {
        "session_id": session_id,
        "user_id": user_id,
    }).fetchone()

    if not session_row:
        return {
            "code": 200,
            "message": "旧对话记录无法恢复完整内容",
            "data": {
                "id": session_id,
                "title": "历史对话",
                "messages": [
                    {
                        "id": 0,
                        "role": "assistant",
                        "content": "这条旧对话记录来自旧表结构，无法恢复完整聊天内容。之后新产生的对话可以正常恢复。",
                        "tool_name": None,
                        "detect_mode": None,
                        "result_payload": None,
                        "created_at": "",
                    }
                ],
            },
        }

    message_rows = db.execute(text("""
        SELECT
            id,
            role,
            content,
            tool_name,
            detect_mode,
            result_payload,
            created_at
        FROM agent_chat_messages
        WHERE session_id = :session_id
          AND user_id = :user_id
        ORDER BY created_at ASC, id ASC
    """), {
        "session_id": session_id,
        "user_id": user_id,
    }).fetchall()

    session = row_to_dict(session_row)
    messages = [row_to_dict(row) for row in message_rows]

    restored_messages = []

    for item in messages:
        result_payload = None

        if item.get("result_payload"):
            try:
                result_payload = json.loads(item["result_payload"])
            except Exception:
                result_payload = None

        restored_messages.append({
            "id": item["id"],
            "role": item["role"],
            "content": item.get("content") or "",
            "tool_name": item.get("tool_name"),
            "detect_mode": item.get("detect_mode"),
            "result_payload": result_payload,
            "created_at": str(item.get("created_at")),
        })

    return {
        "code": 200,
        "message": "获取对话详情成功",
        "data": {
            "id": session["id"],
            "title": session.get("title") or "新的对话",
            "created_at": str(session.get("created_at")),
            "updated_at": str(session.get("updated_at")),
            "messages": restored_messages,
        },
    }


@router.post("/detection/task")
def create_detection_task_history(
    data: DetectionHistoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_history_records_table(db)

    user_id = get_user_id(current_user)

    model_version = data.model_version or "pcb_aoi_v1.0.0"
    result_count = data.result_count or 0

    meta = f"图片检测 · {model_version} · {result_count} 个缺陷"

    result_payload_text = None
    if data.result_payload is not None:
        result_payload_text = json.dumps(data.result_payload, ensure_ascii=False)

    row = db.execute(text("""
        INSERT INTO history_records (
            user_id,
            record_type,
            source_id,
            title,
            meta,
            icon,
            path,
            summary,
            result_payload,
            created_at,
            updated_at
        )
        VALUES (
            :user_id,
            'detection',
            NULL,
            :title,
            :meta,
            '▧',
            '',
            :summary,
            :result_payload,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        RETURNING id
    """), {
        "user_id": user_id,
        "title": data.title,
        "meta": meta,
        "summary": data.summary or "",
        "result_payload": result_payload_text,
    }).fetchone()

    history_id = row[0]

    db.execute(text("""
        UPDATE history_records
        SET source_id = :history_id,
            path = :path,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :history_id
    """), {
        "history_id": history_id,
        "path": f"/detection?task_id={history_id}",
    })

    db.commit()

    return {
        "code": 200,
        "message": "保存检测历史成功",
        "data": {
            "id": history_id,
            "task_id": history_id,
            "title": data.title,
            "path": f"/detection?task_id={history_id}",
        },
    }


@router.get("/detection/task/{task_id}")
def get_detection_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_history_records_table(db)

    user_id = get_user_id(current_user)

    row = db.execute(text("""
        SELECT
            id,
            source_id,
            title,
            meta,
            path,
            summary,
            result_payload,
            created_at,
            updated_at
        FROM history_records
        WHERE id = :task_id
          AND user_id = :user_id
          AND record_type = 'detection'
        LIMIT 1
    """), {
        "task_id": task_id,
        "user_id": user_id,
    }).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="检测历史不存在")

    item = row_to_dict(row)

    result_payload = None
    if item.get("result_payload"):
        try:
            result_payload = json.loads(item["result_payload"])
        except Exception:
            result_payload = None

    return {
        "code": 200,
        "message": "获取检测历史成功",
        "data": {
            "id": item["id"],
            "task_id": item["id"],
            "source_id": item.get("source_id"),
            "title": item.get("title"),
            "meta": item.get("meta"),
            "path": item.get("path"),
            "summary": item.get("summary"),
            "result_payload": result_payload,
            "created_at": str(item.get("created_at")),
            "updated_at": str(item.get("updated_at")),
        },
    }


@router.delete("/{record_id}")
def delete_history_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_history_records_table(db)
    ensure_agent_chat_tables(db)

    user_id = get_user_id(current_user)

    row = db.execute(text("""
        SELECT
            id,
            record_type,
            source_id
        FROM history_records
        WHERE id = :record_id
          AND user_id = :user_id
        LIMIT 1
    """), {
        "record_id": record_id,
        "user_id": user_id,
    }).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="历史记录不存在")

    item = row_to_dict(row)
    record_type = item.get("record_type")
    source_id = item.get("source_id")

    if record_type == "chat" and source_id:
        db.execute(text("""
            DELETE FROM agent_chat_messages
            WHERE session_id = :session_id
              AND user_id = :user_id
        """), {
            "session_id": source_id,
            "user_id": user_id,
        })

        db.execute(text("""
            DELETE FROM agent_chat_sessions
            WHERE id = :session_id
              AND user_id = :user_id
        """), {
            "session_id": source_id,
            "user_id": user_id,
        })

    db.execute(text("""
        DELETE FROM history_records
        WHERE id = :record_id
          AND user_id = :user_id
    """), {
        "record_id": record_id,
        "user_id": user_id,
    })

    db.commit()

    return {
        "code": 200,
        "message": "删除历史记录成功",
        "data": {
            "id": record_id,
        },
    }