"""
Analytics API pytest test file
For GitHub Actions automated testing
"""

import pytest
import requests
from datetime import date, timedelta

# Test configuration
BASE_URL = "http://localhost:8000"
ANALYTICS_URL = f"{BASE_URL}/v2/analytics"


class TestAnalyticsAPI:
    """Analytics API test class"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Test setup"""
        # Reset analytics data before each test
        try:
            requests.post(f"{ANALYTICS_URL}/reset", timeout=5)
        except requests.exceptions.RequestException:
            pass  # Service might not be running

    def test_health_check(self):
        """Test health check endpoint"""
        response = requests.get(f"{ANALYTICS_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_get_analytics_default(self):
        """Test getting analytics data (today's data)"""
        response = requests.get(ANALYTICS_URL, timeout=5)
        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "session_length" in data
        assert "active_users" in data
        assert "current" in data["active_users"]
        assert "max" in data["active_users"]

    def test_simulate_user_activity(self):
        """Test simulating user activity"""
        response = requests.post(f"{ANALYTICS_URL}/test", timeout=5)
        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "current_active" in data
        assert "max_today" in data
        assert data["storage"] == "Memory"

    def test_save_daily_data(self):
        """Test saving daily data"""
        # First simulate some activity
        requests.post(f"{ANALYTICS_URL}/test", timeout=5)

        # Then save daily data
        response = requests.post(f"{ANALYTICS_URL}/save-daily", timeout=5)
        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "data" in data
        assert str(date.today()) in data["message"]

    def test_reset_analytics(self):
        """Test resetting analytics data"""
        # First simulate some activity
        requests.post(f"{ANALYTICS_URL}/test", timeout=5)

        # Then reset
        response = requests.post(f"{ANALYTICS_URL}/reset", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "reset successfully" in data["message"]

    def test_get_analytics_with_date_query(self):
        """Test getting analytics for specific date"""
        today = date.today()
        response = requests.get(f"{ANALYTICS_URL}/?on={today}", timeout=5)
        assert response.status_code == 200
        data = response.json()

        # Should return error since no data for today yet
        assert "error" in data

    def test_get_analytics_with_since_query(self):
        """Test getting analytics since specific date"""
        yesterday = date.today() - timedelta(days=1)
        response = requests.get(f"{ANALYTICS_URL}/?since={yesterday}", timeout=5)
        assert response.status_code == 200
        data = response.json()

        # Should return error since no data available
        assert "error" in data

    def test_invalid_date_query(self):
        """Test query with invalid date (too far in past)"""
        old_date = date.today() - timedelta(days=400)
        response = requests.get(f"{ANALYTICS_URL}/?on={old_date}", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "365 days ago" in data["error"]
