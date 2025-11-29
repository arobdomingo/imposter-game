from fastapi import APIRouter, Query
from datetime import date, timedelta
from typing import Optional
import statistics

router = APIRouter(prefix="/v2/analytics", tags=["Analytics"])

# Simple in-memory storage
_analytics_data = {"active_users": 0, "max_users_today": 0, "session_lengths": []}

# Historical data storage (simulating database)
_historical_data = {}


def calculate_session_stats(session_lengths):
    """Calculate session length statistics"""
    if not session_lengths:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0}

    sorted_lengths = sorted(session_lengths)
    n = len(sorted_lengths)

    # Calculate 95th percentile
    p95_index = int(0.95 * n)
    if p95_index >= n:
        p95_index = n - 1

    return {
        "min": min(session_lengths),
        "max": max(session_lengths),
        "mean": statistics.mean(session_lengths),
        "median": statistics.median(session_lengths),
        "p95": sorted_lengths[p95_index],
    }


@router.get("/")
async def get_analytics(
    on: Optional[date] = Query(None, description="Get analytics for specific date"),
    since: Optional[date] = Query(None, description="Get mean analytics since date"),
):
    """Get analytics data - supports 3 query modes"""
    today = date.today()

    # Validate date limits (no more than 365 days ago)
    max_past_date = today - timedelta(days=365)

    if on and on < max_past_date:
        return {"error": "Date must be no more than 365 days ago"}

    if since and since < max_past_date:
        return {"error": "Since date must be no more than 365 days ago"}

    if on:
        # Specific date query
        if on in _historical_data:
            data = _historical_data[on]
            return {
                "session_length": calculate_session_stats(data["session_lengths"]),
                "active_users": {
                    "current": data["active_users"],
                    "max": data["max_users"],
                },
            }
        else:
            return {"error": f"No data available for {on}"}

    elif since:
        # Period average query
        if since not in _historical_data:
            return {"error": f"No data available since {since}"}

        # Calculate period averages
        period_data = []
        current_date = since
        while current_date <= today:
            if current_date in _historical_data:
                period_data.append(_historical_data[current_date])
            current_date += timedelta(days=1)

        if not period_data:
            return {"error": "No data available for the specified period"}

        # Calculate averages
        session_mins = [
            d["session_lengths"] and min(d["session_lengths"]) or 0 for d in period_data
        ]
        session_maxs = [
            d["session_lengths"] and max(d["session_lengths"]) or 0 for d in period_data
        ]
        session_means = [
            d["session_lengths"] and statistics.mean(d["session_lengths"]) or 0
            for d in period_data
        ]
        session_medians = [
            d["session_lengths"] and statistics.median(d["session_lengths"]) or 0
            for d in period_data
        ]
        session_p95s = [
            d["session_lengths"]
            and calculate_session_stats(d["session_lengths"])["p95"]
            or 0
            for d in period_data
        ]

        current_users = [d["active_users"] for d in period_data]
        max_users = [d["max_users"] for d in period_data]

        return {
            "session_length": {
                "min": statistics.mean(session_mins),
                "max": statistics.mean(session_maxs),
                "mean": statistics.mean(session_means),
                "median": statistics.mean(session_medians),
                "p95": statistics.mean(session_p95s),
            },
            "active_users": {
                "current": statistics.mean(current_users),
                "max": statistics.mean(max_users),
            },
        }

    else:
        # Today's real-time query
        return {
            "session_length": calculate_session_stats(
                _analytics_data["session_lengths"]
            ),
            "active_users": {
                "current": _analytics_data["active_users"],
                "max": _analytics_data["max_users_today"],
            },
        }


@router.post("/test")
async def test_user_activity():
    """Test endpoint - simulate user activity"""
    session_length = 300.0  # 5-minute session

    # Update current data
    _analytics_data["active_users"] += 1
    _analytics_data["max_users_today"] = max(
        _analytics_data["max_users_today"], _analytics_data["active_users"]
    )
    _analytics_data["session_lengths"].append(session_length)

    return {
        "message": "User activity simulated",
        "current_active": _analytics_data["active_users"],
        "max_today": _analytics_data["max_users_today"],
        "storage": "Memory",
    }


@router.post("/save-daily")
async def save_daily_data():
    """Save today's data to historical records"""
    today = date.today()
    _historical_data[today] = {
        "active_users": _analytics_data["active_users"],
        "max_users": _analytics_data["max_users_today"],
        "session_lengths": _analytics_data["session_lengths"].copy(),
    }

    return {"message": f"Daily data saved for {today}", "data": _historical_data[today]}


@router.post("/reset")
async def reset_analytics_data():
    """Reset analytics data to initial state"""
    global _analytics_data, _historical_data
    _analytics_data = {"active_users": 0, "max_users_today": 0, "session_lengths": []}
    _historical_data = {}
    return {"message": "Analytics data reset successfully"}


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "message": "Analytics service is working"}
