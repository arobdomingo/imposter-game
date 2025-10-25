"""
Analytics API pytest测试文件
用于GitHub Actions自动化测试
"""

import pytest
import requests
from datetime import date, timedelta

# 测试配置
BASE_URL = "http://localhost:8000"
ANALYTICS_URL = f"{BASE_URL}/v2/analytics"


class TestAnalyticsAPI:
    """Analytics API测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.base_url = BASE_URL
        self.analytics_url = ANALYTICS_URL
        self.today = date.today()

    def test_health_check(self):
        """测试健康检查"""
        response = requests.get(f"{self.analytics_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data

    def test_today_analytics_initial(self):
        """测试初始分析数据"""
        response = requests.get(self.analytics_url)
        assert response.status_code == 200
        data = response.json()

        # 验证数据结构
        assert "session_length" in data
        assert "active_users" in data

        # 验证session_length结构
        session_length = data["session_length"]
        assert "min" in session_length
        assert "max" in session_length
        assert "mean" in session_length
        assert "median" in session_length
        assert "p95" in session_length

        # 验证active_users结构
        active_users = data["active_users"]
        assert "current" in active_users
        assert "max" in active_users

        # 初始状态应该是0
        assert active_users["current"] == 0
        assert active_users["max"] == 0

    def test_user_activity_simulation(self):
        """测试用户活动模拟"""
        # 模拟3次用户活动
        for i in range(3):
            response = requests.post(f"{self.analytics_url}/test")
            assert response.status_code == 200
            data = response.json()
            assert data["current_active"] == i + 1
            assert data["max_today"] == i + 1
            assert data["storage"] == "Memory"

    def test_analytics_after_activity(self):
        """测试活动后的分析数据"""
        # 先模拟一些活动
        for _ in range(2):
            requests.post(f"{self.analytics_url}/test")

        response = requests.get(self.analytics_url)
        assert response.status_code == 200
        data = response.json()

        # 验证数据更新
        assert data["active_users"]["current"] >= 2
        assert data["active_users"]["max"] >= 2
        assert data["session_length"]["min"] > 0
        assert data["session_length"]["max"] > 0
        assert data["session_length"]["mean"] > 0

    def test_save_daily_data(self):
        """测试保存每日数据"""
        response = requests.post(f"{self.analytics_url}/save-daily")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "data" in data
        assert "active_users" in data["data"]
        assert "max_users" in data["data"]
        assert "session_lengths" in data["data"]

    def test_specific_date_query(self):
        """测试指定日期查询"""
        # 先保存一些数据
        requests.post(f"{self.analytics_url}/save-daily")

        response = requests.get(f"{self.analytics_url}?on={self.today}")
        assert response.status_code == 200
        data = response.json()

        # 验证返回的数据结构
        assert "session_length" in data
        assert "active_users" in data

    def test_since_date_query(self):
        """测试期间平均查询"""
        # 先保存一些数据
        requests.post(f"{self.analytics_url}/save-daily")

        response = requests.get(f"{self.analytics_url}?since={self.today}")
        assert response.status_code == 200
        data = response.json()

        # 验证返回的数据结构
        assert "session_length" in data
        assert "active_users" in data

    def test_error_cases(self):
        """测试错误情况"""
        # 测试未来日期
        future_date = self.today + timedelta(days=1)
        response = requests.get(f"{self.analytics_url}?on={future_date}")
        assert response.status_code == 200
        data = response.json()
        if "error" in data:
            assert "No data available" in data["error"]

        # 测试过期日期（超过365天）
        old_date = self.today - timedelta(days=400)
        response = requests.get(f"{self.analytics_url}?on={old_date}")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "365 days ago" in data["error"]

    def test_statistics_calculation(self):
        """测试统计计算"""
        # 清空数据并重新开始
        requests.post(f"{self.analytics_url}/test")
        requests.post(f"{self.analytics_url}/test")

        response = requests.get(self.analytics_url)
        assert response.status_code == 200
        data = response.json()

        session_length = data["session_length"]

        # 验证统计计算
        assert session_length["min"] > 0
        assert session_length["max"] > 0
        assert session_length["mean"] > 0
        assert session_length["median"] > 0
        assert session_length["p95"] > 0

        # 验证统计关系
        assert session_length["min"] <= session_length["mean"]
        assert session_length["mean"] <= session_length["max"]
        assert session_length["median"] <= session_length["p95"]

    def test_api_endpoints_availability(self):
        """测试所有API端点可用性"""
        endpoints = [
            ("GET", f"{self.analytics_url}", "今日分析"),
            ("GET", f"{self.analytics_url}/health", "健康检查"),
            ("POST", f"{self.analytics_url}/test", "用户活动模拟"),
            ("POST", f"{self.analytics_url}/save-daily", "保存每日数据"),
        ]

        for method, url, name in endpoints:
            if method == "GET":
                response = requests.get(url)
            else:
                response = requests.post(url)

            assert response.status_code == 200, (
                f"{name} 端点返回错误状态码: {response.status_code}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
