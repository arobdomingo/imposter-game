import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from user_service.models.user import Base, User
import user_service.models.friendship  # noqa: F401
import event_service.models.event  # noqa: F401
import game_service.models  # noqa: F401

from admin.main import app
from shared.database import get_db


@pytest.fixture(scope="function")
def engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="function")
def session(engine):
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def users(session):
    user_objs = [
        User(name="user1", email="user1@example.com", password="pass1"),
        User(name="user2", email="user2@example.com", password="pass2"),
        User(name="user3", email="user3@example.com", password="pass3"),
        User(name="user4", email="user4@example.com", password="pass4"),
    ]
    session.add_all(user_objs)
    session.commit()
    return user_objs


@pytest.fixture(scope="session")
def app_fixture():
    """Provide the FastAPI app instance for HTTP route testing."""
    return app


@pytest.fixture(scope="function")
def apply_db_override(app_fixture, session):
    """
    Override FastAPI get_db dependency so route handlers
    use the SAME in-memory database session used by repo tests.
    """

    def override_get_db():
        yield session

    app_fixture.dependency_overrides[get_db] = override_get_db
    yield
    app_fixture.dependency_overrides.clear()
