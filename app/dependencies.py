"""
app/dependencies.py

Reusable FastAPI dependencies. `get_current_user` is what every protected
route uses to enforce JWT auth — it's the single choke point for
"is this request authenticated?".
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app import storage
from app.security import decode_token_of_type

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
