# backend/app/core/init_db.py
import asyncio
import logging
from sqlalchemy import select
from app.core.database import async_session, engine, Base
from app.core.security import hash_password, generate_random_password
# Import all models to register them with Base
from app.models import User, LLMConfig

logger = logging.getLogger(__name__)


async def init_db():
    """初始化数据库，创建表和默认用户"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 检查是否已有用户
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            password = generate_random_password()
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                # password_hash=hash_password(password),
                email="admin@example.com",
                approval_status="approved",
                is_admin=True
            )
            session.add(admin)
            await session.commit()
            logger.warning(
                "Created default admin user. Username: admin, Password: %s  "
                "-- CHANGE THIS PASSWORD IMMEDIATELY!",
                password,
            )
        else:
            logger.info("Default admin user already exists")


if __name__ == "__main__":
    asyncio.run(init_db())
