"""
Cost tracking system for AI API usage.

Monitors and manages costs for Claude API, Gemini API, and other paid services.
"""

import json
import time
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional

class CostTracker:
    """Tracks and manages AI API costs with daily limits and reporting."""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent.parent / "data"
        self.cost_file = self.data_dir / "cost_tracking.json"

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

        # Cost tracking data
        self.daily_costs = {}
        self.cost_history = []
        self.daily_limit = 5.00  # Default $5 daily limit

        # Load existing data
        self._load_data()

    def _load_data(self):
        """Load cost tracking data from file."""
        try:
            if self.cost_file.exists():
                with open(self.cost_file, 'r') as f:
                    data = json.load(f)

                self.daily_costs = data.get("daily_costs", {})
                self.cost_history = data.get("cost_history", [])
                self.daily_limit = data.get("daily_limit", 5.00)

                # Clean up old daily cost entries (keep only last 30 days)
                today = date.today().isoformat()
                cutoff_date = (date.today().replace(day=1) -
                             date.today().replace(day=1, month=date.today().month-1 if date.today().month > 1 else 12)).isoformat()

                self.daily_costs = {
                    date_str: cost for date_str, cost in self.daily_costs.items()
                    if date_str >= cutoff_date
                }

        except Exception as e:
            print(f"Failed to load cost tracking data: {e}")
            self._initialize_defaults()

    def _initialize_defaults(self):
        """Initialize with default values."""
        self.daily_costs = {}
        self.cost_history = []
        self.daily_limit = 5.00

    def _save_data(self):
        """Save cost tracking data to file."""
        try:
            data = {
                "daily_costs": self.daily_costs,
                "cost_history": self.cost_history,
                "daily_limit": self.daily_limit,
                "last_updated": datetime.now().isoformat()
            }

            with open(self.cost_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Failed to save cost tracking data: {e}")

    def record_api_call(self, service: str, model: str, input_tokens: int, output_tokens: int, cost: float):
        """Record an API call and its cost."""
        today = date.today().isoformat()
        timestamp = datetime.now().isoformat()

        # Add to daily total
        if today not in self.daily_costs:
            self.daily_costs[today] = 0.0
        self.daily_costs[today] += cost

        # Add to history
        call_record = {
            "timestamp": timestamp,
            "service": service,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "daily_total": self.daily_costs[today]
        }
        self.cost_history.append(call_record)

        # Keep only last 1000 history entries
        if len(self.cost_history) > 1000:
            self.cost_history = self.cost_history[-1000:]

        self._save_data()

        # Check if we're approaching or exceeding limits
        self._check_limits(today)

        return call_record

    def estimate_claude_cost(self, input_tokens: int, output_tokens: int, model: str = "claude-sonnet-4-20250514") -> float:
        """Estimate cost for a Claude API call."""
        # Claude pricing (as of 2025)
        pricing = {
            "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},  # per 1K tokens
            "claude-opus-4-6": {"input": 0.015, "output": 0.075},
            "claude-haiku-4-5": {"input": 0.00025, "output": 0.00125}
        }

        if model not in pricing:
            model = "claude-sonnet-4-20250514"  # default

        rates = pricing[model]
        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]

        return input_cost + output_cost

    def estimate_gemini_cost(self, input_tokens: int, output_tokens: int, model: str = "gemini-3-flash-preview") -> float:
        """Estimate cost for a Gemini API call."""
        # Gemini is currently free for the model being used
        return 0.0

    def get_today_cost(self) -> float:
        """Get today's total cost."""
        today = date.today().isoformat()
        return self.daily_costs.get(today, 0.0)

    def get_remaining_budget(self) -> float:
        """Get remaining budget for today."""
        return max(0.0, self.daily_limit - self.get_today_cost())

    def can_afford_call(self, estimated_cost: float) -> bool:
        """Check if we can afford a call within daily limit."""
        return (self.get_today_cost() + estimated_cost) <= self.daily_limit

    def set_daily_limit(self, limit: float):
        """Set daily spending limit."""
        self.daily_limit = max(0.0, float(limit))
        self._save_data()

    def reset_daily(self):
        """Reset today's cost counter (for testing or manual reset)."""
        today = date.today().isoformat()
        if today in self.daily_costs:
            self.daily_costs[today] = 0.0
            self._save_data()

    def get_weekly_summary(self) -> Dict:
        """Get cost summary for the past 7 days."""
        today = date.today()
        week_dates = [(today - date.today().replace(day=today.day-i)).isoformat()
                      for i in range(7)]

        summary = {
            "dates": week_dates,
            "costs": [self.daily_costs.get(d, 0.0) for d in week_dates],
            "total": sum(self.daily_costs.get(d, 0.0) for d in week_dates),
            "average": sum(self.daily_costs.get(d, 0.0) for d in week_dates) / 7,
            "days_over_limit": len([d for d in week_dates if self.daily_costs.get(d, 0.0) > self.daily_limit])
        }

        return summary

    def get_service_breakdown(self, days: int = 7) -> Dict:
        """Get cost breakdown by service for recent history."""
        cutoff_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_time = cutoff_time.replace(day=cutoff_time.day - days)

        recent_calls = [
            call for call in self.cost_history
            if datetime.fromisoformat(call["timestamp"]) >= cutoff_time
        ]

        breakdown = {}
        for call in recent_calls:
            service = call["service"]
            if service not in breakdown:
                breakdown[service] = {"calls": 0, "cost": 0.0, "tokens": 0}

            breakdown[service]["calls"] += 1
            breakdown[service]["cost"] += call["cost"]
            breakdown[service]["tokens"] += call["input_tokens"] + call["output_tokens"]

        return breakdown

    def _check_limits(self, date_str: str):
        """Check if we're approaching or exceeding limits."""
        current_cost = self.daily_costs[date_str]

        if current_cost >= self.daily_limit:
            print(f"WARNING: Daily cost limit exceeded! ${current_cost:.3f} >= ${self.daily_limit:.2f}")
        elif current_cost >= self.daily_limit * 0.8:
            print(f"WARNING: Approaching daily limit! ${current_cost:.3f} / ${self.daily_limit:.2f}")

    def get_status_summary(self) -> Dict:
        """Get current status summary for UI display."""
        today_cost = self.get_today_cost()
        remaining = self.get_remaining_budget()

        return {
            "today_cost": today_cost,
            "daily_limit": self.daily_limit,
            "remaining_budget": remaining,
            "percentage_used": (today_cost / self.daily_limit * 100) if self.daily_limit > 0 else 0,
            "can_continue": remaining > 0,
            "status": self._get_status_color(today_cost / self.daily_limit if self.daily_limit > 0 else 0)
        }

    def _get_status_color(self, percentage: float) -> str:
        """Get status color based on budget usage."""
        if percentage >= 1.0:
            return "red"
        elif percentage >= 0.8:
            return "orange"
        elif percentage >= 0.5:
            return "yellow"
        else:
            return "green"

    def format_cost(self, cost: float) -> str:
        """Format cost for display."""
        return f"${cost:.3f}"

    def export_report(self, filepath: str, days: int = 30) -> bool:
        """Export cost report to file."""
        try:
            cutoff_time = datetime.now().replace(day=datetime.now().day - days)

            recent_calls = [
                call for call in self.cost_history
                if datetime.fromisoformat(call["timestamp"]) >= cutoff_time
            ]

            report_data = {
                "report_generated": datetime.now().isoformat(),
                "period_days": days,
                "daily_limit": self.daily_limit,
                "summary": {
                    "total_calls": len(recent_calls),
                    "total_cost": sum(call["cost"] for call in recent_calls),
                    "total_tokens": sum(call["input_tokens"] + call["output_tokens"] for call in recent_calls)
                },
                "daily_costs": self.daily_costs,
                "service_breakdown": self.get_service_breakdown(days),
                "recent_calls": recent_calls
            }

            with open(filepath, 'w') as f:
                json.dump(report_data, f, indent=2)

            return True

        except Exception as e:
            print(f"Failed to export cost report: {e}")
            return False

    def __str__(self):
        """String representation of current cost status."""
        status = self.get_status_summary()
        return f"CostTracker(today=${status['today_cost']:.3f}, limit=${status['daily_limit']:.2f}, remaining=${status['remaining_budget']:.3f})"