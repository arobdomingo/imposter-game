import os
from io import BytesIO
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from PIL import Image, UnidentifiedImageError

from fastapi import FastAPI, Depends, Response, Query
from sqlalchemy.exc import IntegrityError
import logging
import math

from admin.main import ui
from .models.user import (
    UserRepository,
    UserSchema,
    UserCreateSchema,
    UserResponseSchema,
    PaginatedUsersResponse,
    get_user_repository,
)
from .models.friendship_routes import router as friendship_router
from event_service.models.event_routes import router as event_router
from analytics.routes.analytics_routes import router as analytics_router

logger = logging.getLogger("uvicorn.error")
app = FastAPI()

AVATAR_DIRECTORY = os.getenv(
    "AVATAR_DIRECTORY", "media/avatars"
)  # looks for AVATAR_DIRECTORY and sets path as media/avatars if it doesn't
os.makedirs(AVATAR_DIRECTORY, exist_ok=True)  # create media/avatars path if required

# Legacy upload avatar method:


@app.put("/users/{id}/avatar", status_code=201)
async def upload_avatar(
    id: int, file: UploadFile = File(...), user_repo=Depends(get_user_repository)
):
    """Upload a profile picture for a user"""
    user = await user_repo.get_by_id(id)
    if not user:
        raise HTTPException(404, "User not found")

    raw_image = await file.read()
    image = process_image_upload(raw_image)

    destination = os.path.join(AVATAR_DIRECTORY, f"{id}_avatar.jpg")
    image.save(destination, format="JPEG", quality=80, optimize=True)

    return {"message": "Avatar uploaded successfully"}


# get_avatar() is identical between versions:


@app.get("/users/{user_id}/avatar")
@app.get("/v2/users/{user_id}/avatar")
async def get_avatar(user_id: int, user_repo=Depends(get_user_repository)):
    """Get a user's profile picture (for legacy and v2)"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    path = os.path.join(AVATAR_DIRECTORY, f"{user_id}_avatar.jpg")
    if not os.path.isfile(path):
        raise HTTPException(404, "Avatar not found")

    return FileResponse(path, media_type="image/jpeg")


def process_image_upload(raw_image: bytes):
    if not raw_image:
        raise HTTPException(400, "Empty Upload")

    try:
        image = Image.open(
            BytesIO(raw_image)
        )  # convert raw data to file like object and lazy load
        image.load()  # read and decompress pixel data
    except UnidentifiedImageError:
        raise HTTPException(422, "Invalid Image File")

    if image.mode != "RGB":
        image = image.convert(
            "RGB"
        )  # ensure we can safe safely as jpg, pratical image form

    image.thumbnail((256, 256))  # resize (fixed aspect ratio) to fit within 256x256

    return image


# New version 2 methods concerning user avatars:


@app.post("/v2/users/{user_id}/avatar", status_code=201)
async def create_avatar(
    user_id: int, file: UploadFile = File(...), user_repo=Depends(get_user_repository)
):
    """Creates a v2 profile picture (web, png, or jpeg uploads accepted)"""

    # MUST DO: password verification to be implemented

    user = await user_repo.get_by_id(user_id)  # check the user exists
    if not user:
        raise HTTPException(404, "User not found")

    if file.content_type not in (
        "image/png",
        "image/jpeg",
        "image/webp",
    ):  # valid file type
        raise HTTPException(415, "Unsupported media type")

    # open and process the image
    raw_image = await file.read()
    image = process_image_upload(raw_image)

    destination = os.path.join(AVATAR_DIRECTORY, f"{user_id}_avatar.jpg")

    if os.path.exists(destination):
        raise HTTPException(409, "A user avatar already exist, use PUT to replace")

    # add the file to the avatar directory
    image.save(destination, format="JPEG", quality=85, optimize=True)

    return {"message": "Avatar uploaded successfully"}


@app.put("/v2/users/{user_id}/avatar", status_code=204)
async def replace_avatar(
    user_id: int, file: UploadFile = File(...), user_repo=Depends(get_user_repository)
):
    """Replaces an existing v2 profile picture (web, png, or jpeg uploads accepted)"""

    # MUST DO: password verification to be implemented

    # check the user exist
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # validate the file type
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(415, "Unsupported media type")

    # open and process the image
    raw_image = await file.read()
    image = process_image_upload(raw_image)

    # add the file to the avatar directory
    destination = os.path.join(AVATAR_DIRECTORY, f"{user_id}_avatar.jpg")
    image.save(destination, format="JPEG", quality=85, optimize=True)

    return {"message": "Avatar replaced successfully"}


@app.delete("/v2/users/{user_id}/avatar", status_code=204)
async def delete_avatar(user_id: int, user_repo=Depends(get_user_repository)):
    """Deletes an existing v2 profile picture"""

    # MUST DO: password verification to be implemented

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    destination = os.path.join(AVATAR_DIRECTORY, f"{user_id}_avatar.jpg")

    try:
        os.remove(destination)
    except FileNotFoundError:
        raise HTTPException(404, "User avatar not found")

    return {"message": "Avatar deleted successfully"}


@app.post("/users/", status_code=201)
async def create_user(
    user: UserCreateSchema,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        new_user = await user_repo.create(user.name, user.email, user.password)
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


@app.get("/users/{id}")
async def get_user(id: int, user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_id(id)
    if user:
        return {"user": UserResponseSchema.from_db_model(user)}
    return {"user": None}


@app.post("/users/delete", status_code=200)
async def delete_user(
    user: UserSchema,
    user_repo: UserRepository = Depends(get_user_repository),
):
    # Check if user exists
    existing_user = await user_repo.get_by_name(user.name)
    if not existing_user:
        raise HTTPException(404, "User not found")
    # Delete user from database
    await user_repo.delete(existing_user.id)
    return {"message": "User deleted successfully", "user": {"name": user.name}}


# Include friendship routes
app.include_router(friendship_router)

# Include event routes
app.include_router(event_router)

# Include analytics routes
app.include_router(analytics_router)

ui.run_with(app, mount_path="/admin", favicon="👤", title="User Admin")
