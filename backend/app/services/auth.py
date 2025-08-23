"""
Authentication service for user management and JWT tokens.
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User as UserModel
from app.schemas.user import User, UserCreate, UserInDB
from app.schemas.auth import UserRegister

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


class AuthService:
    """Authentication service class."""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email address."""
        if not self.db:
            return None
        
        user = self.db.query(UserModel).filter(UserModel.email == email).first()
        if user:
            return UserInDB.from_orm(user)
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID."""
        if not self.db:
            return None
            
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            return UserInDB.from_orm(user)
        return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with email and password."""
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        if self.db:
            db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
            if db_user:
                db_user.last_login = datetime.utcnow()
                self.db.commit()
        
        return user
    
    def create_user(self, user_data: UserRegister) -> User:
        """Create a new user."""
        if not self.db:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection not available"
            )
        
        # Hash password
        hashed_password = self.get_password_hash(user_data.password)
        
        # Create user model
        db_user = UserModel(
            email=user_data.email,
            full_name=user_data.full_name,
            company=user_data.company,
            hashed_password=hashed_password
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return User.from_orm(db_user)
    
    @staticmethod
    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ) -> User:
        """Get current authenticated user."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        auth_service = AuthService(db)
        user = auth_service.get_user_by_email(email)
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return User.from_orm(user)
    
    @staticmethod
    async def get_current_admin_user(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Get current user if they have admin privileges."""
        if current_user.role not in ["admin", "enterprise"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
