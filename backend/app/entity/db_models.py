
"""
数据库模型定义

表结构总览：
- 用户权限：users, roles, permissions, user_roles, role_permissions
- 检测业务：detection_scenes, detection_tasks, detection_results
- 模型管理：training_tasks, training_metrics, model_versions
- 智能体：chat_sessions, chat_messages
- 系统运维：operation_logs
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


# ============================================================
# 一、用户与权限 RBAC
# ============================================================

class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="加密后的密码")

    phone = Column(String(20), nullable=True, comment="手机号")
    avatar = Column(String(500), nullable=True, comment="头像 URL")

    is_active = Column(Boolean, default=True, comment="是否启用")
    is_superuser = Column(Boolean, default=False, comment="是否超级管理员")

    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    detection_tasks = relationship("DetectionTask", back_populates="user")
    training_tasks = relationship("TrainingTask", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")
    operation_logs = relationship("OperationLog", back_populates="user")


class Role(Base):
    """角色表"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="角色标识，如 admin/operator/viewer")
    display_name = Column(String(100), nullable=False, comment="角色显示名，如 管理员/操作员/访客")
    description = Column(String(500), nullable=True, comment="角色描述")
    is_system = Column(Boolean, default=False, comment="是否系统内置角色")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class Permission(Base):
    """权限表"""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False, comment="权限编码，如 detection:task:create")
    name = Column(String(100), nullable=False, comment="权限名称")
    module = Column(String(50), nullable=False, comment="所属模块：auth/detection/training/agent/system")
    description = Column(String(500), nullable=True, comment="权限描述")

    role_permissions = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class UserRole(Base):
    """用户-角色关联表"""

    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class RolePermission(Base):
    """角色-权限关联表"""

    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False, index=True)

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


# ============================================================
# 二、检测业务
# ============================================================

class DetectionScene(Base):
    """
    检测场景配置表

    每个小组或业务方向一个场景，例如：
    遥感检测、工业缺陷检测、农业病害检测、交通检测等。
    """

    __tablename__ = "detection_scenes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="场景标识，如 remote_sensing")
    display_name = Column(String(100), nullable=False, comment="场景显示名，如 遥感目标检测")
    description = Column(Text, nullable=True, comment="场景描述")
    category = Column(String(50), nullable=False, comment="场景分类：agriculture/industry/remote_sensing/medical/traffic")

    class_names = Column(JSON, nullable=False, comment='类别列表，如 ["airplane", "storage-tank"]')
    class_names_cn = Column(JSON, nullable=True, comment='类别中文名映射，如 {"airplane": "飞机"}')

    is_active = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    detection_tasks = relationship("DetectionTask", back_populates="scene")
    training_tasks = relationship("TrainingTask", back_populates="scene")
    model_versions = relationship("ModelVersion", back_populates="scene")


class DetectionTask(Base):
    """检测任务表：每次检测操作生成一条任务记录"""

    __tablename__ = "detection_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="操作用户")
    scene_id = Column(Integer, ForeignKey("detection_scenes.id"), nullable=False, index=True, comment="检测场景")
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True, comment="使用的模型版本")

    task_type = Column(String(20), nullable=False, comment="检测类型：single/batch/folder/video/camera")
    status = Column(String(20), default="pending", comment="状态：pending/processing/completed/failed")

    total_images = Column(Integer, default=0, comment="处理图像总数")
    total_objects = Column(Integer, default=0, comment="检测到的目标总数")
    total_inference_time = Column(Float, default=0, comment="总推理耗时，单位 ms")

    conf_threshold = Column(Float, default=0.25, comment="置信度阈值")
    iou_threshold = Column(Float, default=0.45, comment="NMS IoU 阈值")
    image_size = Column(Integer, default=640, comment="推理图像尺寸")

    error_message = Column(Text, nullable=True, comment="失败时的错误信息")

    analysis_report = Column(Text, nullable=True, comment="分析报告，Markdown 格式")
    analysis_suggestion = Column(Text, nullable=True, comment="专业建议")
    risk_level = Column(String(20), nullable=True, comment="风险等级：low/medium/high/critical")
    analyzed_at = Column(DateTime, nullable=True, comment="分析完成时间")

    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    user = relationship("User", back_populates="detection_tasks")
    scene = relationship("DetectionScene", back_populates="detection_tasks")
    model_version = relationship("ModelVersion", back_populates="detection_tasks")
    results = relationship("DetectionResult", back_populates="task", cascade="all, delete-orphan")


class DetectionResult(Base):
    """检测结果表：每张图像中每个检测到的目标一条记录"""

    __tablename__ = "detection_results"

    id = Column(Integer, primary_key=True, autoincrement=True)

    task_id = Column(Integer, ForeignKey("detection_tasks.id"), nullable=False, index=True, comment="所属检测任务")

    image_path = Column(String(500), nullable=False, comment="原始图像路径")
    image_url = Column(String(500), nullable=True, comment="原始图像访问 URL")
    annotated_image_url = Column(String(500), nullable=True, comment="标注后图像 URL")

    class_id = Column(Integer, nullable=False, comment="类别编号")
    class_name = Column(String(100), nullable=False, index=True, comment="类别英文名")
    class_name_cn = Column(String(100), nullable=True, comment="类别中文名")

    confidence = Column(Float, nullable=False, comment="置信度")
    bbox = Column(JSON, nullable=False, comment='边界框，如 {"x1":0,"y1":0,"x2":100,"y2":100}')
    bbox_normalized = Column(JSON, nullable=True, comment="归一化边界框")

    inference_time = Column(Float, nullable=True, comment="单图推理耗时，单位 ms")
    image_width = Column(Integer, nullable=True, comment="图像宽度")
    image_height = Column(Integer, nullable=True, comment="图像高度")

    created_at = Column(DateTime, default=datetime.now)

    task = relationship("DetectionTask", back_populates="results")


# ============================================================
# 三、模型训练与模型版本
# ============================================================

class TrainingTask(Base):
    """训练任务表"""

    __tablename__ = "training_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="创建用户")
    scene_id = Column(Integer, ForeignKey("detection_scenes.id"), nullable=False, index=True, comment="训练场景")

    task_name = Column(String(100), nullable=False, comment="训练任务名称")
    status = Column(String(20), default="pending", comment="状态：pending/running/completed/failed/stopped")

    dataset_path = Column(String(500), nullable=False, comment="数据集路径")
    data_yaml_path = Column(String(500), nullable=True, comment="data.yaml 路径")

    base_model = Column(String(100), default="yolov11n.pt", comment="基础模型")
    epochs = Column(Integer, default=100, comment="训练轮数")
    batch_size = Column(Integer, default=16, comment="批大小")
    image_size = Column(Integer, default=640, comment="图像尺寸")
    device = Column(String(50), default="cpu", comment="训练设备，如 cpu/cuda/0")

    current_epoch = Column(Integer, default=0, comment="当前 epoch")
    progress = Column(Float, default=0.0, comment="训练进度百分比")

    best_map50 = Column(Float, nullable=True, comment="最佳 mAP@0.50")
    best_map50_95 = Column(Float, nullable=True, comment="最佳 mAP@0.50:0.95")
    best_model_path = Column(String(500), nullable=True, comment="最佳模型路径")
    last_model_path = Column(String(500), nullable=True, comment="最后模型路径")

    log_path = Column(String(500), nullable=True, comment="训练日志路径")
    output_dir = Column(String(500), nullable=True, comment="训练输出目录")
    error_message = Column(Text, nullable=True, comment="失败原因")

    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="training_tasks")
    scene = relationship("DetectionScene", back_populates="training_tasks")
    metrics = relationship("TrainingMetric", back_populates="task", cascade="all, delete-orphan")
    model_versions = relationship("ModelVersion", back_populates="training_task")


class TrainingMetric(Base):
    """训练指标表：每个 epoch 一条记录"""

    __tablename__ = "training_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)

    task_id = Column(Integer, ForeignKey("training_tasks.id"), nullable=False, index=True)
    epoch = Column(Integer, nullable=False, comment="第几个 epoch")

    box_loss = Column(Float, nullable=True, comment="边界框损失")
    cls_loss = Column(Float, nullable=True, comment="分类损失")
    dfl_loss = Column(Float, nullable=True, comment="DFL 损失")

    precision = Column(Float, nullable=True, comment="精确率")
    recall = Column(Float, nullable=True, comment="召回率")
    map50 = Column(Float, nullable=True, comment="mAP@0.50")
    map50_95 = Column(Float, nullable=True, comment="mAP@0.50:0.95")

    lr = Column(Float, nullable=True, comment="学习率")
    created_at = Column(DateTime, default=datetime.now)

    task = relationship("TrainingTask", back_populates="metrics")


class ModelVersion(Base):
    """模型版本管理表：每次训练产出或手动上传一个版本"""

    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    scene_id = Column(Integer, ForeignKey("detection_scenes.id"), nullable=False, index=True, comment="所属场景")
    training_task_id = Column(Integer, ForeignKey("training_tasks.id"), nullable=True, comment="来源训练任务")

    version = Column(String(50), nullable=False, comment="版本号，如 v1.0.0")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    model_type = Column(String(50), default="yolov11n", comment="模型类型：yolov11n/s/m/l/x")
    status = Column(String(20), default="active", comment="状态：active/archived/deleted")

    model_path = Column(String(500), nullable=False, comment="本地模型文件路径")
    minio_url = Column(String(500), nullable=True, comment="MinIO 存储 URL")

    map50 = Column(Float, nullable=True, comment="mAP@0.50")
    map50_95 = Column(Float, nullable=True, comment="mAP@0.50:0.95")
    precision = Column(Float, nullable=True, comment="精确率")
    recall = Column(Float, nullable=True, comment="召回率")
    per_class_ap = Column(JSON, nullable=True, comment="各类别 AP")

    description = Column(Text, nullable=True, comment="版本描述")
    file_size = Column(BigInteger, nullable=True, comment="模型文件大小，单位字节")

    created_at = Column(DateTime, default=datetime.now)

    scene = relationship("DetectionScene", back_populates="model_versions")
    training_task = relationship("TrainingTask", back_populates="model_versions")
    detection_tasks = relationship("DetectionTask", back_populates="model_version")


# ============================================================
# 四、智能体对话
# ============================================================

class ChatSession(Base):
    """智能体对话会话表"""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=True, comment="会话标题")
    scene_id = Column(Integer, ForeignKey("detection_scenes.id"), nullable=True, comment="关联检测场景")

    status = Column(String(20), default="active", comment="状态：active/archived/deleted")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """智能体对话消息表"""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)

    role = Column(String(20), nullable=False, comment="消息角色：user/assistant/system/tool")
    content = Column(Text, nullable=False, comment="消息内容")

    agent_name = Column(String(100), nullable=True, comment="处理该消息的 Agent 名称")
    intent = Column(String(100), nullable=True, comment="识别出的用户意图")
    tool_calls = Column(JSON, nullable=True, comment="工具调用记录")
    extra_metadata = Column(JSON, nullable=True, comment="扩展元数据")

    created_at = Column(DateTime, default=datetime.now)

    session = relationship("ChatSession", back_populates="messages")


# ============================================================
# 五、系统运维
# ============================================================

class OperationLog(Base):
    """操作审计日志表"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, comment="操作动作，如 auth:login")
    module = Column(String(50), nullable=False, comment="所属模块")
    description = Column(Text, nullable=True, comment="操作描述")

    ip_address = Column(String(50), nullable=True, comment="IP 地址")
    user_agent = Column(String(500), nullable=True, comment="浏览器 User-Agent")
    request_method = Column(String(20), nullable=True, comment="请求方法")
    request_path = Column(String(500), nullable=True, comment="请求路径")
    request_params = Column(JSON, nullable=True, comment="请求参数")

    status = Column(String(20), default="success", comment="状态：success/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")

    created_at = Column(DateTime, default=datetime.now, index=True)

    user = relationship("User", back_populates="operation_logs")
