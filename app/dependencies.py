"""
app/dependencies.py

Reusable FastAPI dependencies. `get_current_user` is what every protected
route uses to enforce JWT auth — it's the single choke point for
"is this request authenticated?".

Admin access has three tiers:
  - get_current_user      any logged-in user
  - get_current_admin     any admin (is_admin=True), regardless of which
                           specific privileges they hold
  - require_permission(p) an admin who either IS the principal admin
                           (who implicitly holds every privilege and can
                           never be locked out) OR has `p` explicitly in
                           their admin_permissions list
  - get_current_principal_admin
                           only the single principal admin — used for
                           promoting/revoking other admins and editing
                           their permissions, so that power can never be
                           granted or taken away by a regular admin.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app import storage
from app.security import decode_token_of_type

# The full set of grantable admin privileges. Kept as a single source of
# truth so the management endpoints can validate incoming permission lists
# against it, and the frontend's "manage admins" tab can stay in sync with
# whatever's actually enforceable server-side.
ADMIN_PERMISSIONS = {"payouts", "places", "feedback", "notifications"}

# tokenUrl is only used to populate Swagger UI's "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    try:
        payload = decode_token_of_type(token, expected_type="access")
    except JWTError:
        raise credentials_exception

    username = payload.get("sub")
    if not username:
        raise credentials_exception

    users = storage.read_all(storage.USERS_FILE)
    user = next((u for u in users if u["username"] == username), None)
    if user is None:
        raise credentials_exception

    return user


def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_current_principal_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_principal_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the principal admin can do this",
        )
    return user


def require_permission(permission: str):
    """
    Dependency factory: `Depends(require_permission("payouts"))`.

    The principal admin always passes, regardless of their stored
    admin_permissions list — that's what makes them "principal" rather
    than just another admin, and it means the principal can never lock
    themselves out by mis-editing their own permission list.
    """
    if permission not in ADMIN_PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission!r}")

    def _check(user: dict = Depends(get_current_admin)) -> dict:
        if user.get("is_principal_admin", False):
            return user
        if permission not in (user.get("admin_permissions") or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required admin permission: {permission}",
            )
        return user

    return _check
