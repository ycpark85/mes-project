# app/core/auth.py

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from typing import Any

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.db.session import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260000

TOKEN_ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    if password is None or len(password) < 6:
        raise ValueError("password must be at least 6 characters")

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PASSWORD_HASH_ITERATIONS,
    )

    return (
        f"{PASSWORD_HASH_ALGORITHM}"
        f"${PASSWORD_HASH_ITERATIONS}"
        f"${salt}"
        f"${digest.hex()}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected_hash = password_hash.split("$")
        iterations = int(iterations_text)

        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            iterations,
        )

        return hmac.compare_digest(digest.hex(), expected_hash)
    except Exception:
        return False


def create_access_token(user: User) -> str:
    now = utc_now()
    expires_at = now + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)

    header = {
        "alg": TOKEN_ALGORITHM,
        "typ": "JWT",
    }

    payload = {
        "sub": str(user.user_id),
        "login_id": user.login_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    encoded_header = _base64url_encode_json(header)
    encoded_payload = _base64url_encode_json(payload)

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = _sign(signing_input)

    return f"{encoded_header}.{encoded_payload}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("invalid token format")

        encoded_header, encoded_payload, encoded_signature = parts

        header = _base64url_decode_json(encoded_header)
        if header.get("alg") != TOKEN_ALGORITHM:
            raise ValueError("invalid token algorithm")

        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_signature = _sign(signing_input)

        if not hmac.compare_digest(expected_signature, encoded_signature):
            raise ValueError("invalid token signature")

        payload = _base64url_decode_json(encoded_payload)

        exp = payload.get("exp")
        if exp is None:
            raise ValueError("token exp missing")

        now = int(utc_now().timestamp())
        if now >= int(exp):
            raise ValueError("token expired")

        return payload
    except Exception:
        raise _credentials_exception()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)

    user_id_text = payload.get("sub")
    if not user_id_text:
        raise _credentials_exception()

    try:
        user_id = int(user_id_text)
    except ValueError:
        raise _credentials_exception()

    user = (
        db.query(User)
        .filter(
            User.user_id == user_id,
            User.is_active == True,
        )
        .first()
    )

    if user is None:
        raise _credentials_exception()

    return user


def get_user_roles(db: Session, user_id: int) -> list[Role]:
    return (
        db.query(Role)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .filter(
            UserRole.user_id == user_id,
            Role.is_active == True,
        )
        .order_by(Role.role_code.asc())
        .all()
    )


def get_user_permission_codes(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(Permission.permission_code)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .join(Role, Role.role_id == UserRole.role_id)
        .filter(
            UserRole.user_id == user_id,
            Role.is_active == True,
            Permission.is_active == True,
        )
        .distinct()
        .order_by(Permission.permission_code.asc())
        .all()
    )

    return [row[0] for row in rows]


def _base64url_encode_json(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _base64url_encode(raw)


def _base64url_decode_json(value: str) -> dict[str, Any]:
    raw = _base64url_decode(value)
    decoded = json.loads(raw.decode("utf-8"))

    if not isinstance(decoded, dict):
        raise ValueError("invalid json payload")

    return decoded


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(signing_input: bytes) -> str:
    signature = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    return _base64url_encode(signature)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 올바르지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_permission(permission_code: str):
    normalized_permission_code = permission_code.strip().upper()

    if not normalized_permission_code:
        raise ValueError("permission_code is required")

    def _require_permission(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        permission_codes = set(get_user_permission_codes(db, current_user.user_id))

        if normalized_permission_code not in permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="권한이 없습니다.",
            )

        return current_user

    return _require_permission

def require_any_permission(*permission_codes: str):
    normalized_permission_codes = {
        permission_code.strip().upper()
        for permission_code in permission_codes
        if permission_code and permission_code.strip()
    }

    if not normalized_permission_codes:
        raise ValueError("permission_codes is required")

    def _require_any_permission(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_permission_codes = set(get_user_permission_codes(db, current_user.user_id))

        if normalized_permission_codes.isdisjoint(user_permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="권한이 없습니다.",
            )

        return current_user

    return _require_any_permission

def require_method_any_permission(
    read_permission_codes: list[str] | tuple[str, ...],
    write_permission_codes: list[str] | tuple[str, ...],
):
    normalized_read_permission_codes = {
        permission_code.strip().upper()
        for permission_code in read_permission_codes
        if permission_code and permission_code.strip()
    }

    normalized_write_permission_codes = {
        permission_code.strip().upper()
        for permission_code in write_permission_codes
        if permission_code and permission_code.strip()
    }

    if not normalized_read_permission_codes:
        raise ValueError("read_permission_codes is required")

    if not normalized_write_permission_codes:
        raise ValueError("write_permission_codes is required")

    def _require_method_any_permission(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        method = request.method.upper()

        if method in {"GET", "HEAD", "OPTIONS"}:
            required_permission_codes = normalized_read_permission_codes
        else:
            required_permission_codes = normalized_write_permission_codes

        user_permission_codes = set(get_user_permission_codes(db, current_user.user_id))

        if required_permission_codes.isdisjoint(user_permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="권한이 없습니다.",
            )

        return current_user

    return _require_method_any_permission
