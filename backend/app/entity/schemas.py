
"""
Pydantic 请求/响应模型

用途：
- 请求参数校验
- API 响应序列化
- 避免把数据库敏感字段直接暴露给前端
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


# ============================================================
# 一、用户与认证
# ============================================================

class UserRegister(BaseModel):
    """用户注册请求"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserLogin(BaseModel):
    """用户登录请求"""

    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """登录成功后的 Token 响应"""

    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    """用户响应模型，不包含 hashed_password"""

    id: int
    username: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    is_superuser: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户信息更新请求"""

    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=100)


# ============================================================
# 二、角色与权限
# ============================================================

class RoleResponse(BaseModel):
    """角色响应"""

    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    """权限响应"""

    id: int
    code: str
    name: str
    module: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# 三、检测场景
# ============================================================

class DetectionSceneCreate(BaseModel):
    """创建检测场景"""

    name: str = Field(..., description="场景标识，如 remote_sensing")
    display_name: str = Field(..., description="场景显示名，如 遥感目标检测")
    description: Optional[str] = None
    category: str = Field(..., description="场景分类：agriculture/industry/remote_sensing/medical/traffic")
    class_names: list[str] = Field(..., description="类别英文名列表")
    class_names_cn: Optional[dict[str, str]] = Field(default=None, description="类别中文名映射")


class DetectionSceneUpdate(BaseModel):
    """更新检测场景"""

    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    class_names: Optional[list[str]] = None
    class_names_cn: Optional[dict[str, str]] = None
    is_active: Optional[bool] = None


class DetectionSceneResponse(BaseModel):
    """检测场景响应"""

    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    category: str
    class_names: list[str]
    class_names_cn: Optional[dict[str, str]] = None
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 四、检测任务与检测结果
# ============================================================

class DetectionTaskCreate(BaseModel):
    """创建检测任务"""

    scene_id: int
    model_version_id: Optional[int] = None
    task_type: str = Field(..., description="single/batch/folder/video/camera")
    conf_threshold: float = Field(default=0.25, ge=0, le=1)
    iou_threshold: float = Field(default=0.45, ge=0, le=1)
    image_size: int = Field(default=640, ge=32)


class DetectionTaskResponse(BaseModel):
    """检测任务响应"""

    id: int
    user_id: int
    scene_id: int
    model_version_id: Optional[int] = None
    task_type: str
    status: str

    total_images: int
    total_objects: int
    total_inference_time: float

    conf_threshold: float
    iou_threshold: float
    image_size: int

    error_message: Optional[str] = None
    analysis_report: Optional[str] = None
    analysis_suggestion: Optional[str] = None
    risk_level: Optional[str] = None
    analyzed_at: Optional[datetime] = None

    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DetectionResultResponse(BaseModel):
    """检测结果响应"""

    id: int
    task_id: int

    image_path: str
    image_url: Optional[str] = None
    annotated_image_url: Optional[str] = None

    class_id: int
    class_name: str
    class_name_cn: Optional[str] = None

    confidence: float
    bbox: dict[str, Any]
    bbox_normalized: Optional[dict[str, Any]] = None

    inference_time: Optional[float] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None

    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 五、训练任务与模型版本
# ============================================================

class TrainingTaskCreate(BaseModel):
    """创建训练任务"""

    scene_id: int
    task_name: str
    dataset_path: str
    data_yaml_path: Optional[str] = None

    base_model: str = "yolov11n.pt"
    epochs: int = Field(default=100, ge=1)
    batch_size: int = Field(default=16, ge=1)
    image_size: int = Field(default=640, ge=32)
    device: str = "cpu"


class TrainingTaskResponse(BaseModel):
    """训练任务响应"""

    id: int
    user_id: int
    scene_id: int
    task_name: str
    status: str

    dataset_path: str
    data_yaml_path: Optional[str] = None

    base_model: str
    epochs: int
    batch_size: int
    image_size: int
    device: str

    current_epoch: int
    progress: float

    best_map50: Optional[float] = None
    best_map50_95: Optional[float] = None
    best_model_path: Optional[str] = None
    last_model_path: Optional[str] = None

    log_path: Optional[str] = None
    output_dir: Optional[str] = None
    error_message: Optional[str] = None

    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrainingMetricResponse(BaseModel):
    """训练指标响应"""

    id: int
    task_id: int
    epoch: int

    box_loss: Optional[float] = None
    cls_loss: Optional[float] = None
    dfl_loss: Optional[float] = None

    precision: Optional[float] = None
    recall: Optional[float] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None

    lr: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ModelVersionResponse(BaseModel):
    """模型版本响应"""

    id: int
    scene_id: int
    training_task_id: Optional[int] = None

    version: str
    model_name: str
    model_type: str
    status: str

    model_path: str
    minio_url: Optional[str] = None

    map50: Optional[float] = None
    map50_95: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    per_class_ap: Optional[dict[str, Any]] = None

    description: Optional[str] = None
    file_size: Optional[int] = None

    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 六、智能体对话
# ============================================================

class ChatSessionCreate(BaseModel):
    """创建对话会话"""

    title: Optional[str] = None
    scene_id: Optional[int] = None


class ChatSessionResponse(BaseModel):
    """对话会话响应"""

    id: int
    user_id: int
    title: Optional[str] = None
    scene_id: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    """创建对话消息"""

    content: str
    role: str = "user"


class ChatMessageResponse(BaseModel):
    """对话消息响应"""

    id: int
    session_id: int
    role: str
    content: str

    agent_name: Optional[str] = None
    intent: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    extra_metadata: Optional[dict[str, Any]] = None

    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 七、操作日志
# ============================================================

class OperationLogResponse(BaseModel):
    """操作日志响应"""

    id: int
    user_id: Optional[int] = None
    action: str
    module: str
    description: Optional[str] = None

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    request_params: Optional[dict[str, Any]] = None

    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 八、通用模型
# ============================================================

class ApiResponse(BaseModel):
    """统一 API 响应"""

    code: int = 200
    message: str = "success"
    data: Optional[dict | list] = None


class PageParams(BaseModel):
    """分页查询参数"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class PageResponse(BaseModel):
    """分页响应"""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: list


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = "healthy"
    app_name: str
    version: str
    database: Optional[str] = None
    redis: Optional[str] = None
    minio: Optional[str] = None
