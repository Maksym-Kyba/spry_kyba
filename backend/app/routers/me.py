from fastapi import APIRouter

from app.auth import CurrentUser
from app.models import User
from app.schemas import UserRead

router = APIRouter(prefix="/me", tags=["auth"])


@router.get("", response_model=UserRead)
async def get_me(user: CurrentUser) -> User:
    """The signed-in user (created on their first request)."""
    return user
