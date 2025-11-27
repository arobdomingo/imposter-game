import os
import logging
import math
from io import BytesIO
from datetime import datetime, timedelta, timezone
from typing import Optional
import binascii
from fastapi import (
    UploadFile,
    File,
    HTTPException,
    Body,
    FastAPI,
    Depends,
    Response,
    Query,
    Header,
    status,
)
from fastapi.responses import FileResponse, RedirectResponse
from time import time
from PIL import Image, UnidentifiedImageError
from jose import jwt, JWTError

from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware

from urllib.parse import urlencode
import httpx

from admin.main import ui
from .models.user import (
    UserRepository,
    User,
    UserSchema,
    UserCreateSchema,
    UserUpdateSchema,
    UserResponseSchema,
    PaginatedUsersResponse,
    get_user_repository,
    verify_password
)
from .models.friendship_routes import router as friendship_router
from event_service.models.event_routes import router as event_router
from analytics.routes.analytics_routes import router as analytics_router
from .models.friendship import FriendshipRepository, get_friendship_repository
from game_service.routes import lobby_router
from game_service.websocket import lobby_ws_router, game_ws_router

logger = logging.getLogger("uvicorn.error")

# --- Discord OAuth config ---
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_ME_URL = "https://discord.com/api/users/@me"

app = FastAPI()

rate_limits = {}  # { key: (count, window_start) }


SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if os.environ.get("TESTING") == "1":
            return await call_next(request)
        user_repo = get_user_repository()

        # Extract JWT if available
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user = await verify_jwt(token, user_repo)
            if user:
                key = f"user:{user.id}"
                limit = 2 * user.tier
            else:
                key = f"ip:{request.client.host}"
                limit = 1
        else:
            key = f"ip:{request.client.host}"
            limit = 1

        now = time()
        window = 10
        count, start = rate_limits.get(key, (0, now))

        if now - start > window:
            rate_limits[key] = (1, now)
        else:
            if count >= limit:
                return Response(status_code=429)
            rate_limits[key] = (count + 1, start)

        response = await call_next(request)
        return response


app.add_middleware(RateLimiterMiddleware)


AVATAR_DIRECTORY = os.getenv(
    "AVATAR_DIRECTORY", "media/avatars"
)  # looks for AVATAR_DIRECTORY and sets path as media/avatars if it doesn't
os.makedirs(AVATAR_DIRECTORY, exist_ok=True)  # create media/avatars path if required


async def get_current_user(
    authorization: Optional[str] = Header(None),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Verify HTTP Basic Auth and return authenticated user"""
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Decode Basic Auth
    import base64

    try:
        credentials = base64.b64decode(authorization[6:]).decode("utf-8")
        username, password = credentials.split(":", 1)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    # Authenticate user
    user = await user_repo.authenticate(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return user


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


# V2 API Endpoints


@app.get("/v2/users/", response_model=PaginatedUsersResponse)
async def list_users_v2(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of users per page"),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Get paginated list of users (V2)"""
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


@app.get("/v2/users/{user_name}")
async def get_user_by_name_v2(
    user_name: str, user_repo: UserRepository = Depends(get_user_repository)
):
    """Get user by name (V2)"""
    user = await user_repo.get_by_name(user_name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": UserSchema.from_db_model(user)}


@app.get("/v2/users/{user_id}")
async def get_user_by_id_v2(
    user_id: int, user_repo: UserRepository = Depends(get_user_repository)
):
    """Get user by id (V2)"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": UserSchema.from_db_model(user)}


@app.post("/v2/users/", status_code=201)
async def create_user_v2(
    user: UserCreateSchema,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Create a new user (V2)"""
    try:
        new_user = await user_repo.create(user.name, user.email, user.password)
        return {"user": UserSchema.from_db_model(new_user)}
    except IntegrityError:
        response.status_code = 409
        return {"detail": "Item already exists"}


@app.patch("/v2/users/{user_id}")
async def update_user_v2(
    user_id: int,
    update_data: UserUpdateSchema,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Update user (authenticated, V2)"""
    # Verify user is updating their own account
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own account",
        )

    try:
        updated_user = await user_repo.update(
            user_id=user_id,
            name=update_data.name,
            email=update_data.email,
            password=update_data.password,
            new_password=update_data.new_password,
        )

        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")

        return {"user": UserSchema.from_db_model(updated_user)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Name or email already exists")


@app.delete("/v2/users/{user_id}", status_code=204)
async def delete_user_v2(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    fr_repo: FriendshipRepository = Depends(get_friendship_repository),
):
    """Delete user (authenticated, V2)"""
    # Verify user is deleting their own account
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own account",
        )

    # cascade delete friendships and requests
    await fr_repo.delete_all_for_user(user_id)
    result = await user_repo.delete(user_id)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return Response(status_code=204)


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


@app.post("/v2/authentications/")
async def create_auth_token(
    payload: dict = Body(...),
    user_repo: UserRepository = Depends(get_user_repository),
):
    name = payload.get("name")
    password = payload.get("password")
    expiry_str = payload.get("expiry")

    user = await user_repo.get_by_name(name)
    if not user or not verify_password(password, user.password):
        raise HTTPException(401, "Invalid credentials")

    try:
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        # Assume UTC timezone if not specified
        expiry = expiry.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, "Invalid datetime format (YYYY-MM-DD HH:MM:SS)")

    # Enforce max duration 1 hour
    max_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    if expiry > max_expiry:
        expiry = max_expiry

    # Convert datetime to Unix timestamp for JWT exp claim
    expiry_timestamp = int(expiry.timestamp())
    payload = {"sub": str(user.id), "exp": expiry_timestamp}

    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

    # Invalidate previous token and save new one
    await user_repo.update_jwt(user.id, token)

    return {"jwt": token}

@app.delete("/v2/authentications/")
async def delete_auth_token(
    payload: dict = Body(...),
    user_repo: UserRepository = Depends(get_user_repository),
):
    token = payload.get("jwt")
    try:
        data = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
    except JWTError:
        raise HTTPException(401, "Invalid or expired JWT")

    user = await user_repo.get_by_id(int(data["sub"]))
    if not user or user.current_jwt != token:
        raise HTTPException(401, "Invalid token")

    await user_repo.update_jwt(user.id, None)
    return {"message": "JWT invalidated"}


async def verify_jwt(token: str, user_repo: UserRepository):
    try:
        data = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
    except JWTError:
        return None

    user = await user_repo.get_by_id(int(data["sub"]))
    if not user or user.current_jwt != token:
        return None
    return user


# Include friendship routes
app.include_router(friendship_router)

# Include event routes
app.include_router(event_router)

# Include analytics routes
app.include_router(analytics_router)

# Include game service routes
app.include_router(lobby_router)

# Include WebSocket routes
app.include_router(lobby_ws_router)
app.include_router(game_ws_router)

# ================== V2 Friend Requests ==================


@app.get("/v2/users/{user_id}/friend-requests/")
async def get_friend_requests_v2(
    user_id: int,
    q: str = Query("incoming", pattern="^(incoming|outgoing)$"),
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if q == "incoming":
        rows = await repo.get_incoming_requests(user_id)
    else:
        rows = await repo.get_outgoing_requests(user_id)
    return {
        "requests": [
            {"from": r.requester, "to": r.receiver, "status": r.status} for r in rows
        ]
    }


@app.post("/v2/users/{user_id}/friend-requests/", status_code=201)
async def create_friend_request_v2(
    user_id: int,
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only act as yourself")
    other_id = payload.get("to")
    if not isinstance(other_id, int):
        raise HTTPException(400, "Missing 'to' user id")
    if other_id == user_id:
        raise HTTPException(400, "Cannot friend-request yourself")
    if not await user_repo.get_by_id(other_id):
        raise HTTPException(404, "Target user not found")
    await repo.send_request(user_id, other_id)
    return {"message": "Friend request sent"}


@app.patch("/v2/users/{user_id}/friend-requests/{other_id}")
async def respond_friend_request_v2(
    user_id: int,
    other_id: int,
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only act as yourself")
    if not await user_repo.get_by_id(other_id):
        raise HTTPException(404, "Other user not found")
    action = payload.get("action", "accept")
    if action == "accept":
        await repo.accept_request(other_id, user_id)
        return {"message": "Friend request accepted"}
    elif action == "reject":
        await repo.reject_request(other_id, user_id)
        return {"message": "Friend request rejected"}
    else:
        raise HTTPException(400, "Invalid action. Use 'accept' or 'reject'")


@app.delete("/v2/users/{user_id}/friend-requests/{other_id}", status_code=204)
async def cancel_friend_request_v2(
    user_id: int,
    other_id: int,
    current_user: User = Depends(get_current_user),
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only act as yourself")
    if not await user_repo.get_by_id(other_id):
        raise HTTPException(404, "Other user not found")
    await repo.cancel_request(user_id, other_id)
    return Response(status_code=204)


# ================== V2 Friends ==================


def _friend_ids_for(user_id: int, friendships: list) -> list[int]:
    ids = []
    for f in friendships:
        ids.append(f.requester if f.receiver == user_id else f.receiver)
    return ids


@app.get("/v2/users/{user_id}/friends/")
async def list_friends_v2(
    user_id: int,
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if not await user_repo.get_by_id(user_id):
        raise HTTPException(404, "User not found")
    friendships = await repo.list_friends(user_id)
    friend_ids = _friend_ids_for(user_id, friendships)
    users = [await user_repo.get_by_id(fid) for fid in friend_ids]
    return {"friends": [UserSchema.from_db_model(u).__dict__ for u in users if u]}


@app.get("/v2/users/{user_id}/friends/{friend_name}")
async def get_friend_by_name_v2(
    user_id: int,
    friend_name: str,
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if not await user_repo.get_by_id(user_id):
        raise HTTPException(404, "User not found")
    target = await user_repo.get_by_name(friend_name)
    if not target:
        raise HTTPException(404, "Friend not found")
    friendships = await repo.list_friends(user_id)
    if target.id not in _friend_ids_for(user_id, friendships):
        raise HTTPException(404, "Friend not found")
    return {"friend": UserSchema.from_db_model(target)}


@app.get("/v2/users/{user_id}/friends/{friend_id}")
async def get_friend_by_id_v2(
    user_id: int,
    friend_id: int,
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if not await user_repo.get_by_id(user_id):
        raise HTTPException(404, "User not found")
    target = await user_repo.get_by_id(friend_id)
    if not target:
        raise HTTPException(404, "Friend not found")
    friendships = await repo.list_friends(user_id)
    if friend_id not in _friend_ids_for(user_id, friendships):
        raise HTTPException(404, "Friend not found")
    return {"friend": UserSchema.from_db_model(target)}


@app.delete("/v2/users/{user_id}/friends/{friend_name}", status_code=204)
async def delete_friend_by_name_v2(
    user_id: int,
    friend_name: str,
    current_user: User = Depends(get_current_user),
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only act as yourself")
    friend = await user_repo.get_by_name(friend_name)
    if not friend:
        raise HTTPException(404, "Friend not found")
    await repo.delete_friendship(user_id, friend.id)
    return Response(status_code=204)


@app.delete("/v2/users/{user_id}/friends/{friend_id}", status_code=204)
async def delete_friend_by_id_v2(
    user_id: int,
    friend_id: int,
    current_user: User = Depends(get_current_user),
    repo: FriendshipRepository = Depends(get_friendship_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only act as yourself")
    if not await user_repo.get_by_id(friend_id):
        raise HTTPException(404, "Friend not found")
    await repo.delete_friendship(user_id, friend_id)
    return Response(status_code=204)


ui.run_with(app, mount_path="/admin", favicon="👤", title="User Admin")

# Load or generate RSA keys (for RS256)
PRIVATE_KEY_PATH = "private.pem"
PUBLIC_KEY_PATH = "public.pem"

if not os.path.exists(PRIVATE_KEY_PATH):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(
            key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

@app.get("/v2/authentications/discord/login")
async def discord_login():
    """
    Start Discord OAuth login by redirecting the user to Discord's authorization page.
    """

    if not DISCORD_CLIENT_ID or not DISCORD_REDIRECT_URI:
        # Misconfigured backend – missing env vars
        raise HTTPException(status_code=500, detail="Discord OAuth is not configured on the server.")
    
    params = {"client_id": DISCORD_CLIENT_ID, "response_type": "code", "redirect_uri": DISCORD_REDIRECT_URI, "scope": "identify email"}
    # optional: "state": <csrf_token>

    url = f"{DISCORD_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    return RedirectResponse(url)

@app.get("/v2/authentications/discord/callback")
async def discord_callback(code: str, user_repo: UserRepository = Depends(get_user_repository)):

    '''OAuth callback for Discord login. Discord redirects the user here with a `code` query parameter.
        1) Exchange code for access token, 2) use token to fetch profile, 3) find/create local user, 4) issue a JWT'''
    
    if not (DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET and DISCORD_REDIRECT_URI):
        raise HTTPException(status_code=500, detail="Discord OAuth is not configured on the server.")

    token_data = {"client_id": DISCORD_CLIENT_ID, "client_secret": DISCORD_CLIENT_SECRET, "grant_type": "authorization_code", "code": code, "redirect_uri": DISCORD_REDIRECT_URI}

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(DISCORD_OAUTH_TOKEN_URL, data=token_data)

    # Something went wrong on the token exchange
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to obtain access token from Discord.")
    
    token_json = token_resp.json()
    access_token = token_json.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Discord did not return an access token.")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        me_resp = await client.get(DISCORD_API_ME_URL, headers=headers)    

    if me_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user profile from Discord.")
    
    me = me_resp.json()
    discord_id = me["id"]
    discord_username = me["username"]
    discord_email = me.get("email")

    existing_user = await user_repo.get_by_discord_id(discord_id)
    if existing_user is None:
        user = await user_repo.create_from_discord(discord_id=discord_id, username=discord_username, email=discord_email)
    else:
        user = existing_user

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=1)
    expiry_timestamp = int(expiry.timestamp())

    payload = {"sub": str(user.id), "exp": expiry_timestamp}
    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

    await user_repo.update_jwt(user.id, token) # Store current JWT in the DB

    return {"jwt": token, "user": UserSchema.from_db_model(user)}


with open(PRIVATE_KEY_PATH, "rb") as f:
    PRIVATE_KEY = f.read()
with open(PUBLIC_KEY_PATH, "rb") as f:
    PUBLIC_KEY = f.read()

app.include_router(analytics_router)
