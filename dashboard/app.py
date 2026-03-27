"""NexGen AI Corp — Textual terminal dashboard."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Label, Static

from core.config import get_settings
from core.message_bus import get_bus
from dashboard.widgets.agent_status import AgentActivityFeed
from dashboard.widgets.department_panel import DepartmentPanel
from dashboard.widgets.revenue_tracker import RevenueTracker


class CompanyStats(Static):
    DEFAULT_CSS = """
    CompanyStats {
        background: $panel;
        padding: 1 2;
        height: 5;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._start_time = datetime.now(timezone.utc)
        self._cycle = 0
        self._output_count = 0
        self._revenue_total = 0.0
        self._active_depts = []

    def compose(self) -> ComposeResult:
        settings = get_settings()
        yield Label(f"[bold bright_green]🏢 {settings.company_name}[/bold bright_green]", id="company_name")
        yield Label("Uptime: 0:00:00 | Cycle: 0 | Outputs: 0 | Revenue: $0.00 | Depts: —", id="stats_line")

    def update_stats(self, cycle: int = 0, outputs: int = 0, revenue: float = 0.0, depts: list[str] | None = None) -> None:
        self._cycle = cycle
        self._output_count = outputs
        self._revenue_total = revenue
        self._active_depts = depts or []

        elapsed = datetime.now(timezone.utc) - self._start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        depts_str = ", ".join(self._active_depts) if self._active_depts else "none"
        try:
            self.query_one("#stats_line", Label).update(
                f"Uptime: [cyan]{uptime}[/cyan] | "
                f"Cycle: [yellow]{cycle}[/yellow] | "
                f"Outputs: [bright_white]{outputs}[/bright_white] | "
                f"Revenue: [green]${revenue:.2f}[/green] | "
                f"Depts: [magenta]{depts_str}[/magenta]"
            )
        except Exception:
            pass


class AICompanyDashboard(App):
    """Main Textual dashboard for the AI company."""

    TITLE = "NexGen AI Corp — Live Dashboard"
    CSS = """
    Screen {
        layout: vertical;
    }
    #main_area {
        layout: horizontal;
        height: 1fr;
    }
    #left_col {
        width: 2fr;
        height: 1fr;
    }
    #right_col {
        width: 1fr;
        height: 1fr;
    }
    #bottom_row {
        layout: horizontal;
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "pause", "Pause/Resume"),
        Binding("r", "force_research", "Force Research"),
        Binding("s", "status", "Status"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bus = get_bus()
        self._total_revenue = 0.0
        self._output_count = 0
        self._dept_states: dict[str, dict] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield CompanyStats(id="stats")
        with Horizontal(id="main_area"):
            with Vertical(id="left_col"):
                yield AgentActivityFeed(id="activity_feed")
            with Vertical(id="right_col"):
                yield DepartmentPanel(id="dept_panel")
        yield RevenueTracker(id="revenue_tracker")
        yield Footer()

    async def on_mount(self) -> None:
        """Wire up message bus subscriptions."""
        stats = self.query_one("#stats", CompanyStats)

        async def on_message(msg):
            try:
                feed = self.query_one("#activity_feed", AgentActivityFeed)
                feed.log_message(msg.from_agent, msg.to_agent, msg.content, msg.message_type)
            except Exception:
                pass

        async def on_heartbeat(pulse):
            try:
                feed = self.query_one("#activity_feed", AgentActivityFeed)
                feed.log_heartbeat(pulse)
            except Exception:
                pass

        async def on_revenue_event(event: dict):
            try:
                tracker = self.query_one("#revenue_tracker", RevenueTracker)
                tracker.add_event(event)
                self._total_revenue += event.get("estimated_value_usd", 0.0)
                self._output_count += 1
                stats.update_stats(revenue=self._total_revenue, outputs=self._output_count)
            except Exception:
                pass

        async def on_company_event(event: dict):
            try:
                feed = self.query_one("#activity_feed", AgentActivityFeed)
                event_type = event.get("type", "")
                if event_type == "startup":
                    feed.log_event("startup", f"{event.get('company')} is online!")
                elif event_type == "cycle_complete":
                    feed.log_event("cycle_complete",
                        f"Cycle #{event.get('cycle')} complete | "
                        f"{event.get('revenue_events', 0)} revenue events")
                    stats.update_stats(cycle=event.get("cycle", 0))
                elif event_type == "cycle_start":
                    depts = event.get("departments", [])
                    feed.log_event("cycle_start", f"Departments active: {', '.join(depts)}")
                    stats.update_stats(depts=depts)
            except Exception:
                pass

        async def on_output_ready(event: dict):
            try:
                panel = self.query_one("#dept_panel", DepartmentPanel)
                dept = event.get("department", "")
                output = event.get("output", {})
                if dept not in self._dept_states:
                    self._dept_states[dept] = {"cycle": 0, "outputs": 0}
                self._dept_states[dept]["outputs"] += 1
                panel.update_department(
                    dept,
                    status="working",
                    cycle=self._dept_states[dept]["cycle"],
                    output_count=self._dept_states[dept]["outputs"],
                    last_output=output.get("title", "—"),
                )
            except Exception:
                pass

        self.bus.subscribe("agent.all", on_message)
        self.bus.subscribe("heartbeat", on_heartbeat)
        self.bus.subscribe("revenue_event", on_revenue_event)
        self.bus.subscribe("company_event", on_company_event)
        self.bus.subscribe("output_ready", on_output_ready)

        # Uptime ticker
        self.set_interval(1.0, self._tick_uptime)

    def _tick_uptime(self) -> None:
        stats = self.query_one("#stats", CompanyStats)
        stats.update_stats(
            cycle=stats._cycle,
            outputs=stats._output_count,
            revenue=self._total_revenue,
            depts=stats._active_depts,
        )

    def action_pause(self) -> None:
        feed = self.query_one("#activity_feed", AgentActivityFeed)
        feed.log_event("pause", "Company PAUSED by user. Resume with P.")

    def action_force_research(self) -> None:
        feed = self.query_one("#activity_feed", AgentActivityFeed)
        feed.log_event("research", "Forcing new research cycle...")

    def action_status(self) -> None:
        tracker = self.query_one("#revenue_tracker", RevenueTracker)
        dept_totals = {dept: state.get("revenue", 0) for dept, state in self._dept_states.items()}
        tracker.update_totals(dept_totals)
