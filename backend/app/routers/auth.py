import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_session, get_current_user
from app.core.config import get_settings
from app.infrastructure.database.session import get_db
from app.models.session import UserSession
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    TokenResponse,
    UserRegistrationRequest,
    UserResponse,
)
from app.services.auth_service import (
    DuplicateEmailError,
    UnverifiedEmailError,
    authenticate_user,
    create_authenticated_session,
    create_password_reset,
    register_user,
    reset_password,
    revoke_session,
    verify_email,
)
from app.services.email_service import send_password_reset_email, send_verification_email
from app.services.google_auth_service import (
    GoogleAuthError,
    GoogleAuthNotConfigured,
    authenticate_google_callback,
    google_authorization_url,
    validate_google_state,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/google/start")
def google_start() -> RedirectResponse:
    try:
        return RedirectResponse(
            google_authorization_url(), status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except GoogleAuthNotConfigured:
        frontend_url = get_settings().frontend_url.rstrip("/")
        return RedirectResponse(
            f"{frontend_url}/#access&auth_error=Google%20sign-in%20is%20not%20configured"
        )


@router.get("/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings_url = get_settings().frontend_url.rstrip("/")
    if error or code is None or state is None or not validate_google_state(state):
        return RedirectResponse(
            f"{settings_url}/#access&auth_error=Google%20sign-in%20was%20cancelled%20or%20invalid"
        )
    try:
        token = authenticate_google_callback(db, code)
    except (GoogleAuthError, GoogleAuthNotConfigured):
        return RedirectResponse(
            f"{settings_url}/#access&auth_error=Google%20sign-in%20could%20not%20be%20completed"
        )
    return RedirectResponse(f"{settings_url}/#oauth_token={urllib.parse.quote(token)}")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegistrationRequest, db: Session = Depends(get_db)) -> User:
    try:
        user, verification_token = register_user(
            db, str(payload.email), payload.name, payload.password
        )
        send_verification_email(user.email, user.name, verification_token)
        return user
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Registration could not be completed"
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = authenticate_user(db, str(payload.email), payload.password)
    except UnverifiedEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before signing in",
        ) from exc
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return TokenResponse(access_token=create_authenticated_session(db, user))


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> Response:
    reset = create_password_reset(db, str(payload.email))
    if reset is not None:
        user, token = reset
        send_password_reset_email(user.email, user.name, token)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password_endpoint(
    payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)
) -> Response:
    if not reset_password(db, payload.token, payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/verify-email")
def verify_email_address(
    token: str = Query(min_length=32), db: Session = Depends(get_db)
) -> RedirectResponse:
    frontend_url = get_settings().frontend_url.rstrip("/")
    if verify_email(db, token) is None:
        return RedirectResponse(
            f"{frontend_url}/#access&auth_error=Email%20verification%20link%20is%20invalid%20or%20expired"
        )
    return RedirectResponse(f"{frontend_url}/#access&auth_message=Email%20verified%20successfully")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session: UserSession = Depends(get_current_session), db: Session = Depends(get_db)
) -> Response:
    revoke_session(db, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
