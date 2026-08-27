from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_session, get_current_user
from app.infrastructure.database.session import get_db
from app.models.session import UserSession
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserRegistrationRequest, UserResponse
from app.services.auth_service import (
    DuplicateEmailError,
    authenticate_user,
    create_authenticated_session,
    register_user,
    revoke_session,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegistrationRequest, db: Session = Depends(get_db)) -> User:
    try:
        return register_user(db, str(payload.email), payload.name, payload.password)
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Registration could not be completed"
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return TokenResponse(access_token=create_authenticated_session(db, user))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: UserSession = Depends(get_current_session), db: Session = Depends(get_db)
) -> Response:
    revoke_session(db, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
