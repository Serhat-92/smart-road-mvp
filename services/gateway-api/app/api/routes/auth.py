"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# Hardcoded MVP User
MVP_USER = {
    "username": "admin",
    "password": "admin123",  # For MVP. Do not use in production.
}


@router.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Login to get an access token."""
    if form_data.username != MVP_USER["username"] or form_data.password != MVP_USER["password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def read_users_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """Get current user information (validates token)."""
    return current_user
