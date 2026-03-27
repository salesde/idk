"""Department status grid widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static


DEPT_CONFIG = {
    "tiktok": {"icon": "🎵", "color": "magenta", "head": "Kai"},
    "youtube": {"icon": "▶️", "color": "red", "head": "Sage"},
    "website_seo": {"icon": "🌐", "color": "blue", "head": "Rex"},
    "dropshipping": {"icon": "🛍️", "color": "green", "head": "Mia"},
}

STATUS_ICONS = {
    "idle": "💤",
    "working": "⚙️",
    "blocked": "🚫",
    "stopped": "⛔",
    "pending": "⏳",
}


class DepartmentCard(Static):
    DEFAULT_CSS = """
    DepartmentCard {
        border: solid $panel;
        padding: 1;
        margin: 0 0 1 0;
        height: auto;
    }
    """

    def __init__(self, department: str, **kwargs):
        super().__init__(**kwargs)
        self.department = department
        self._status = "pending"
        self._task_count = 0
        self._output_count = 0
        self._last_output = "—"
        self._cycle = 0

    def compose(self) -> ComposeResult:
        cfg = DEPT_CONFIG.get(self.department, {"icon": "📦", "color": "white", "head": "?"})
        color = cfg["color"]
        icon = cfg["icon"]
        head = cfg["head"]
        dept_display = self.department.replace("_", " ").title()

        yield Label(
            f"{icon} [{color}]{dept_display}[/{color}] (Head: {head})",
            id=f"{self.department}_title",
        )
        yield Label(f"Status: ⏳ pending | Cycle: 0 | Outputs: 0", id=f"{self.department}_status")
        yield Label(f"Last: —", id=f"{self.department}_last")

    def update_status(self, status: str, cycle: int, output_count: int, last_output: str = "—") -> None:
        self._status = status
        self._cycle = cycle
        self._output_count = output_count
        self._last_output = last_output

        status_icon = STATUS_ICONS.get(status, "❓")
        try:
            self.query_one(f"#{self.department}_status", Label).update(
                f"Status: {status_icon} {status} | Cycle: {cycle} | Outputs: {output_count}"
            )
            self.query_one(f"#{self.department}_last", Label).update(
                f"Last: {last_output[:60]}"
            )
        except Exception:
            pass


class DepartmentPanel(Widget):
    """Shows status cards for all departments."""

    DEFAULT_CSS = """
    DepartmentPanel {
        border: solid $accent;
        height: 1fr;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[bold]Department Status[/bold]")
        for dept in DEPT_CONFIG:
            yield DepartmentCard(dept, id=f"card_{dept}")

    def update_department(self, department: str, status: str, cycle: int, output_count: int, last_output: str = "—") -> None:
        try:
            card = self.query_one(f"#card_{department}", DepartmentCard)
            card.update_status(status, cycle, output_count, last_output)
        except Exception:
            pass
