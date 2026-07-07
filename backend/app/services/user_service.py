"""
用户服务层

职责：
- 用户注册
- 用户登录校验
- 根据 ID 查询用户
- 为用户生成 JWT Token
"""

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.entity.db_models import User
from app.entity.schemas import UserRegister


class UserService:
    """用户服务"""

    @staticmethod
    def create_user(db: Session, user_data: UserRegister) -> User:
        """
        创建新用户

        Raises:
            HTTPException: 用户名或邮箱已存在
        """
        existing_user = (
            db.query(User)
            .filter(
                or_(
                    User.username == user_data.username,
                    User.email == user_data.email,
                )
            )
            .first()
        )

        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(status_code=400, detail="用户名已存在")
            raise HTTPException(status_code=400, detail="邮箱已存在")

        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            is_active=True,
            is_superuser=False,
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> User:
        """
        用户登录认证

        username 参数既可以是用户名，也可以是邮箱。

        Raises:
            HTTPException: 用户名或密码错误、用户被禁用
        """
        user = (
            db.query(User)
            .filter(or_(User.username == username, User.email == username))
            .first()
        )

        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="用户已被禁用")

        return user

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        """为用户生成 JWT Token"""
        return create_access_token(data={"sub": str(user.id)})

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """根据 ID 获取用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user

    @staticmethod
    def get_user_roles(db: Session, user: User) -> list[str]:
        """获取用户角色列表"""
        return [user_role.role.name for user_role in user.user_roles]


# 全局单例
user_service = UserService()
