from fastapi import FastAPI, Depends, Response, Query
from sqlalchemy.exc import IntegrityError
import logging
import math

from admin.main import ui
from .models.user import (
    UserRepository,
    UserSchema,
    PaginatedUsersResponse,
    get_user_repository,
)


logger = logging.getLogger("uvicorn.error")
app = FastAPI()


@app.post("/users/", status_code=201)
async def create_user(
    user: UserSchema,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        new_user = await user_repo.create(user.name)
        return {"user": UserSchema.from_db_model(new_user)}
    except IntegrityError:
        response.status_code = 409
        return {"detail": "Item already exists"}


@app.get("/users/", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of users per page"),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Get paginated list of users"""
    user_models, total_count = await user_repo.get_paginated(page, page_size)

    users = [UserSchema.from_db_model(model) for model in user_models]
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    return PaginatedUsersResponse(
        users=users,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/users/{name}")
async def get_user(name: str, user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_name(name)
    return {"user": user}


ui.run_with(app, mount_path="/admin", favicon="👤", title="User Admin")
