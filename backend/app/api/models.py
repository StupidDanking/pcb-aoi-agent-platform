import csv
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/models", tags=["模型版本"])

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = BACKEND_ROOT / "models"
ACTIVE_MODEL_FILE = MODELS_DIR / "active_model.json"


class ActiveModelRequest(BaseModel):
    version: str


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_results_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []

    rows = []

    with open(path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            item = {}

            for key, value in row.items():
                clean_key = key.strip()

                try:
                    item[clean_key] = float(value)
                except Exception:
                    item[clean_key] = value

            rows.append(item)

    return rows


def get_model_dir(version: str) -> Path:
    if version.startswith("pcb_aoi_"):
        return MODELS_DIR / version

    return MODELS_DIR / f"pcb_aoi_{version}"


def get_active_model_name() -> str:
    data = read_json(ACTIVE_MODEL_FILE)
    return data.get("model_name", "")


def set_active_model_name(model_name: str):
    write_json(ACTIVE_MODEL_FILE, {
        "model_name": model_name,
    })


def build_model_item(model_dir: Path) -> dict:
    meta_path = model_dir / "model_meta.json"
    meta = read_json(meta_path)

    best_path = model_dir / "best.pt"
    last_path = model_dir / "last.pt"
    results_csv = model_dir / "results.csv"

    metrics = read_results_csv(results_csv)
    last_metric = metrics[-1] if metrics else {}

    version = meta.get("version") or model_dir.name.replace("pcb_aoi_", "")
    active_model_name = get_active_model_name()

    # 如果还没设置 active_model，则默认 v1.0.0 是当前模型
    is_active = active_model_name == model_dir.name
    if not active_model_name and model_dir.name == "pcb_aoi_v1.0.0":
        is_active = True

    return {
        "version": version,
        "name": model_dir.name,
        "display_name": meta.get("display_name") or model_dir.name,
        "description": meta.get("description") or "",
        "model_type": meta.get("model_type") or "YOLOv11",
        "dataset": meta.get("dataset") or "pcb_defect",
        "epochs": meta.get("epochs") or int(last_metric.get("epoch", 0) or 0),
        "image_size": meta.get("image_size") or 640,
        "batch_size": meta.get("batch_size"),
        "device": meta.get("device") or "",
        "is_default": is_active,
        "has_best": best_path.exists(),
        "has_last": last_path.exists(),
        "has_results_csv": results_csv.exists(),
        "best_size_mb": round(best_path.stat().st_size / 1024 / 1024, 2) if best_path.exists() else 0,
        "precision": meta.get("precision", last_metric.get("metrics/precision(B)")),
        "recall": meta.get("recall", last_metric.get("metrics/recall(B)")),
        "map50": meta.get("map50", last_metric.get("metrics/mAP50(B)")),
        "map50_95": meta.get("map50_95", last_metric.get("metrics/mAP50-95(B)")),
        "train_box_loss": meta.get("train_box_loss", last_metric.get("train/box_loss")),
        "train_cls_loss": meta.get("train_cls_loss", last_metric.get("train/cls_loss")),
        "train_dfl_loss": meta.get("train_dfl_loss", last_metric.get("train/dfl_loss")),
        "val_box_loss": meta.get("val_box_loss", last_metric.get("val/box_loss")),
        "val_cls_loss": meta.get("val_cls_loss", last_metric.get("val/cls_loss")),
        "val_dfl_loss": meta.get("val_dfl_loss", last_metric.get("val/dfl_loss")),
        "artifacts": {
            "results_png": (model_dir / "results.png").exists(),
            "confusion_matrix": (model_dir / "confusion_matrix.png").exists(),
            "confusion_matrix_normalized": (model_dir / "confusion_matrix_normalized.png").exists(),
            "BoxPR_curve": (model_dir / "BoxPR_curve.png").exists(),
            "BoxF1_curve": (model_dir / "BoxF1_curve.png").exists(),
            "BoxP_curve": (model_dir / "BoxP_curve.png").exists(),
            "BoxR_curve": (model_dir / "BoxR_curve.png").exists(),
        },
    }


@router.get("")
def list_models():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    model_dirs = [
        path
        for path in MODELS_DIR.iterdir()
        if path.is_dir() and path.name.startswith("pcb_aoi_")
    ]

    items = [
        build_model_item(model_dir)
        for model_dir in sorted(model_dirs, key=lambda p: p.name)
    ]

    return {
        "code": 200,
        "message": "获取模型版本成功",
        "data": items,
    }


@router.get("/active")
def get_active_model():
    active_model_name = get_active_model_name()

    if not active_model_name:
        active_model_name = "pcb_aoi_v1.0.0"

    model_dir = MODELS_DIR / active_model_name

    return {
        "code": 200,
        "message": "获取当前模型成功",
        "data": {
            "model_name": active_model_name,
            "exists": model_dir.exists(),
            "best_exists": (model_dir / "best.pt").exists(),
        },
    }


@router.post("/active")
def set_active_model(data: ActiveModelRequest):
    model_dir = get_model_dir(data.version)

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail="模型版本不存在")

    best_path = model_dir / "best.pt"

    if not best_path.exists():
        raise HTTPException(status_code=400, detail="该模型版本没有 best.pt，不能设为当前模型")

    set_active_model_name(model_dir.name)

    return {
        "code": 200,
        "message": "当前检测模型设置成功",
        "data": {
            "model_name": model_dir.name,
            "version": model_dir.name.replace("pcb_aoi_", ""),
            "best_path": str(best_path),
        },
    }


@router.get("/{version}")
def get_model_detail(version: str):
    model_dir = get_model_dir(version)

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail="模型版本不存在")

    return {
        "code": 200,
        "message": "获取模型详情成功",
        "data": build_model_item(model_dir),
    }


@router.get("/{version}/metrics")
def get_model_metrics(version: str):
    model_dir = get_model_dir(version)

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail="模型版本不存在")

    rows = read_results_csv(model_dir / "results.csv")

    return {
        "code": 200,
        "message": "获取训练曲线成功",
        "data": rows,
    }


@router.get("/{version}/artifact/{filename}")
def get_model_artifact(version: str, filename: str):
    allowed_files = {
        "results.png",
        "confusion_matrix.png",
        "confusion_matrix_normalized.png",
        "BoxPR_curve.png",
        "BoxF1_curve.png",
        "BoxP_curve.png",
        "BoxR_curve.png",
        "results.csv",
        "args.yaml",
    }

    if filename not in allowed_files:
        raise HTTPException(status_code=400, detail="不允许访问该文件")

    model_dir = get_model_dir(version)
    file_path = model_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(str(file_path))