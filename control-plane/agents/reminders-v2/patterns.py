#!/usr/bin/env python3
"""
Pattern Analyzer for REMINDERS-V2

Analyzes user behavior patterns to optimize reminder timing:
- Peak activity hours
- Response time patterns
- Preferred notification times
- Focus/productivity cycles
- Day-of-week patterns
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics


@dataclass
class UserPatterns:
    """User behavior patterns derived from activity analysis"""
    user_id: str
    peak_focus_hours: List[int]  # Hours with best focus (0-23)
    peak_activity_hours: List[int]  # Hours with most activity
    best_response_hours: List[int]  # Hours with fastest response times
    preferred_days: List[int]  # Day of week patterns (0=Monday)
    average_response_time: float  # Average response time in seconds
    focus_duration: int  # Typical focus session duration in minutes
    break_frequency: int  # How often breaks are taken (minutes)
    morning_person: bool  # Is user more active in morning
    evening_person: bool  # Is user more active in evening
    low_activity_hours: List[int]  # Hours to avoid reminders
    last_updated: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPatterns':
        return cls(**data)

    @classmethod
    def default(cls, user_id: str) -> 'UserPatterns':
        """Create default patterns for new users"""
        return cls(
            user_id=user_id,
            peak_focus_hours=[9, 10, 11, 14, 15, 16],
            peak_activity_hours=[9, 10, 11, 14, 15, 16, 17],
            best_response_hours=[10, 11, 14, 15],
            preferred_days=[0, 1, 2, 3, 4],  # Weekdays
            average_response_time=300.0,  # 5 minutes
            focus_duration=25,  # Pomodoro default
            break_frequency=25,
            morning_person=True,
            evening_person=False,
            low_activity_hours=[0, 1, 2, 3, 4, 5, 6, 22, 23],
            last_updated=datetime.now().isoformat()
        )


class PatternAnalyzer:
    """
    Analyzes user activity patterns to optimize reminder timing.

    Uses historical data to determine:
    - Best times to send reminders
    - User's natural rhythms
    - Response patterns
    """

    def __init__(self, patterns_path: str, db_path: str = None):
        self.patterns_path = Path(patterns_path)
        self.db_path = db_path
        self.patterns_cache: Dict[str, UserPatterns] = {}
        self._load_patterns()

    def _load_patterns(self):
        """Load patterns from JSON file"""
        if self.patterns_path.exists():
            try:
                with open(self.patterns_path) as f:
                    data = json.load(f)
                    for user_id, pattern_data in data.items():
                        self.patterns_cache[user_id] = UserPatterns.from_dict(pattern_data)
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error loading patterns: {e}")

    def _save_patterns(self):
        """Save patterns to JSON file"""
        self.patterns_path.parent.mkdir(parents=True, exist_ok=True)
        data = {user_id: pattern.to_dict() for user_id, pattern in self.patterns_cache.items()}
        with open(self.patterns_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_patterns(self, user_id: str) -> UserPatterns:
        """Get patterns for a user, creating defaults if needed"""
        if user_id not in self.patterns_cache:
            self.patterns_cache[user_id] = UserPatterns.default(user_id)
            self._save_patterns()
        return self.patterns_cache[user_id]

    def analyze_activity(self, user_id: str, db_path: str) -> UserPatterns:
        """
        Analyze activity log to derive patterns.

        This should be run periodically to update patterns based on new data.
        """
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Get activity by hour
        c.execute('''
            SELECT hour_of_day, COUNT(*) as count,
                   AVG(response_time_seconds) as avg_response
            FROM activity_log
            WHERE user_id = ?
            GROUP BY hour_of_day
        ''', (user_id,))

        hourly_data = {row['hour_of_day']: {
            'count': row['count'],
            'avg_response': row['avg_response'] or 300
        } for row in c.fetchall()}

        # Get activity by day of week
        c.execute('''
            SELECT day_of_week, COUNT(*) as count
            FROM activity_log
            WHERE user_id = ?
            GROUP BY day_of_week
            ORDER BY count DESC
        ''', (user_id,))

        day_data = {row['day_of_week']: row['count'] for row in c.fetchall()}

        # Get overall response time
        c.execute('''
            SELECT AVG(response_time_seconds) as avg_response
            FROM activity_log
            WHERE user_id = ? AND response_time_seconds IS NOT NULL
        ''', (user_id,))

        avg_response = c.fetchone()['avg_response'] or 300

        conn.close()

        # Analyze patterns
        if not hourly_data:
            return UserPatterns.default(user_id)

        # Find peak hours (top 40% by activity count)
        if hourly_data:
            sorted_hours = sorted(hourly_data.items(), key=lambda x: x[1]['count'], reverse=True)
            top_count = max(1, len(sorted_hours) // 3)
            peak_activity = [h for h, _ in sorted_hours[:top_count]]

            # Best response hours (fastest 30%)
            response_sorted = sorted(hourly_data.items(), key=lambda x: x[1]['avg_response'])
            best_response = [h for h, _ in response_sorted[:max(1, len(response_sorted) // 3)]]

            # Low activity hours
            low_activity = [h for h in range(24) if h not in hourly_data or hourly_data[h]['count'] < 2]
        else:
            peak_activity = [9, 10, 11, 14, 15, 16]
            best_response = [10, 11, 14, 15]
            low_activity = [0, 1, 2, 3, 4, 5, 6, 22, 23]

        # Determine morning/evening person
        morning_activity = sum(hourly_data.get(h, {}).get('count', 0) for h in range(6, 12))
        evening_activity = sum(hourly_data.get(h, {}).get('count', 0) for h in range(18, 24))

        # Preferred days
        preferred_days = sorted(day_data.keys(), key=lambda d: day_data[d], reverse=True)[:5] if day_data else [0,1,2,3,4]

        # Calculate focus duration from activity gaps
        focus_duration = self._estimate_focus_duration(user_id, db_path)

        patterns = UserPatterns(
            user_id=user_id,
            peak_focus_hours=peak_activity[:6],  # Top 6 hours
            peak_activity_hours=peak_activity,
            best_response_hours=best_response,
            preferred_days=preferred_days,
            average_response_time=avg_response,
            focus_duration=focus_duration,
            break_frequency=focus_duration,  # Assume break after focus
            morning_person=morning_activity > evening_activity,
            evening_person=evening_activity > morning_activity,
            low_activity_hours=low_activity,
            last_updated=datetime.now().isoformat()
        )

        self.patterns_cache[user_id] = patterns
        self._save_patterns()

        return patterns

    def _estimate_focus_duration(self, user_id: str, db_path: str) -> int:
        """Estimate typical focus session duration from activity gaps"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        c.execute('''
            SELECT timestamp FROM activity_log
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (user_id,))

        timestamps = [datetime.fromisoformat(row[0]) for row in c.fetchall() if row[0]]
        conn.close()

        if len(timestamps) < 2:
            return 25  # Default Pomodoro

        # Calculate gaps between activities
        gaps = []
        for i in range(len(timestamps) - 1):
            gap = (timestamps[i] - timestamps[i + 1]).total_seconds() / 60  # minutes
            if 5 < gap < 120:  # Reasonable focus session range
                gaps.append(gap)

        if gaps:
            return int(statistics.median(gaps))
        return 25

    def get_optimal_reminder_time(
        self,
        user_id: str,
        reminder_type: str = "standard",
        priority: str = "normal",
        target_date: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate optimal time to send a reminder based on user patterns.

        Args:
            user_id: User ID to get patterns for
            reminder_type: Type of reminder (standard, deadline, checkin, motivational)
            priority: Priority level (low, normal, high, urgent)
            target_date: Optional target date, defaults to today/tomorrow

        Returns:
            Optimal datetime for the reminder
        """
        patterns = self.get_patterns(user_id)
        now = datetime.now()

        # For urgent, send immediately
        if priority == "urgent":
            return now + timedelta(minutes=1)

        # Determine candidate hours based on reminder type
        if reminder_type in ["checkin", "motivational"]:
            # Use peak focus hours for check-ins (when user is most engaged)
            candidate_hours = patterns.peak_focus_hours
        elif reminder_type == "deadline":
            # Use best response hours for deadline reminders
            candidate_hours = patterns.best_response_hours
        else:
            # Standard reminders - use peak activity hours
            candidate_hours = patterns.peak_activity_hours

        # Filter out low activity hours
        candidate_hours = [h for h in candidate_hours if h not in patterns.low_activity_hours]

        if not candidate_hours:
            candidate_hours = [10, 14, 16]  # Fallback

        # Determine target date
        if target_date:
            base_date = target_date.date()
        else:
            base_date = now.date()
            # If it's late, schedule for tomorrow
            if now.hour >= max(candidate_hours):
                base_date = base_date + timedelta(days=1)

        # Find next available hour
        for hour in sorted(candidate_hours):
            candidate = datetime.combine(base_date, datetime.min.time().replace(hour=hour))
            if candidate > now:
                # Add some minutes to avoid exact hour (feels more natural)
                candidate = candidate + timedelta(minutes=(hash(user_id) % 15))
                return candidate

        # If no hour today, use first hour tomorrow
        tomorrow = base_date + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time().replace(hour=candidate_hours[0]))

    def should_send_now(self, user_id: str) -> Tuple[bool, str]:
        """
        Determine if now is a good time to send a notification.

        Returns:
            Tuple of (should_send, reason)
        """
        patterns = self.get_patterns(user_id)
        now = datetime.now()
        current_hour = now.hour
        current_day = now.weekday()

        # Never send during low activity hours
        if current_hour in patterns.low_activity_hours:
            return False, f"Current hour ({current_hour}) is in low activity period"

        # Prefer preferred days
        if current_day not in patterns.preferred_days:
            return False, f"Today ({current_day}) is not a preferred day"

        # Best if during peak hours
        if current_hour in patterns.peak_activity_hours:
            return True, "Current time is during peak activity hours"

        # Acceptable if not during low hours
        return True, "Acceptable time window"

    def get_next_good_time(self, user_id: str, min_delay_minutes: int = 15) -> datetime:
        """
        Get the next good time to send a notification.

        Args:
            user_id: User to check patterns for
            min_delay_minutes: Minimum delay from now

        Returns:
            Next optimal datetime
        """
        patterns = self.get_patterns(user_id)
        now = datetime.now() + timedelta(minutes=min_delay_minutes)

        # Check if current hour is good
        if now.hour in patterns.peak_activity_hours and now.hour not in patterns.low_activity_hours:
            return now

        # Find next peak hour
        for offset_hours in range(1, 24):
            candidate = now + timedelta(hours=offset_hours)
            if candidate.hour in patterns.peak_activity_hours and candidate.hour not in patterns.low_activity_hours:
                return candidate.replace(minute=0, second=0, microsecond=0)

        # Fallback to 10 AM tomorrow
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time().replace(hour=10))

    def update_from_response(self, user_id: str, response_time_seconds: float, hour: int, success: bool):
        """
        Update patterns based on a user response to a reminder.

        This provides real-time pattern updates for adaptive scheduling.
        """
        patterns = self.get_patterns(user_id)

        # Update average response time (exponential moving average)
        alpha = 0.1  # Weight for new data
        patterns.average_response_time = (
            alpha * response_time_seconds +
            (1 - alpha) * patterns.average_response_time
        )

        # If fast response at this hour, consider it a peak hour
        if success and response_time_seconds < patterns.average_response_time:
            if hour not in patterns.best_response_hours:
                patterns.best_response_hours.append(hour)
                patterns.best_response_hours = sorted(patterns.best_response_hours)

        patterns.last_updated = datetime.now().isoformat()
        self.patterns_cache[user_id] = patterns
        self._save_patterns()

    def get_adhd_friendly_intervals(self, user_id: str) -> Dict[str, int]:
        """
        Get ADHD-friendly intervals for various reminder types.

        Based on research suggesting shorter, more frequent check-ins
        work better for ADHD.
        """
        patterns = self.get_patterns(user_id)

        # Base intervals on user's observed focus duration
        focus = patterns.focus_duration or 25

        return {
            "focus_check": max(15, focus // 2),  # Check mid-focus
            "break_reminder": focus,  # Remind to take break
            "motivation": focus * 2,  # Motivational every 2 sessions
            "task_nudge": max(10, focus // 3),  # Gentle task nudges
            "hydration": 45,  # Stay hydrated
            "movement": 60,  # Movement reminder
            "daily_summary": 480  # 8 hours
        }

    def get_pattern_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a human-readable summary of user patterns"""
        patterns = self.get_patterns(user_id)

        return {
            "user_id": user_id,
            "chronotype": "morning person" if patterns.morning_person else "evening person" if patterns.evening_person else "balanced",
            "peak_hours": f"{min(patterns.peak_focus_hours)}:00-{max(patterns.peak_focus_hours)+1}:00" if patterns.peak_focus_hours else "Not determined",
            "average_response": f"{patterns.average_response_time:.0f} seconds",
            "focus_style": f"{patterns.focus_duration} minute sessions",
            "best_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][patterns.preferred_days[0]] if patterns.preferred_days else "Not determined",
            "quiet_hours": f"{min(patterns.low_activity_hours)}:00-{max(patterns.low_activity_hours)+1}:00" if patterns.low_activity_hours else "None set",
            "last_analysis": patterns.last_updated
        }
