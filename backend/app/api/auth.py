"""
认证相关 API 路由

接口：
- POST /api/auth/register 用户注册
- POST /api/auth/login 用户登录
- GET /api/auth/me 获取当前用户信息
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.user_service import user_service


router = APIRouter(tags=["认证"])

# Swagger 右上角 Authorize 使用的 Bearer Token 认证方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    根据请求头中的 Bearer Token 获取当前登录用户。

    请求头格式：
        Authorization: Bearer <access_token>
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id = int(user_id)
    except (JWTError, ValueError):
        raise credentials_exception

    user = user_service.get_user_by_id(db, user_id)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")

    return user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    """注册新用户"""
    return user_service.create_user(db, user_data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """用户登录，成功后返回 JWT Token"""
    user = user_service.authenticate_user(
        db=db,
        username=form_data.username,
        password=form_data.password,
    )

    access_token = user_service.create_access_token_for_user(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        username=user.username,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户信息"""
    return current_user
