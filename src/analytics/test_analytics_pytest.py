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
        self.base_url = BASE_URL
        self.analytics_url = ANALYTICS_URL
        self.today = date.today()

    def test_health_check(self):
        """Test health check"""
        response = requests.get(f"{self.analytics_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data

    def test_today_analytics_initial(self):
        """Test initial analytics data"""
        response = requests.get(self.analytics_url)
        assert response.status_code == 200
        data = response.json()

        # Validate data structure
        assert "session_length" in data
        assert "active_users" in data

        # Validate session_length structure
        session_length = data["session_length"]
        assert "min" in session_length
        assert "max" in session_length
        assert "mean" in session_length
        assert "median" in session_length
        assert "p95" in session_length

        # Validate active_users structure
        active_users = data["active_users"]
        assert "current" in active_users
        assert "max" in active_users

        # Initial state should be 0
        assert active_users["current"] == 0
        assert active_users["max"] == 0

    def test_user_activity_simulation(self):
        """Test user activity simulation"""
        # Simulate 3 user activities
        for i in range(3):
            response = requests.post(f"{self.analytics_url}/test")
            assert response.status_code == 200
            data = response.json()
            assert data["current_active"] == i + 1
            assert data["max_today"] == i + 1
            assert data["storage"] == "Memory"

    def test_analytics_after_activity(self):
        """Test analytics after activity"""
        # Simulate some activities first
        for _ in range(2):
            requests.post(f"{self.analytics_url}/test")

        response = requests.get(self.analytics_url)
        assert response.status_code == 200
        data = response.json()

        # Validate data updates
        assert data["active_users"]["current"] >= 2
        assert data["active_users"]["max"] >= 2
        assert data["session_length"]["min"] > 0
        assert data["session_length"]["max"] > 0
        assert data["session_length"]["mean"] > 0

    def test_save_daily_data(self):
        """Test save daily data"""
        response = requests.post(f"{self.analytics_url}/save-daily")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "data" in data
        assert "active_users" in data["data"]
        assert "max_users" in data["data"]
        assert "session_lengths" in data["data"]

    def test_specific_date_query(self):
        """Test specific date query"""
        # Save some data first
        requests.post(f"{self.analytics_url}/save-daily")

        response = requests.get(f"{self.analytics_url}?on={self.today}")
        assert response.status_code == 200
        data = response.json()

        # Validate returned data structure
        assert "session_length" in data
        assert "active_users" in data

    def test_since_date_query(self):
        """Test period average query"""
        # Save some data first
        requests.post(f"{self.analytics_url}/save-daily")

        response = requests.get(f"{self.analytics_url}?since={self.today}")
        assert response.status_code == 200
        data = response.json()

        # Validate returned data structure
        assert "session_length" in data
        assert "active_users" in data

    def test_error_cases(self):
        """Test error cases"""
        # Test future date
        future_date = self.today + timedelta(days=1)
        response = requests.get(f"{self.analytics_url}?on={future_date}")
        assert response.status_code == 200
        data = response.json()
        if "error" in data:
            assert "No data available" in data["error"]

        # Test expired date (more than 365 days)
        old_date = self.today - timedelta(days=400)
        response = requests.get(f"{self.analytics_url}?on={old_date}")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "365 days ago" in data["error"]

    def test_statistics_calculation(self):
        """Test statistics calculation"""
        # Clear data and start fresh
        requests.post(f"{self.analytics_url}/test")
        requests.post(f"{self.analytics_url}/test")

        response = requests.get(self.analytics_url)
        assert response.status_code == 200
        data = response.json()

        session_length = data["session_length"]

        # Validate statistics calculation
        assert session_length["min"] > 0
        assert session_length["max"] > 0
        assert session_length["mean"] > 0
        assert session_length["median"] > 0
        assert session_length["p95"] > 0

        # Validate statistical relationships
        assert session_length["min"] <= session_length["mean"]
        assert session_length["mean"] <= session_length["max"]
        assert session_length["median"] <= session_length["p95"]

    def test_api_endpoints_availability(self):
        """Test all API endpoints availability"""
        endpoints = [
            ("GET", f"{self.analytics_url}", "Today's analytics"),
            ("GET", f"{self.analytics_url}/health", "Health check"),
            ("POST", f"{self.analytics_url}/test", "User activity simulation"),
            ("POST", f"{self.analytics_url}/save-daily", "Save daily data"),
        ]

        for method, url, name in endpoints:
            if method == "GET":
                response = requests.get(url)
            else:
                response = requests.post(url)

            assert response.status_code == 200, (
                f"{name} endpoint returned error status code: {response.status_code}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
