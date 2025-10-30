"""
Event Service pytest test file
For GitHub Actions automated testing
"""

import pytest
import requests
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://localhost:8000"
EVENTS_URL = f"{BASE_URL}/v2/events"


class TestEventService:
    """Event Service test class"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Test setup - clean up any existing events"""
        pass  # Events are immutable, so no cleanup needed

    def test_health_check(self):
        """Test that the service is running"""
        # This is a basic connectivity test
        try:
            response = requests.get(f"{EVENTS_URL}/", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.RequestException:
            pytest.skip("Service not available")

    def test_create_event(self):
        """Test creating a new event"""
        event_data = {
            "when": datetime.now().isoformat(),
            "source": "test_source",
            "type": "test_event",
            "payload": {"test": "data", "value": 123},
            "user": "test_user",
        }

        response = requests.post(f"{EVENTS_URL}/", json=event_data, timeout=5)
        assert response.status_code == 201
        data = response.json()

        assert "event" in data
        event = data["event"]
        assert event["source"] == "test_source"
        assert event["type"] == "test_event"
        assert event["user"] == "test_user"
        assert "id" in event

    def test_create_event_minimal(self):
        """Test creating an event with minimal data"""
        event_data = {
            "when": datetime.now().isoformat(),
            "source": "minimal_test",
            "type": "minimal_event",
            "payload": {},
        }

        response = requests.post(f"{EVENTS_URL}/", json=event_data, timeout=5)
        assert response.status_code == 201
        data = response.json()

        assert "event" in data
        event = data["event"]
        assert event["source"] == "minimal_test"
        assert event["type"] == "minimal_event"
        assert event["user"] is None

    def test_get_events_default(self):
        """Test getting events with default parameters"""
        response = requests.get(f"{EVENTS_URL}/", timeout=5)
        assert response.status_code == 200
        data = response.json()

        assert "events" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["events"], list)

    def test_get_events_with_pagination(self):
        """Test getting events with pagination"""
        response = requests.get(f"{EVENTS_URL}/?page=1&page_size=10", timeout=5)
        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["events"]) <= 10

    def test_get_events_filter_by_type(self):
        """Test filtering events by type"""
        # First create a test event
        event_data = {
            "when": datetime.now().isoformat(),
            "source": "filter_test",
            "type": "filtered_event",
            "payload": {"test": "filter"},
        }
        requests.post(f"{EVENTS_URL}/", json=event_data, timeout=5)

        # Then filter by type
        response = requests.get(f"{EVENTS_URL}/?type=filtered_event", timeout=5)
        assert response.status_code == 200
        data = response.json()

        # Should have at least one event
        assert len(data["events"]) >= 1
        for event in data["events"]:
            assert event["type"] == "filtered_event"

    def test_get_events_filter_by_source(self):
        """Test filtering events by source"""
        # First create a test event
        event_data = {
            "when": datetime.now().isoformat(),
            "source": "source_filter_test",
            "type": "source_event",
            "payload": {"test": "source_filter"},
        }
        requests.post(f"{EVENTS_URL}/", json=event_data, timeout=5)

        # Then filter by source
        response = requests.get(f"{EVENTS_URL}/?source=source_filter_test", timeout=5)
        assert response.status_code == 200
        data = response.json()

        # Should have at least one event
        assert len(data["events"]) >= 1
        for event in data["events"]:
            assert event["source"] == "source_filter_test"

    def test_get_events_filter_by_user(self):
        """Test filtering events by user"""
        # First create a test event
        event_data = {
            "when": datetime.now().isoformat(),
            "source": "user_filter_test",
            "type": "user_event",
            "payload": {"test": "user_filter"},
            "user": "filter_test_user",
        }
        requests.post(f"{EVENTS_URL}/", json=event_data, timeout=5)

        # Then filter by user
        response = requests.get(f"{EVENTS_URL}/?user=filter_test_user", timeout=5)
        assert response.status_code == 200
        data = response.json()

        # Should have at least one event
        assert len(data["events"]) >= 1
        for event in data["events"]:
            assert event["user"] == "filter_test_user"

    def test_get_events_time_filter(self):
        """Test filtering events by time range"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        # Filter events after yesterday
        response = requests.get(
            f"{EVENTS_URL}/?after={yesterday.isoformat()}", timeout=5
        )
        assert response.status_code == 200
        data = response.json()

        # All events should be after yesterday
        for event in data["events"]:
            event_time = datetime.fromisoformat(event["when"].replace("Z", "+00:00"))
            assert event_time > yesterday

    def test_invalid_pagination(self):
        """Test invalid pagination parameters"""
        # Test negative page
        response = requests.get(f"{EVENTS_URL}/?page=-1", timeout=5)
        assert response.status_code == 422  # Validation error

        # Test page size too large
        response = requests.get(f"{EVENTS_URL}/?page_size=2000", timeout=5)
        assert response.status_code == 422  # Validation error
