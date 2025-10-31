from pydantic import BaseModel
from sqlalchemy import select, delete, String, func, Integer
from sqlalchemy.orm import declarative_base, Session, mapped_column, Mapped
from sqlalchemy.exc import IntegrityError
from fastapi import Depends
from typing import Tuple
import bcrypt


from shared.database import get_db


Base = declarative_base()


def hash_password(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


class User(Base):
    """
    User model used by SQLAlchemy to interact with the database. When you look up a user in the database, you will get an instance of this class back. This is the database's view of users.
    """

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)


class UserRepository:
    """
    Controls manipulation of the users table.
    """

    def __init__(self, session: Session):
        self.session = session

    async def create(self, name: str, email: str, password: str) -> User:
        try:
            new_user = User(name=name, email=email, password=hash_password(password))
            self.session.add(new_user)
            self.session.commit()
            self.session.refresh(new_user)  # This retrieves the auto-generated id
            return new_user
        except IntegrityError:
            self.session.rollback()
            raise

    async def delete(self, id: int) -> None:
        """Delete user by id"""
        stmt = delete(User).where(User.id == id)
        result = self.session.execute(stmt)
        self.session.commit()
        return result

    async def update(
        self,
        user_id: int,
        name: str = None,
        email: str = None,
        password: str = None,
        new_password: str = None,
    ):
        """Update user fields"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # If changing password, verify current password first
        if new_password:
            if not password or not verify_password(password, user.password):
                raise ValueError("Invalid current password")
            user.password = hash_password(new_password)

        # Update other fields if provided
        if name:
            user.name = name
        if email:
            user.email = email

        self.session.commit()
        self.session.refresh(user)
        return user

    async def authenticate(self, name: str, password: str):
        """Authenticate a user by name and password"""
        user = await self.get_by_name(name)
        if not user or not verify_password(password, user.password):
            return None
        return user

    async def get_all(self) -> list[User]:
        """Get all users"""
        users = self.session.scalars(select(User)).all()
        return users

    async def get_paginated(
        self, page: int = 1, page_size: int = 50
    ) -> Tuple[list[User], int]:
        """Get paginated users with total count"""
        # Calculate offset
        offset = (page - 1) * page_size

        # Get total count
        total_count = self.session.scalar(select(func.count(User.name)))

        # Get paginated users
        users = self.session.scalars(select(User).offset(offset).limit(page_size)).all()

        return list(users), total_count

    async def get_by_name(self, name: str) -> User:
        """Get user by name"""
        user = self.session.scalar(select(User).where(User.name == name))
        return user

    async def get_by_id(self, id: int) -> User:
        """Get user by id"""
        user = self.session.scalar(select(User).where(User.id == id))
        return user


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


class UserSchema(BaseModel):
    """
    The application's view of users. This is how the API represents users (as opposed to how the database represents them).
    """

    id: int
    name: str
    email: str

    @classmethod
    def from_db_model(cls, user: User) -> "UserSchema":
        """Create a UserSchema from a User (without password for security)"""
        return cls(id=user.id, name=user.name, email=user.email)


class UserResponseSchema(BaseModel):
    """Schema for user responses (without password for security)"""

    id: int
    name: str
    email: str

    @classmethod
    def from_db_model(cls, user: User) -> "UserResponseSchema":
        """Create a UserResponseSchema from a User"""
        return cls(id=user.id, name=user.name, email=user.email)


class UserCreateSchema(BaseModel):
    """Schema for creating a user (without id)"""

    name: str
    email: str
    password: str


class UserUpdateSchema(BaseModel):
    """Schema for updating a user"""

    name: str = None
    email: str = None
    password: str = None
    new_password: str = None


class PaginatedUsersResponse(BaseModel):
    """
    Response model for paginated users
    """

    users: list[UserSchema]
    total: int
    page: int
    page_size: int
    total_pages: int
