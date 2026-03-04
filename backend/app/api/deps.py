# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_access_token
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    username = payload.get("sub")

    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    if user.approval_status != "approved":
        raise HTTPException(status_code=403, detail="User account is not approved")

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """验证用户是否为admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def handle_dsl_exception(e: Exception, operation: str) -> HTTPException:
    """Convert DSL parsing/validation exceptions to appropriate HTTP errors.

    Args:
        e: The exception raised during DSL processing
        operation: Description of the operation (e.g., "upload rule", "update action")

    Returns:
        HTTPException with appropriate status code
    """
    if isinstance(e, ValueError):
        raise HTTPException(status_code=400, detail=str(e))
    error_type = type(e).__name__
    if "Unexpected" in error_type or "Visit" in error_type:
        raise HTTPException(status_code=400, detail=f"Invalid DSL: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Failed to {operation}: {str(e)}")
