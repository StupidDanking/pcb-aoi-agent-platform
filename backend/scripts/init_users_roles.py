"""
初始化系统角色和开发者用户

功能：
1. 创建 user / developer / admin 三个角色
2. 创建五个开发者用户
3. 给五个用户绑定 developer 角色
4. 给其他已有用户绑定 user 角色
5. 自动适配当前数据库表字段

运行方式：
cd D:/shixi/rsod-agent-platform/backend
python scripts/init_users_roles.py
"""

import sys
from pathlib import Path
from datetime import datetime

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from passlib.context import CryptContext
from sqlalchemy import text

from app.database.session import SessionLocal


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


DEVELOPER_USERS = [
    {
        "username": "limuhang",
        "email": "limuhang@pcb-aoi.local",
        "password": "123456",
    },
    {
        "username": "wanshaokun",
        "email": "wanshaokun@pcb-aoi.local",
        "password": "123456",
    },
    {
        "username": "zhouyuhan",
        "email": "zhouyuhan@pcb-aoi.local",
        "password": "123456",
    },
    {
        "username": "lixiang",
        "email": "lixiang@pcb-aoi.local",
        "password": "123456",
    },
    {
        "username": "deming",
        "email": "deming@pcb-aoi.local",
        "password": "123456",
    },
]


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_columns(db, table_name: str) -> set[str]:
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


def insert_dynamic(db, table_name: str, values: dict):
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


def ensure_role(db, role_name: str, display_name: str, description: str):
    role = db.execute(
        text("SELECT id FROM roles WHERE name = :name"),
        {"name": role_name},
    ).mappings().first()

    if role:
        print(f"Role already exists: {role_name}")
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

    print(f"Created role: {role_name}")
    return role_id


def ensure_user(db, username: str, email: str, password: str):
    user = db.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).mappings().first()

    if user:
        print(f"User already exists: {username}")
        return user["id"]

    columns = get_columns(db, "users")

    if "hashed_password" in columns:
        password_column = "hashed_password"
    elif "password_hash" in columns:
        password_column = "password_hash"
    elif "password" in columns:
        password_column = "password"
    else:
        raise RuntimeError("users 表里没有 hashed_password / password_hash / password 字段")

    now = datetime.now()
    password_hash = get_password_hash(password)

    values = {
        "username": username,
        "email": email,
        password_column: password_hash,
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
        "updated_at": now,
    }

    user_id = insert_dynamic(db, "users", values)

    print(f"Created user: {username}")
    return user_id


def bind_user_role(db, user_id: int, role_id: int):
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


def bind_other_users_as_normal_user(db, user_role_id: int):
    developer_names = [item["username"] for item in DEVELOPER_USERS]

    rows = db.execute(
        text(
            """
            SELECT id, username
            FROM users
            """
        )
    ).mappings().all()

    for row in rows:
        username = row["username"]
        user_id = row["id"]

        if username in developer_names:
            continue

        bind_user_role(db, user_id, user_role_id)
        print(f"Bind user role: {username}")


def print_table_columns(db):
    for table_name in ["users", "roles", "user_roles"]:
        columns = sorted(get_columns(db, table_name))
        print(f"{table_name} columns:", columns)


def main():
    db = SessionLocal()

    try:
        print_table_columns(db)

        user_role_id = ensure_role(
            db,
            "user",
            "普通用户",
            "普通用户：可进行图片检测、查看检测结果和智能问答",
        )

        developer_role_id = ensure_role(
            db,
            "developer",
            "算法工程师",
            "算法工程师：可进行模型训练、模型评估、模型导出和模型版本管理",
        )

        admin_role_id = ensure_role(
            db,
            "admin",
            "管理员",
            "管理员：拥有系统全部管理权限",
        )

        for item in DEVELOPER_USERS:
            user_id = ensure_user(
                db,
                username=item["username"],
                email=item["email"],
                password=item["password"],
            )

            bind_user_role(db, user_id, developer_role_id)
            print(f"Bind developer role: {item['username']}")

        bind_other_users_as_normal_user(db, user_role_id)

        db.commit()

        print("\n角色和开发者用户初始化完成。")
        print("developer users:")

        for item in DEVELOPER_USERS:
            print(f"  {item['username']} / 123456")

    except Exception as exc:
        db.rollback()
        print("初始化失败：", exc)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()