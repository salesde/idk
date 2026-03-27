#!/usr/bin/env python3
"""
NexGen AI Corp — Autonomous AI Company CLI

Usage:
    python main.py start              # Launch the full company (dashboard + agents)
    python main.py start --dry-run    # Run without real API calls (mock mode)
    python main.py research --dept tiktok  # Run research for one department
    python main.py status             # Show current company state
    python main.py dashboard          # Open dashboard without starting agents
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from pathlib import Path

import click

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("main")


def setup_file_logging(log_file: str) -> None:
    """Add file handler to root logger."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logging.getLogger().addHandler(file_handler)


@click.group()
def cli():
    """NexGen AI Corp — Autonomous AI Revenue Company"""
    pass


@cli.command()
@click.option("--dry-run", is_flag=True, default=False, help="Run without real API calls")
@click.option("--no-dashboard", is_flag=True, default=False, help="Run without terminal dashboard")
def start(dry_run: bool, no_dashboard: bool):
    """Start the autonomous AI company. Runs forever until stopped."""

    # Load settings
    from core.config import get_settings
    settings = get_settings()

    if dry_run:
        import os
        os.environ["DRY_RUN"] = "true"
        click.echo("🔶 DRY RUN MODE — no real API calls will be made")

    setup_file_logging(settings.log_file)

    click.echo(f"\n🏢 Starting {settings.company_name}")
    click.echo(f"   Mission: {settings.company_mission}")
    click.echo(f"   Models: Executive={settings.executive_model}, Research={settings.research_model}, Worker={settings.worker_model}")
    click.echo(f"   Cycle interval: {settings.cycle_interval_minutes} minutes")
    click.echo(f"   Dashboard: {'disabled' if no_dashboard else 'enabled'}")
    click.echo("\n   Press CTRL+C to stop\n")

    async def run_agents():
        """Run the company graph in the background."""
        from graphs.company_graph import run_company
        try:
            await run_company(dry_run=dry_run)
        except asyncio.CancelledError:
            logger.info("Company stopped.")
        except Exception as e:
            logger.error("Company crashed: %s", e, exc_info=True)

    if no_dashboard:
        # Simple asyncio run
        try:
            asyncio.run(run_agents())
        except KeyboardInterrupt:
            click.echo("\n👋 Company stopped.")
    else:
        # Run agents in a background thread, dashboard in the main thread
        from dashboard.app import AICompanyDashboard

        dashboard = AICompanyDashboard()

        def run_agent_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_agents())
            except Exception as e:
                logger.error("Agent loop error: %s", e)
            finally:
                loop.close()

        agent_thread = threading.Thread(target=run_agent_loop, daemon=True)
        agent_thread.start()

        try:
            dashboard.run()
        except KeyboardInterrupt:
            pass
        click.echo("\n👋 Dashboard closed. Agents stopping...")


@cli.command()
@click.option("--dept", default=None, help="Specific department to research (tiktok|youtube|website_seo|dropshipping)")
def research(dept: str | None):
    """Run the research pipeline for one or all departments."""

    from core.config import get_settings
    settings = get_settings()
    setup_file_logging(settings.log_file)

    departments = [dept] if dept else ["tiktok", "youtube", "website_seo", "dropshipping"]

    async def run():
        from graphs.research_graph import run_research
        from core.tools.file_manager import save_report
        import json

        for d in departments:
            click.echo(f"\n🔍 Researching {d}...")
            result = await run_research(d)
            confidence = result.get("confidence", 0)
            approved = result.get("approved", False)
            strategy = result.get("strategy", {})

            click.echo(f"   ✅ Done | Confidence: {confidence:.0%} | Approved: {approved}")
            if strategy:
                est = strategy.get("estimated_monthly_revenue_usd", 0)
                click.echo(f"   Est. monthly revenue: ${est:,.0f}")
                click.echo(f"   Trend: {strategy.get('trend_direction', 'unknown')}")

            # Save report
            report_content = f"# Research Report: {d}\n\n"
            report_content += f"**Confidence:** {confidence:.0%}\n"
            report_content += f"**Approved:** {approved}\n\n"
            report_content += f"## Analysis\n\n{result.get('analysis', 'N/A')}\n\n"
            report_content += f"## Strategy\n\n```json\n{json.dumps(strategy, indent=2, default=str)}\n```\n"
            path = save_report(f"research_{d}", report_content, department=d)
            click.echo(f"   Report saved: {path}")

    asyncio.run(run())


@cli.command()
def status():
    """Show the current company database status."""

    async def run():
        from db.database import get_session
        from db.models import AgentRecord, ContentItem, RevenueRecord, TaskRecord
        from sqlalchemy import func, select

        try:
            async with get_session() as session:
                agent_count = (await session.execute(select(func.count()).select_from(AgentRecord))).scalar()
                task_count = (await session.execute(select(func.count()).select_from(TaskRecord))).scalar()
                content_count = (await session.execute(select(func.count()).select_from(ContentItem))).scalar()
                revenue_total = (await session.execute(select(func.sum(RevenueRecord.estimated_value_usd)))).scalar() or 0.0

                click.echo("\n📊 Company Status")
                click.echo(f"   Agents registered: {agent_count}")
                click.echo(f"   Tasks recorded:    {task_count}")
                click.echo(f"   Content items:     {content_count}")
                click.echo(f"   Total est. revenue: ${revenue_total:.2f}")
        except Exception as e:
            click.echo(f"   ❌ Could not read DB: {e}")
            click.echo("   (Run 'python main.py start' first to initialize)")

    asyncio.run(run())


@cli.command()
def dashboard():
    """Open the dashboard without starting agents (view-only mode)."""
    from dashboard.app import AICompanyDashboard
    AICompanyDashboard().run()


if __name__ == "__main__":
    cli()
