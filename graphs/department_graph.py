"""Department execution graph — runs the content/work loop for one department."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from core.message_bus import get_bus
from core.state import DepartmentState

logger = logging.getLogger(__name__)


async def _run_tiktok_cycle(state: DepartmentState) -> DepartmentState:
    """One TikTok content cycle: find trends, create content, schedule posts."""
    from agents.departments.tiktok.trend_monitor import TikTokTrendMonitor
    from agents.departments.tiktok.content_creator import TikTokContentCreator
    from agents.departments.tiktok.posting_manager import TikTokPostingManager

    monitor = TikTokTrendMonitor()
    creator = TikTokContentCreator()
    poster = TikTokPostingManager()

    # Find trends
    trends = await monitor.get_trending_topics()
    top_trend = trends[0] if trends else {"topic": "AI character story", "format": "drama", "hashtags": []}

    # Generate content batch
    outputs = await creator.create_content_batch(state.get("strategy", {}), batch_size=3)

    # Schedule posts
    scheduled = poster.schedule_posts(outputs, posts_per_day=3)

    revenue_events = []
    for output in outputs:
        revenue_events.append({
            "department": "tiktok",
            "event_type": "content_created",
            "description": f"Script: {output.get('title', 'Unknown')}",
            "estimated_value_usd": 0.50,  # Estimated value of one content piece
        })

    bus = get_bus()
    await bus.send("Kai (TikTok)", "ALL", f"Created {len(outputs)} TikTok scripts. Scheduled {len(scheduled)} posts.", message_type="report")

    completed_outputs = list(state.get("completed_outputs", [])) + outputs
    all_revenue_events = list(state.get("revenue_events", [])) + revenue_events

    return {
        **state,
        "completed_outputs": completed_outputs,
        "revenue_events": all_revenue_events,
        "current_task": None,
        "status": "idle",
        "cycle_count": state.get("cycle_count", 0) + 1,
    }


async def _run_youtube_cycle(state: DepartmentState) -> DepartmentState:
    """One YouTube content cycle: research, write scripts, schedule."""
    from agents.departments.youtube.trend_researcher import YouTubeTrendResearcher
    from agents.departments.youtube.script_writer import YouTubeScriptWriter
    from agents.departments.youtube.channel_manager import YouTubeChannelManager

    researcher = YouTubeTrendResearcher()
    writer = YouTubeScriptWriter()
    manager = YouTubeChannelManager()

    # Find opportunities
    opportunities = await researcher.find_video_opportunities()
    top_opp = opportunities[0] if opportunities else {"niche": "general knowledge", "keywords": [], "monthly_searches": 0}

    # Write 2 shorts + 1 longform
    outputs = []
    for _ in range(2):
        short = await writer.write_shorts_script(top_opp)
        outputs.append(short)

    longform = await writer.write_longform_script(top_opp)
    outputs.append(longform)

    # Schedule
    schedule = manager.generate_upload_schedule(outputs, shorts_per_day=2, longform_per_week=3)

    revenue_events = [{
        "department": "youtube",
        "event_type": "script_created",
        "description": f"Scripts: {len(outputs)} created for {top_opp.get('niche', 'general')}",
        "estimated_value_usd": 1.00,
    }]

    bus = get_bus()
    await bus.send("Sage (YouTube)", "ALL", f"Produced {len(outputs)} YouTube scripts. {len(schedule)} scheduled.", message_type="report")

    return {
        **state,
        "completed_outputs": list(state.get("completed_outputs", [])) + outputs,
        "revenue_events": list(state.get("revenue_events", [])) + revenue_events,
        "current_task": None,
        "status": "idle",
        "cycle_count": state.get("cycle_count", 0) + 1,
    }


async def _run_seo_cycle(state: DepartmentState) -> DepartmentState:
    """One SEO cycle: research keywords, write articles, build site, deploy."""
    from agents.departments.website_seo.keyword_researcher import KeywordResearcher
    from agents.departments.website_seo.content_writer import SEOContentWriter
    from agents.departments.website_seo.site_builder import SiteBuilder
    from agents.departments.website_seo.deploy_manager import NetlifyDeployManager

    researcher = KeywordResearcher()
    writer = SEOContentWriter()
    builder = SiteBuilder()
    deployer = NetlifyDeployManager()

    # Research
    clusters = await researcher.find_keyword_opportunities()
    top_cluster = clusters[0] if clusters else {"seed_keyword": "best products", "cluster_theme": "product reviews"}

    # Write articles
    articles = await writer.write_article_batch(top_cluster, count=3)

    # Build site
    site = await builder.build_niche_site(top_cluster, articles)

    # Deploy
    deploy_result = await deployer.deploy_site(site)
    site_url = deploy_result.get("url", "localhost")

    revenue_events = [{
        "department": "website_seo",
        "event_type": "site_deployed",
        "description": f"Site '{site.get('site_name')}' deployed to {site_url} with {len(articles)} articles",
        "estimated_value_usd": 5.00,   # Conservative initial value
        "metadata": {"url": site_url},
    }]

    bus = get_bus()
    await bus.send("Rex (SEO)", "ALL", f"Site deployed: {site_url} | {len(articles)} articles published.", message_type="report")

    return {
        **state,
        "completed_outputs": list(state.get("completed_outputs", [])) + articles + [site],
        "revenue_events": list(state.get("revenue_events", [])) + revenue_events,
        "status": "idle",
        "cycle_count": state.get("cycle_count", 0) + 1,
    }


async def _run_dropshipping_cycle(state: DepartmentState) -> DepartmentState:
    """One dropshipping cycle: find products, create content, list in store."""
    from agents.departments.dropshipping.product_researcher import ProductResearcher
    from agents.departments.dropshipping.ad_copy_writer import AdCopyWriter
    from agents.departments.dropshipping.store_manager import ShopifyStoreManager
    from agents.departments.dropshipping.pricing_agent import PricingAgent

    researcher = ProductResearcher()
    writer = AdCopyWriter()
    store = ShopifyStoreManager()
    pricer = PricingAgent()

    # Research products
    products = await researcher.find_winning_products()
    top_products = products[:2]  # Work on top 2 per cycle

    outputs = []
    revenue_events = []

    for product in top_products:
        # Optimize pricing
        pricing = pricer.calculate_margins(product)
        if not pricing.get("viable", False):
            continue

        # Write ad copy
        ugc_script = await writer.create_ugc_tiktok_script(product)
        description = await writer.write_product_description(product)

        # List in store
        store_result = await store.create_product(product, description)

        outputs.append(ugc_script)
        revenue_events.append({
            "department": "dropshipping",
            "event_type": "product_listed",
            "description": f"Listed: {product.get('name')} at ${product.get('recommended_price_usd')} (margin: {pricing.get('margin_percent')}%)",
            "estimated_value_usd": pricing.get("gross_profit_usd", 0) * 0.1,  # Conservative: 0.1 sales estimate
            "metadata": {"product_id": store_result.get("product_id"), "margin": pricing.get("margin_percent")},
        })

    bus = get_bus()
    await bus.send("Mia (Dropship)", "ALL", f"Listed {len(top_products)} products. {len(outputs)} UGC scripts created.", message_type="report")

    return {
        **state,
        "completed_outputs": list(state.get("completed_outputs", [])) + outputs,
        "revenue_events": list(state.get("revenue_events", [])) + revenue_events,
        "status": "idle",
        "cycle_count": state.get("cycle_count", 0) + 1,
    }


DEPARTMENT_RUNNERS = {
    "tiktok": _run_tiktok_cycle,
    "youtube": _run_youtube_cycle,
    "website_seo": _run_seo_cycle,
    "dropshipping": _run_dropshipping_cycle,
}


def build_department_graph(department: str):
    """Build the execution loop graph for a specific department."""

    runner = DEPARTMENT_RUNNERS.get(department)
    if not runner:
        raise ValueError(f"Unknown department: {department}")

    async def select_task(state: DepartmentState) -> DepartmentState:
        return {**state, "status": "working", "current_task": {"description": f"Run {department} cycle"}}

    async def execute(state: DepartmentState) -> DepartmentState:
        logger.info("Running %s department cycle #%d", department, state.get("cycle_count", 0) + 1)
        return await runner(state)

    async def report(state: DepartmentState) -> DepartmentState:
        count = len(state.get("completed_outputs", []))
        logger.info("%s cycle complete. Total outputs: %d", department, count)
        return state

    workflow = StateGraph(DepartmentState)
    workflow.add_node("select_task", select_task)
    workflow.add_node("execute", execute)
    workflow.add_node("report", report)

    workflow.add_edge(START, "select_task")
    workflow.add_edge("select_task", "execute")
    workflow.add_edge("execute", "report")
    workflow.add_edge("report", END)

    return workflow.compile()


async def run_department_cycle(department: str, strategy: dict) -> DepartmentState:
    """Run one full department cycle."""
    initial: DepartmentState = {
        "department_name": department,
        "soul_key": f"{department}_head",
        "task_queue": [],
        "current_task": None,
        "completed_outputs": [],
        "revenue_events": [],
        "status": "idle",
        "cycle_count": 0,
        "strategy": strategy,
        "error": None,
    }
    graph = build_department_graph(department)
    return await graph.ainvoke(initial)
