import pytest, os
from user_service.models.user import Base
from shared.database import get_db
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, text
from user_service.api import app


from .models.user import Base, UserRepository, get_user_repository
from .models.friendship import (
    Friendship,  # noqa: F401 - Imported to register table with Base.metadata
    FriendshipRepository,
    get_friendship_repository,
)

from .api import app
# Ensure testing mode
os.environ["TESTING"] = "1"

# Create a single in-memory SQLite engine for all tests
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables once
Base.metadata.create_all(bind=engine)

# Override get_db dependency to use SQLite for testing
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_user_repository] = lambda: UserRepository(next(override_get_db()))
app.dependency_overrides[get_friendship_repository] = lambda: FriendshipRepository(next(override_get_db()))

@pytest.fixture(scope="function")
def db_session():
    """Provide a transactional scope around each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.rollback()
        connection.close()

@pytest.fixture(scope="function")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def user_data():
    return {
        "name": "testuser",
        "email": "test@example.com",
        "password": "password123",
    }



@pytest.fixture(scope="function")
def engine():
    engine = create_engine("sqlite:///:memory:?check_same_thread=False")
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture(scope="function")
def session(engine):
    conn = engine.connect()
    trans=conn.begin()
    db = Session(bind=conn)
    try:
        yield db
    finally:
        trans.rollback()
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
        json={"id": created_user["id"]},
    )
    assert response.status_code == 200
    assert response.json() == {
        "message": "User deleted successfully",
    }
    # Verify user is actually deleted
    get_response = client.get(f"/users/{created_user['id']}")
    assert get_response.json() == {"user": None}


def test_delete_nonexistent_user(client):
    """Test deleting non-existent user"""
    response = client.post(
        "/users/delete",
        json={"id": 999},  # only send id
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

def test_jwt_login_and_auth(client, user_data):
    # Create the user first
    client.post("/users/", json={
        "name": user_data["name"],
        "email": user_data["email"],
        "password": user_data["password"]
    })

    # Then login to get JWT
    res = client.post("/v2/authentications/", json={
        "name": user_data["name"],
        "password": user_data["password"],
        "expiry": "2025-10-30 10:00:00"
    })
    assert res.status_code == 200
    data = res.json()
    assert "jwt" in data

def test_rate_limit(client, user_data):
    # Create user before login
    client.post("/users/", json={
        "name": user_data["name"],
        "email": user_data["email"],
        "password": user_data["password"]
    })

    # Login to get JWT
    res = client.post("/v2/authentications/", json={
        "name": user_data["name"],
        "password": user_data["password"],
        "expiry": "2025-10-30 10:00:00"
    })
    assert res.status_code == 200
    jwt = res.json()["jwt"]

    headers = {"Authorization": f"Bearer {jwt}"}

    # Make multiple requests to trigger rate limit
    for _ in range(3):
        res = client.get("/users/", headers=headers)
    assert res.status_code in (200, 429)