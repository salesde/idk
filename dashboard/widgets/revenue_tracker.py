"""Revenue and output tracker widget."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Label, RichLog


class RevenueTracker(Widget):
    """Displays revenue events and estimated earnings per department."""

    DEFAULT_CSS = """
    RevenueTracker {
        border: solid $success;
        height: 1fr;
        padding: 0 1;
    }
    RevenueTracker Label {
        color: $success;
        text-style: bold;
        padding: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("💰 Revenue Tracker")
        yield DataTable(id="revenue_table")
        yield RichLog(id="revenue_log", wrap=True)

    def on_mount(self) -> None:
        table = self.query_one("#revenue_table", DataTable)
        table.add_columns("Dept", "Type", "Value", "Time")
        table.cursor_type = "none"

    def add_event(self, event: dict) -> None:
        table = self.query_one("#revenue_table", DataTable)
        log = self.query_one("#revenue_log", RichLog)

        dept = event.get("department", "?")
        event_type = event.get("event_type", "?")
        value = event.get("estimated_value_usd", 0.0)
        ts = datetime.utcnow().strftime("%H:%M")

        dept_colors = {
            "tiktok": "magenta",
            "youtube": "red",
            "website_seo": "blue",
            "dropshipping": "green",
        }
        color = dept_colors.get(dept, "white")

        table.add_row(
            f"[{color}]{dept[:8]}[/{color}]",
            event_type[:12],
            f"[green]${value:.2f}[/green]",
            ts,
        )

        log.write(f"[dim]{ts}[/dim] [green]+${value:.2f}[/green] [{color}]{dept}[/{color}] — {event.get('description', '')[:60]}")

    def update_totals(self, by_department: dict[str, float]) -> None:
        log = self.query_one("#revenue_log", RichLog)
        total = sum(by_department.values())
        summary = " | ".join(f"{k}: ${v:.2f}" for k, v in by_department.items())
        log.write(f"\n[bold green]TOTAL: ${total:.2f}[/bold green] | {summary}\n")
