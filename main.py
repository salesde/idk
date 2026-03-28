#!/usr/bin/env python3
"""
NexGen AI Corp — Autonomous AI Company
Opens a browser dashboard. No terminal knowledge needed.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import webbrowser
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("main")


def setup_file_logging(log_file: str) -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(fh)
    logging.getLogger().setLevel(logging.INFO)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """NexGen AI Corp — just run this and the browser opens."""
    if ctx.invoked_subcommand is None:
        # Default: run the web UI
        ctx.invoke(start)


@cli.command()
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--port", default=8080, help="Web server port")
def start(dry_run: bool, port: int):
    """Start the company — opens dashboard in your browser."""

    from core.config import get_settings
    settings = get_settings()

    if dry_run:
        os.environ["DRY_RUN"] = "true"

    setup_file_logging(settings.log_file)

    # Initialise DB directory
    Path("output").mkdir(exist_ok=True)

    print(f"\n🏢  {settings.company_name}")
    print(f"    Starting on http://localhost:{port}")
    print(f"    Opening your browser...\n")
    print("    Press CTRL+C to stop.\n")

    async def run():
        # Init DB
        from db.database import init_db
        await init_db()

        # Check if keys are set; if not open setup page
        keys_ok = (
            bool(settings.anthropic_api_key) and
            bool(settings.google_api_key) and
            bool(settings.tavily_api_key)
        )

        url = f"http://localhost:{port}"
        open_url = f"{url}/setup" if not keys_ok else url

        # Open browser after short delay so server is ready
        async def open_browser():
            await asyncio.sleep(1.5)
            webbrowser.open(open_url)

        asyncio.create_task(open_browser())

        if keys_ok and not dry_run:
            # Run web server + agents in parallel
            from web.app import start_web_server
            from graphs.company_graph import run_company
            await asyncio.gather(
                start_web_server(port=port),
                run_company(dry_run=False),
            )
        else:
            # Just serve the web UI (setup page or dry-run dashboard)
            from web.app import start_web_server
            await start_web_server(port=port)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n👋 Stopped.")


@cli.command()
@click.option("--dept", default=None)
def research(dept: str | None):
    """Run research for a department and save the report."""
    from core.config import get_settings
    setup_file_logging(get_settings().log_file)

    async def run():
        from graphs.research_graph import run_research
        from core.tools.file_manager import save_report
        import json

        depts = [dept] if dept else ["tiktok", "youtube", "website_seo", "dropshipping"]
        for d in depts:
            print(f"\n🔍 Researching {d}...")
            result = await run_research(d)
            confidence = result.get("confidence", 0)
            approved = result.get("approved", False)
            strategy = result.get("strategy", {})
            print(f"   ✅ Confidence: {confidence:.0%} | Approved: {approved}")
            if strategy:
                print(f"   Est. monthly: ${strategy.get('estimated_monthly_revenue_usd', 0):,.0f}")
            content = f"# Research: {d}\n\nConfidence: {confidence:.0%}\n\n{result.get('analysis','')}\n\n```json\n{json.dumps(strategy, indent=2, default=str)}\n```"
            path = save_report(f"research_{d}", content, department=d)
            print(f"   Saved: {path}")

    asyncio.run(run())


@cli.command()
def status():
    """Print current company stats."""
    async def run():
        from db.database import get_session
        from db.models import ContentItem, RevenueRecord, TaskRecord
        from sqlalchemy import func, select
        try:
            async with get_session() as s:
                tasks = (await s.execute(select(func.count()).select_from(TaskRecord))).scalar()
                content = (await s.execute(select(func.count()).select_from(ContentItem))).scalar()
                revenue = (await s.execute(select(func.sum(RevenueRecord.estimated_value_usd)))).scalar() or 0.0
            print(f"\n📊 Company Status")
            print(f"   Tasks: {tasks}  |  Content: {content}  |  Revenue: ${revenue:.2f}")
        except Exception as e:
            print(f"   No data yet. Start the company first.")

    asyncio.run(run())


if __name__ == "__main__":
    cli()
