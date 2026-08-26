from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User, UserRole
from app.core.security import get_current_user, require_admin, hash_password

router = APIRouter()


class UpdateUserRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    email: str | None = None


@router.get("/", dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active,
            "broker": u.broker,
            "last_login": u.last_login,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.patch("/{user_id}", dependencies=[Depends(require_admin)])
async def update_user(user_id: int, payload: UpdateUserRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.email is not None:
        user.email = payload.email

    await db.commit()
    return {"message": "User updated"}


@router.put("/{user_id}/password", dependencies=[Depends(require_admin)])
async def reset_password(user_id: int, new_password: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(new_password)
    await db.commit()
    return {"message": "Password reset"}
