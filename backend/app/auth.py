from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr

from . import crud, models, schemas

# Configuration
SECRET_KEY = "YOUR_SECRET_KEY"  # In a real app, use a strong, environment-variable-sourced key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") # Adjusted tokenUrl to match router prefix

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> models.UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[EmailStr] = payload.get("sub") # Assuming email is stored in 'sub'
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_email(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.UserInDB = Depends(get_current_user)) -> models.UserInDB:
    # In a real app, you might check if the user is active, e.g., current_user.is_active
    # For now, we just return the user
    # if not current_user.is_active: # Assuming an is_active field in UserInDB or fetched User model
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# --- API Key Utilities ---
import secrets
import hashlib

def generate_api_key(length: int = 32) -> str:
    """Generates a secure random string for the API key."""
    # Generates a key like "ppk_xxxxxxxx..." (Prompt Pilot Key)
    # The actual random part will be `length` hex characters (length*2 in final string if using hex)
    # For simplicity, let's use base64 encoding which is more compact.
    # A 32-byte random string will be 44 chars in base64. Let's aim for around 40-50 char total.
    # prefix + 32 random bytes base64 encoded
    # secrets.token_urlsafe(n) generates n random bytes.
    return "ppk_" + secrets.token_urlsafe(32) # Results in "ppk_" + 43 chars = 47 total

def hash_api_key(api_key: str) -> str:
    """Hashes the API key using SHA256."""
    # This is for verification. We store the hash and compare the hash of the incoming key.
    return hashlib.sha256(api_key.encode()).hexdigest()

def get_key_prefix(api_key: str, length: int = 8) -> str:
    """Returns the first few characters of the key after the 'ppk_' part."""
    if api_key.startswith("ppk_") and len(api_key) > (4 + length) :
        return api_key[4 : 4 + length] # Return 8 chars after "ppk_"
    elif len(api_key) > length:
        return api_key[:length] # Fallback if no "ppk_" prefix
    return api_key[:length] # Fallback for very short keys (should not happen with generation)
