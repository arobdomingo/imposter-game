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

logger = logging.getLogger("uvicorn.error")
app = FastAPI()

AVATAR_DIRECTORY = os.getenv(
    "AVATAR_DIRECTORY", "media/avatars"
)  # looks for AVATAR_DIRECTORY and sets path as media/avatars if it doesn't
os.makedirs(AVATAR_DIRECTORY, exist_ok=True)  # create media/avatars path if required


@app.put("/users/{id}/avatar", status_code=201)
async def upload_avatar(
    id: int, file: UploadFile = File(...), user_repo=Depends(get_user_repository)
):
    """Upload a profile picture for a user"""
    user = await user_repo.get_by_id(id)
    if not user:
        raise HTTPException(404, "User not found")

    raw_image = await file.read()
    image = process_and_crop_image(raw_image)

    destination = os.path.join(
        AVATAR_DIRECTORY, f"{id}_avatar.jpg"
    )
    image.save(destination, format="JPEG", quality=80, optimize=True)
    
    return {"message": "Avatar uploaded successfully"}


def process_and_crop_image(raw_image):
    # verify an image was uploaded
    if not raw_image:
        raise HTTPException(400, "Empty upload")

    try:
        image = Image.open(
            BytesIO(raw_image)
        )  # convert raw data to file like object and lazy load
        image.load()  # read and decompress pixel data
    except UnidentifiedImageError:
        raise HTTPException(400, "Invalid Image")

    standard_size = 512

    w, h = image.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    # Crop to a centered square with the length of the image's smallest side
    image = image.crop((left, top, left + side, top + side))

    # Resize image to fixed 512x512 dimensions to save disk space
    image = image.resize((standard_size, standard_size))

    if image.mode == "RGBA" or image.mode == "LA":  # if image is transparent
        background = Image.new(
            "RGB", image.size, (255, 255, 255)
        )  # create a white background (a canvas)
        background.paste(
            image, mask=image.split()[-1]
        )  # paste the non-transparent pixels of the image onto background
        image = background

        # final image has a white background (non-transparent)

    elif image.mode != "RGB":  # pixels not stored as RGB
        image = image.convert("RGB")

    return image


@app.get("/users/{id}/avatar")
async def get_avatar(id: int, user_repo=Depends(get_user_repository)):
    """Get a user's profile picture"""
    user = await user_repo.get_by_id(id)
    if not user:
        raise HTTPException(404, "User not found")

    path = os.path.join(AVATAR_DIRECTORY, f"{id}_avatar.jpg")
    if not os.path.isfile(path):
        raise HTTPException(404, "Avatar not found")

    return FileResponse(path, media_type="image/jpeg")


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

