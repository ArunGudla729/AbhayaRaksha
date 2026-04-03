from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import Worker
from .config import settings

import bcrypt as _bcrypt

# passlib 1.7.4 is incompatible with bcrypt 4.x — it tries to read
# bcrypt.__about__.__version__ which no longer exists, causing verify_password
# to silently return False on every call. Patch the version attribute so
# passlib can initialise correctly.
if not hasattr(_bcrypt, "__about__"):
    class _About:
        __version__ = "4.0.1"
    _bcrypt.__about__ = _About()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_worker(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Worker:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        worker_id_str = payload.get("sub")
        if worker_id_str is None:
            raise credentials_exception
        worker_id = int(worker_id_str)
    except JWTError:
        raise credentials_exception
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker is None:
        raise credentials_exception
    return worker

def get_current_admin(current_worker: Worker = Depends(get_current_worker)) -> Worker:
    if not current_worker.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_worker
