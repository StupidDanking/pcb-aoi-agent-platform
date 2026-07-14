from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.session import SessionLocal


router = APIRouter(tags=["用户认证"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# =========================
# Pydantic Schemas
# =========================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfoResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str = "user"


# =========================
# Database Dependency
# =========================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================
# Password / JWT Utils
# =========================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的登录凭证",
        )


# =========================
# Dynamic SQL Helpers
# =========================

def get_columns(db: Session, table_name: str) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).mappings().all()

    return {row["column_name"] for row in rows}


def insert_dynamic(db: Session, table_name: str, values: dict) -> int:
    columns = get_columns(db, table_name)

    filtered = {
        key: value
        for key, value in values.items()
        if key in columns
    }

    if not filtered:
        raise RuntimeError(f"{table_name} 没有可插入字段")

    col_sql = ", ".join(filtered.keys())
    val_sql = ", ".join([f":{key}" for key in filtered.keys()])

    sql = text(
        f"""
        INSERT INTO {table_name} ({col_sql})
        VALUES ({val_sql})
        RETURNING id
        """
    )

    result = db.execute(sql, filtered)
    return result.scalar_one()


# =========================
# User / Role Helpers
# =========================

def get_user_by_username(db: Session, username: str):
    return db.execute(
        text(
            """
            SELECT *
            FROM users
            WHERE username = :username
            """
        ),
        {"username": username},
    ).mappings().first()


def get_user_by_email(db: Session, email: str):
    return db.execute(
        text(
            """
            SELECT *
            FROM users
            WHERE email = :email
            """
        ),
        {"email": email},
    ).mappings().first()


def get_user_by_id(db: Session, user_id: int):
    return db.execute(
        text(
            """
            SELECT *
            FROM users
            WHERE id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()


def get_user_password_hash(user_row) -> str:
    if "hashed_password" in user_row:
        return user_row["hashed_password"]

    if "password_hash" in user_row:
        return user_row["password_hash"]

    if "password" in user_row:
        return user_row["password"]

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="users 表中没有密码字段",
    )


def get_user_primary_role(db: Session, user_id: int) -> str:
    """
    从数据库读取用户角色。

    优先级：
    admin > developer > user
    """

    rows = db.execute(
        text(
            """
            SELECT r.name
            FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().all()

    role_names = [row["name"] for row in rows]

    if "admin" in role_names:
        return "admin"

    if "developer" in role_names:
        return "developer"

    return "user"


def ensure_role_exists(
    db: Session,
    role_name: str,
    display_name: str,
    description: str,
) -> int:
    role = db.execute(
        text(
            """
            SELECT id
            FROM roles
            WHERE name = :name
            """
        ),
        {"name": role_name},
    ).mappings().first()

    if role:
        return role["id"]

    now = datetime.now()

    role_id = insert_dynamic(
        db,
        "roles",
        {
            "name": role_name,
            "display_name": display_name,
            "description": description,
            "is_system": True,
            "created_at": now,
            "updated_at": now,
        },
    )

    return role_id


def bind_user_role(db: Session, user_id: int, role_id: int):
    exists = db.execute(
        text(
            """
            SELECT 1
            FROM user_roles
            WHERE user_id = :user_id
              AND role_id = :role_id
            """
        ),
        {
            "user_id": user_id,
            "role_id": role_id,
        },
    ).first()

    if exists:
        return

    now = datetime.now()

    insert_dynamic(
        db,
        "user_roles",
        {
            "user_id": user_id,
            "role_id": role_id,
            "created_at": now,
            "updated_at": now,
        },
    )


def bind_default_user_role(db: Session, user_id: int):
    """
    新注册用户默认绑定普通用户角色。
    """

    user_role_id = ensure_role_exists(
        db,
        role_name="user",
        display_name="普通用户",
        description="普通用户：可进行图片检测、查看检测结果和智能问答",
    )

    bind_user_role(db, user_id, user_role_id)


def create_user(db: Session, username: str, email: str, password: str) -> int:
    columns = get_columns(db, "users")

    if "hashed_password" in columns:
        password_column = "hashed_password"
    elif "password_hash" in columns:
        password_column = "password_hash"
    elif "password" in columns:
        password_column = "password"
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="users 表中没有 hashed_password / password_hash / password 字段",
        )

    now = datetime.now()
    hashed_password = get_password_hash(password)

    user_id = insert_dynamic(
        db,
        "users",
        {
            "username": username,
            "email": email,
            password_column: hashed_password,
            "is_active": True,
            "is_superuser": False,
            "created_at": now,
            "updated_at": now,
        },
    )

    return user_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证缺少用户信息",
        )

    user = get_user_by_id(db, int(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    return user


# =========================
# API Routes
# =========================

@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    email = payload.email.strip()
    password = payload.password

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名不能为空",
        )

    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度不能小于 6 位",
        )

    existing_user = get_user_by_username(db, username)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    existing_email = get_user_by_email(db, email)

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在",
        )

    try:
        user_id = create_user(
            db,
            username=username,
            email=email,
            password=password,
        )

        bind_default_user_role(db, user_id)

        db.commit()

        return {
            "code": 200,
            "message": "注册成功",
            "data": {
                "id": user_id,
                "username": username,
                "email": email,
                "role": "user",
            },
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败：{exc}",
        )


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    password = payload.password

    user = get_user_by_username(db, username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    is_active = user.get("is_active", True)

    if is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    hashed_password = get_user_password_hash(user)

    if not verify_password(password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    role = get_user_primary_role(db, user["id"])

    access_token = create_access_token(
        data={
            "sub": str(user["id"]),
            "username": user["username"],
            "role": role,
        }
    )

    try:
        columns = get_columns(db, "users")

        if "last_login_at" in columns:
            db.execute(
                text(
                    """
                    UPDATE users
                    SET last_login_at = :last_login_at
                    WHERE id = :user_id
                    """
                ),
                {
                    "last_login_at": datetime.now(),
                    "user_id": user["id"],
                },
            )
            db.commit()

    except Exception:
        db.rollback()

    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email"),
            "role": role,
        },
    }


@router.get("/me")
def read_current_user(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = get_user_primary_role(db, current_user["id"])

    return {
        "code": 200,
        "message": "获取当前用户成功",
        "data": {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user.get("email"),
            "role": role,
        },
    }