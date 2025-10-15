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


@app.put("/users/{name}/avatar", status_code=201)
async def upload_avatar(
    name: str, file: UploadFile = File(...), user_repo=Depends(get_user_repository)
):  # parameters are the name (key), a required UploadFile, and database dependency
    user = await user_repo.get_by_name(name)
    if not user:
        raise HTTPException(404, "User not found")

    raw_image = await file.read()
    image = process_and_crop_image(raw_image)

    destination = os.path.join(
        AVATAR_DIRECTORY, f"{name}_avatar.jpg"
    )  # create string for file path to the  user's JPEG avatar in the avatar directory (adding a file)
    image.save(
        destination, format="JPEG", quality=80, optimize=True
    )  # save image at that path (in directory)


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
    image.crop((left, top, left + side, top + side))
    # crop to a centered square with the length of the image's smallest side

    image = image.resize(
        (standard_size, standard_size)
    )  # resize image to fixed P x P dimensions

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


@app.get("/users/{name}/avatar")
async def get_avatar(name: str, user_repo=Depends(get_user_repository)):
    user = await user_repo.get_by_name(name)
    if not user:
        raise HTTPException(404, "User not found")

    path = os.path.join(
        AVATAR_DIRECTORY, f"{name}_avatar.jpg"
    )  # create string for file path to the  user's JPEG avatar
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


ui.run_with(app, mount_path="/admin", favicon="👤", title="User Admin")
