"""
安全工具模块

职责：
- 密码哈希
- 密码校验
- JWT Token 生成
- JWT Token 解析
"""

from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config.settings import settings


# bcrypt 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码进行哈希加密"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码和哈希密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """
    创建 JWT Token

    Args:
        data: 要写入 Token 的载荷，例如 {"sub": "1"}

    Returns:
        JWT Token 字符串
    """
    to_encode = data.copy()
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
    """
    解析 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        Token 载荷数据
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
