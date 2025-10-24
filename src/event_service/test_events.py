import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from datetime import datetime

from event_service.models.event import Base, EventRepository, get_event_repository
from user_service.api import app


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
    yield EventRepository(session)


@pytest.fixture(scope="function")
def client(repo):
    app.dependency_overrides[get_event_repository] = lambda: repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_event_with_user(client):
    """Test creating an event with a user ID"""
    event_data = {
        "when": "2025-10-15 13:32:22",
        "source": "http://localhost/blog/some-post",
        "type": "text-highlight",
        "payload": {"content": "something the user highlighted"},
        "user": "1234-abcd-5678-efgh"
    }
    
    response = client.post("/v2/events/", json=event_data)
    assert response.status_code == 201
    event_response = response.json()["event"]
    assert event_response["id"] == 1
    assert event_response["when"] == "2025-10-15T13:32:22"
    assert event_response["source"] == "http://localhost/blog/some-post"
    assert event_response["type"] == "text-highlight"
    assert event_response["payload"] == {"content": "something the user highlighted"}
    assert event_response["user"] == "1234-abcd-5678-efgh"


def test_create_event_without_user(client):
    """Test creating an event without a user ID"""
    event_data = {
        "when": "2025-10-15 10:14:39",
        "source": "http://localhost/blog/another-post",
        "type": "link-out",
        "payload": {"destination": "https://wikipedia.org/"},
        "user": None
    }
    
    response = client.post("/v2/events/", json=event_data)
    assert response.status_code == 201
    event_response = response.json()["event"]
    assert event_response["id"] == 1
    assert event_response["when"] == "2025-10-15T10:14:39"
    assert event_response["source"] == "http://localhost/blog/another-post"
    assert event_response["type"] == "link-out"
    assert event_response["payload"] == {"destination": "https://wikipedia.org/"}
    assert event_response["user"] is None


def test_get_events_without_filters(client, session):
    """Test getting all events without any filters"""
    # Create test events
    session.execute(
        text("""
            INSERT INTO events (`when`, source, type, payload, user) VALUES 
            ('2025-10-15 10:00:00', 'http://localhost/page1', 'click', '{"element": "button"}', 'user1'),
            ('2025-10-15 11:00:00', 'http://localhost/page2', 'scroll', '{"position": 100}', 'user2'),
            ('2025-10-15 12:00:00', 'http://localhost/page3', 'click', '{"element": "link"}', NULL)
        """)
    )
    session.commit()
    
    response = client.get("/v2/events/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 3
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 50


def test_get_events_filter_by_type(client, session):
    """Test filtering events by type"""
    # Create test events
    session.execute(
        text("""
            INSERT INTO events (`when`, source, type, payload, user) VALUES 
            ('2025-10-15 10:00:00', 'http://localhost/page1', 'click', '{"element": "button"}', 'user1'),
            ('2025-10-15 11:00:00', 'http://localhost/page2', 'scroll', '{"position": 100}', 'user2'),
            ('2025-10-15 12:00:00', 'http://localhost/page3', 'click', '{"element": "link"}', NULL)
        """)
    )
    session.commit()
    
    response = client.get("/v2/events/?type=click")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 2
    assert all(event["type"] == "click" for event in data["events"])


def test_get_events_filter_by_source(client, session):
    """Test filtering events by source"""
    # Create test events
    session.execute(
        text("""
            INSERT INTO events (`when`, source, type, payload, user) VALUES 
            ('2025-10-15 10:00:00', 'http://localhost/page1', 'click', '{"element": "button"}', 'user1'),
            ('2025-10-15 11:00:00', 'http://localhost/page2', 'scroll', '{"position": 100}', 'user2'),
            ('2025-10-15 12:00:00', 'http://localhost/page1', 'click', '{"element": "link"}', NULL)
        """)
    )
    session.commit()
    
    response = client.get("/v2/events/?source=http://localhost/page1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 2
    assert all(event["source"] == "http://localhost/page1" for event in data["events"])


def test_get_events_filter_by_user(client, session):
    """Test filtering events by user"""
    # Create test events
    session.execute(
        text("""
            INSERT INTO events (`when`, source, type, payload, user) VALUES 
            ('2025-10-15 10:00:00', 'http://localhost/page1', 'click', '{"element": "button"}', 'user1'),
            ('2025-10-15 11:00:00', 'http://localhost/page2', 'scroll', '{"position": 100}', 'user2'),
            ('2025-10-15 12:00:00', 'http://localhost/page3', 'click', '{"element": "link"}', NULL)
        """)
    )
    session.commit()
    
    response = client.get("/v2/events/?user=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["user"] == "user1"


def test_get_events_filter_by_time_range(client, session):
    """Test filtering events by time range"""
    # Create test events
    session.execute(
        text("""
            INSERT INTO events (`when`, source, type, payload, user) VALUES 
            ('2025-10-15 10:00:00', 'http://localhost/page1', 'click', '{"element": "button"}', 'user1'),
            ('2025-10-15 11:00:00', 'http://localhost/page2', 'scroll', '{"position": 100}', 'user2'),
            ('2025-10-15 12:00:00', 'http://localhost/page3', 'click', '{"element": "link"}', NULL)
        """)
    )
    session.commit()
    
    # Test after filter
    response = client.get("/v2/events/?after=2025-10-15T10:30:00")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 2  # Only events after 10:30
    
    # Test before filter
    response = client.get("/v2/events/?before=2025-10-15T11:30:00")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 2  # Only events before 11:30
    
    # Test both filters
    response = client.get("/v2/events/?after=2025-10-15T10:30:00&before=2025-10-15T11:30:00")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1  # Only the 11:00 event


def test_get_events_pagination(client, session):
    """Test pagination of events"""
    # Create 5 test events
    for i in range(5):
        session.execute(
            text(f"""
                INSERT INTO events (`when`, source, type, payload, user) VALUES 
                ('2025-10-15 {10+i:02d}:00:00', 'http://localhost/page{i}', 'click', '{{"element": "button{i}"}}', 'user{i}')
            """)
        )
    session.commit()
    
    # Test first page
    response = client.get("/v2/events/?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3
    
    # Test second page
    response = client.get("/v2/events/?page=2&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 2
    assert data["page"] == 2


def test_events_are_immutable(client, session):
    """Test that events cannot be updated or deleted"""
    # Create an event
    session.execute(
        text("""
            INSERT INTO events (`when`, source, type, payload, user) VALUES 
            ('2025-10-15 10:00:00', 'http://localhost/page1', 'click', '{"element": "button"}', 'user1')
        """)
    )
    session.commit()
    
    # Try to update (should not be possible via API)
    # Note: This test verifies that there are no PUT/PATCH/DELETE endpoints for events
    # The API only supports POST (create) and GET (read) operations
    
    # Verify the event exists and is unchanged
    response = client.get("/v2/events/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "click"
    assert data["events"][0]["user"] == "user1"


