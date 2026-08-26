from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.config import settings
from loguru import logger


async def create_admin_user():
    """Create the default admin user on first boot if not exists."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == settings.admin_username)
        )
        if result.scalar_one_or_none():
            return
        admin = User(
            username=settings.admin_username,
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"Admin user '{settings.admin_username}' created.")
