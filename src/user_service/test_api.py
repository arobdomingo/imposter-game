import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

from .models.user import Base, UserRepository, get_user_repository

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
def client(repo):
    app.dependency_overrides[get_user_repository] = lambda: repo
    with TestClient(app) as c:
        yield c


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


def test_upload_and_get_avatar(client, created_user):
    """Test uploading and retrieving a user avatar"""
    from PIL import Image
    from io import BytesIO

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
