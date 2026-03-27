"""Live agent activity feed widget."""

from __future__ import annotations

from collections import deque
from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import RichLog

MOOD_COLORS = {
    "focused": "cyan",
    "excited": "yellow",
    "confident": "green",
    "frustrated": "red",
    "curious": "magenta",
    "determined": "blue",
}

AGENT_COLORS = {
    "Marcus": "bright_green",
    "Aiden": "cyan",
    "Zara": "yellow",
    "Nova": "bright_blue",
    "Iris": "magenta",
    "Kai": "orange1",
    "Sage": "bright_cyan",
    "Rex": "bright_yellow",
    "Mia": "bright_magenta",
}


class AgentActivityFeed(Widget):
    """Scrolling log of agent messages and heartbeats."""

    DEFAULT_CSS = """
    AgentActivityFeed {
        border: solid $accent;
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="activity_log", wrap=True, markup=True, highlight=True)

    def log_message(self, from_agent: str, to_agent: str, content: str, message_type: str = "info") -> None:
        log = self.query_one("#activity_log", RichLog)
        ts = datetime.utcnow().strftime("%H:%M:%S")
        color = AGENT_COLORS.get(from_agent.split()[0], "white")

        type_icons = {
            "info": "📢",
            "task": "📋",
            "report": "📊",
            "directive": "⚡",
            "alert": "🚨",
        }
        icon = type_icons.get(message_type, "💬")

        log.write(
            f"[dim]{ts}[/dim] {icon} [bold {color}]{from_agent}[/bold {color}] → "
            f"[dim]{to_agent}[/dim]: {content[:120]}"
        )

    def log_heartbeat(self, pulse) -> None:
        log = self.query_one("#activity_log", RichLog)
        ts = pulse.timestamp.strftime("%H:%M:%S")
        color = AGENT_COLORS.get(pulse.agent_name, "white")
        mood_color = MOOD_COLORS.get(pulse.mood, "white")

        log.write(
            f"[dim]{ts}[/dim] 💓 [bold {color}]{pulse.agent_name}[/bold {color}] "
            f"[[{mood_color}]{pulse.mood}[/{mood_color}]] 💭 [italic]{pulse.inner_thought[:100]}[/italic]"
        )

    def log_event(self, event_type: str, message: str, department: str = "") -> None:
        log = self.query_one("#activity_log", RichLog)
        ts = datetime.utcnow().strftime("%H:%M:%S")
        dept_color = {
            "tiktok": "magenta",
            "youtube": "red",
            "website_seo": "blue",
            "dropshipping": "green",
        }.get(department, "white")

        icons = {
            "startup": "🚀",
            "cycle_start": "🔄",
            "cycle_complete": "✅",
            "site_deployed": "🌐",
            "content_created": "📝",
            "product_listed": "🛍️",
        }
        icon = icons.get(event_type, "📌")

        dept_tag = f"[{dept_color}][{department.upper()}][/{dept_color}] " if department else ""
        log.write(f"[dim]{ts}[/dim] {icon} {dept_tag}{message}")
