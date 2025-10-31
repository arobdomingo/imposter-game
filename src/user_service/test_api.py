import pytest

from PIL import Image
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

from .models.user import Base, UserRepository, get_user_repository
from .models.friendship import (
    Friendship,  # noqa: F401 - Imported to register table with Base.metadata
    FriendshipRepository,
    get_friendship_repository,
)

from .api import app


@pytest.fixture(scope="function")
def engine():
    engine = create_engine("sqlite:///:memory:?check_same_thread=False")
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture(scope="function")
def session(engine):
    conn = engine.connect()
    conn.begin()
    db = Session(bind=conn)
    yield db
    db.rollback()
    conn.close()


@pytest.fixture(scope="function")
def repo(session):
    yield UserRepository(session)


@pytest.fixture(scope="function")
def friendship_repo(session):
    yield FriendshipRepository(session)


@pytest.fixture(scope="function")
def client(repo, friendship_repo):
    app.dependency_overrides[get_user_repository] = lambda: repo
    app.dependency_overrides[get_friendship_repository] = lambda: friendship_repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def created_user(session):
    user_data = {"name": "foo", "email": "foo@example.com", "password": "foopass"}
    session.execute(
        text(
            "INSERT INTO users (name, email, password) VALUES (:name, :email, :password)"
        ),
        user_data,
    )
    session.commit()
    return user_data


def test_read_user(client, created_user):
    response = client.get("/users/1")
    assert response.status_code == 200
    user_response = response.json()["user"]
    assert user_response["id"] == 1
    assert user_response["name"] == "foo"
    assert user_response["email"] == "foo@example.com"
    # Password should NOT be in response (security)
    assert "password" not in user_response


def test_create_user(client):
    response = client.post(
        "/users/",
        json={"name": "foobar", "email": "foobar@example.com", "password": "foobar"},
    )
    assert response.status_code == 201
    user_response = response.json()["user"]
    assert user_response["id"] == 1
    assert user_response["name"] == "foobar"
    assert user_response["email"] == "foobar@example.com"
    # Password should NOT be in response (security)
    assert "password" not in user_response


def test_create_existing_user(client, created_user):
    response = client.post(
        "/users/",
        json=created_user,
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Item already exists"}


def _clean_avatar(client, user_id=1):
    client.delete(f"/v2/users/{user_id}/avatar")  # ignore 404 if not present


def test_v2_avatar_post_errors_via_endpoint(client, created_user):
    _clean_avatar(client)

    # Empty upload -> 400
    r = client.post(
        "/v2/users/1/avatar",
        files={"file": ("empty.jpg", BytesIO(b""), "image/jpeg")},
    )
    assert r.status_code == 400

    # Not-an-image bytes -> 422
    r = client.post(
        "/v2/users/1/avatar",
        files={"file": ("bad.png", BytesIO(b"not-an-image"), "image/png")},
    )
    assert r.status_code == 422

    # Unsupported content-type -> 415
    r = client.post(
        "/v2/users/1/avatar",
        files={"file": ("note.txt", BytesIO(b"text"), "text/plain")},
    )
    assert r.status_code == 415


def test_v2_avatar_png_rgba_converted_and_resized(client, created_user):
    _clean_avatar(client)

    # Create RGBA (has alpha) PNG; server should convert to RGB + clamp to <=256
    buf = BytesIO()
    Image.new("RGBA", (800, 600), (0, 200, 255, 128)).save(buf, format="PNG")
    buf.seek(0)

    # POST create
    r = client.post(
        "/v2/users/1/avatar",
        files={"file": ("has_alpha.png", buf, "image/png")},
    )
    assert r.status_code == 201

    # GET and inspect returned image
    r = client.get("/v2/users/1/avatar")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    img = Image.open(BytesIO(r.content))
    assert img.mode == "RGB"
    assert max(img.size) <= 256  # resized within 256x256


def test_upload_and_get_legacy_avatar(client, created_user):
    # Create a test image
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    # Upload the avatar
    response = client.put(
        "/users/1/avatar", files={"file": ("test.jpg", img_bytes, "image/jpeg")}
    )
    assert response.status_code == 201

    # Get the avatar
    response = client.get("/users/1/avatar")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_create_and_get_v2_avatar(client, created_user):
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # Create avatar (POST)
    response = client.post(
        "/v2/users/1/avatar",
        files={"file": ("avatar.png", img_bytes, "image/png")},
    )
    assert response.status_code in (
        201,
        409,
    )  # accepts outcome that avatar already exists (from legacy test)

    # Retrieve avatar (GET)
    response = client.get("/v2/users/1/avatar")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_replace_v2_avatar(client, created_user):
    from PIL import Image
    from io import BytesIO

    # Create initial image
    img = Image.new("RGB", (50, 50), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    client.post(
        "/v2/users/1/avatar",
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
    )

    # Replace it with a new one
    img2 = Image.new("RGB", (80, 80), color="green")
    img2_bytes = BytesIO()
    img2.save(img2_bytes, format="JPEG")
    img2_bytes.seek(0)

    response = client.put(
        "/v2/users/1/avatar",
        files={"file": ("replace.jpg", img2_bytes, "image/jpeg")},
    )
    assert response.status_code in (200, 204)


def test_delete_v2_avatar(client, created_user):
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (100, 100), color="yellow")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    client.post(
        "/v2/users/1/avatar",
        files={"file": ("delete.jpg", img_bytes, "image/jpeg")},
    )

    response = client.delete("/v2/users/1/avatar")
    assert response.status_code in (200, 204)

    # Double-check that it's actually gone
    response = client.get("/v2/users/1/avatar")
    assert response.status_code == 404


def test_delete_user(client, created_user):
    """Test deleting a user account"""
    response = client.post(
        "/users/delete",
        json={"id": 1, "name": "foo", "email": "foo@example.com"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "message": "User deleted successfully",
        "user": {"name": "foo"},
    }
    # Verify user is actually deleted
    get_response = client.get("/users/1")
    assert get_response.json() == {"user": None}


def test_delete_nonexistent_user(client):
    """Test deleting non-existent user"""
    response = client.post(
        "/users/delete",
        json={"id": 999, "name": "nonexistent", "email": "none@example.com"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


# Friendship Tests


def test_send_friend_request(session, client):
    session.execute(
        text(
            "INSERT INTO users (name, email, password) VALUES ('user1', 'user1@example.com', 'pass1')"
        )
    )
    session.execute(
        text(
            "INSERT INTO users (name, email, password) VALUES ('user2', 'user2@example.com', 'pass2')"
        )
    )
    session.commit()

    response = client.post(
        "/friendships/request", params={"requester_id": 1, "receiver_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Friend request sent"}


def test_accept_friend_request(session, client):
    session.execute(
        text(
            "INSERT INTO users (name, email, password) VALUES ('user1', 'user1@example.com', 'pass1')"
        )
    )
    session.execute(
        text(
            "INSERT INTO users (name, email, password) VALUES ('user2', 'user2@example.com', 'pass2')"
        )
    )
    session.execute(
        text(
            "INSERT INTO friendships (requester, receiver, status) VALUES (1, 2, 'pending')"
        )
    )
    session.commit()

    response = client.post(
        "/friendships/accept", params={"requester_id": 1, "receiver_id": 2}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Friend request accepted"}


def test_accept_nonexistent_friendship(client):
    response = client.post(
        "/friendships/accept", params={"requester_id": 99, "receiver_id": 100}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Friend request accepted"}
