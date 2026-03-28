"""FastAPI web server — serves the browser dashboard and WebSocket feed."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.config import get_settings
from core.message_bus import get_bus

logger = logging.getLogger(__name__)

# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()

# ── Agent registry for user chat ─────────────────────────────────────────────

AGENT_REGISTRY: dict[str, Any] = {}


def _init_agent_registry() -> None:
    """Create one BaseAgent instance per agent soul for user chat."""
    global AGENT_REGISTRY
    from core.base_agent import BaseAgent
    from core.soul import get_soul
    from core.config import get_settings
    from agents.executives.ceo import CEO
    from agents.executives.cto import CTO
    from agents.executives.cmo import CMO
    from agents.executives.cfo import CFO

    settings = get_settings()
    try:
        AGENT_REGISTRY = {
            "Marcus": CEO(),
            "Aiden":  CTO(),
            "Zara":   CMO(),
            "Nova":   CFO(),
            "Iris":   BaseAgent(soul=get_soul("researcher"),    model=settings.research_model),
            "Kai":    BaseAgent(soul=get_soul("tiktok_head"),   model=settings.worker_model),
            "Sage":   BaseAgent(soul=get_soul("youtube_head"),  model=settings.worker_model),
            "Rex":    BaseAgent(soul=get_soul("seo_head"),      model=settings.worker_model),
            "Mia":    BaseAgent(soul=get_soul("dropship_head"), model=settings.worker_model),
        }
        logger.info("Agent registry initialised with %d agents", len(AGENT_REGISTRY))
    except Exception as e:
        logger.error("Failed to initialise agent registry: %s", e)


async def handle_user_message(to: str, message: str) -> None:
    """Route a user message to the chosen agent(s) and broadcast their replies."""
    entry = push_feed("👤", "YOU", f"→ {to}: {message[:120]}", "blue")
    await manager.broadcast({"type": "feed", "data": entry})

    targets = list(AGENT_REGISTRY.items()) if to == "ALL" else (
        [(to, AGENT_REGISTRY[to])] if to in AGENT_REGISTRY else []
    )

    context = (
        "The user (your operator/owner) is speaking to you directly via the dashboard. "
        "Stay fully in character and respond concisely."
    )
    for name, agent in targets:
        try:
            response = await agent.think(message, context=context)
            text = response.text.strip()
            entry = push_feed("💬", name, text[:400], "cyan")
            await manager.broadcast({"type": "feed", "data": entry})
        except Exception as e:
            logger.error("Agent %s failed to respond: %s", name, e)
            entry = push_feed("⚠️", name, f"[{type(e).__name__}: unavailable]", "red")
            await manager.broadcast({"type": "feed", "data": entry})


# ── State tracking ────────────────────────────────────────────────────────────

company_state: dict[str, Any] = {
    "phase": "offline",
    "cycle": 0,
    "total_revenue": 0.0,
    "output_count": 0,
    "active_departments": [],
    "start_time": None,
    "departments": {
        "tiktok":       {"status": "pending", "cycle": 0, "outputs": 0, "last": "—"},
        "youtube":      {"status": "pending", "cycle": 0, "outputs": 0, "last": "—"},
        "website_seo":  {"status": "pending", "cycle": 0, "outputs": 0, "last": "—"},
        "dropshipping": {"status": "pending", "cycle": 0, "outputs": 0, "last": "—"},
    },
    "feed": [],          # last 200 activity messages
    "revenue_events": [], # last 100 revenue events
}


def push_feed(icon: str, agent: str, msg: str, color: str = "white"):
    entry = {
        "ts": datetime.utcnow().strftime("%H:%M:%S"),
        "icon": icon,
        "agent": agent,
        "msg": msg,
        "color": color,
    }
    company_state["feed"].insert(0, entry)
    company_state["feed"] = company_state["feed"][:200]
    return entry


# ── FastAPI app ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire up message bus subscriptions on startup."""
    bus = get_bus()

    async def on_agent_msg(msg):
        entry = push_feed("📨", msg.from_agent, f"→ {msg.to_agent}: {msg.content[:120]}", "cyan")
        await manager.broadcast({"type": "feed", "data": entry})

    async def on_heartbeat(pulse):
        entry = push_feed("💓", pulse.agent_name, f"[{pulse.mood}] {pulse.inner_thought[:100]}", "green")
        await manager.broadcast({"type": "feed", "data": entry})
        await manager.broadcast({"type": "heartbeat", "data": {
            "agent": pulse.agent_name,
            "role": pulse.role,
            "mood": pulse.mood,
            "thought": pulse.inner_thought,
            "ts": pulse.timestamp.strftime("%H:%M:%S"),
        }})

    async def on_revenue(event: dict):
        company_state["total_revenue"] += event.get("estimated_value_usd", 0)
        company_state["output_count"] += 1
        company_state["revenue_events"].insert(0, {
            **event,
            "ts": datetime.utcnow().strftime("%H:%M:%S"),
        })
        company_state["revenue_events"] = company_state["revenue_events"][:100]
        entry = push_feed("💰", event.get("department", "?").upper(),
                          f"+${event.get('estimated_value_usd', 0):.2f} — {event.get('description', '')[:80]}", "yellow")
        await manager.broadcast({"type": "revenue", "data": {
            "event": event,
            "total": company_state["total_revenue"],
            "feed": entry,
        }})

    async def on_company_event(event: dict):
        etype = event.get("type", "")
        if etype == "startup":
            company_state["phase"] = "starting"
            company_state["start_time"] = datetime.utcnow().isoformat()
            entry = push_feed("🚀", "SYSTEM", f"{event.get('company')} is online!", "green")
        elif etype == "cycle_start":
            company_state["active_departments"] = event.get("departments", [])
            company_state["phase"] = "active"
            entry = push_feed("🔄", "SYSTEM", f"Cycle started — {', '.join(event.get('departments', []))}", "blue")
        elif etype == "cycle_complete":
            company_state["cycle"] = event.get("cycle", 0)
            entry = push_feed("✅", "SYSTEM", f"Cycle #{event.get('cycle')} complete", "green")
        else:
            entry = push_feed("📌", "SYSTEM", str(event), "white")
        await manager.broadcast({"type": "company_event", "data": {**event, "state": company_state}})

    async def on_output(event: dict):
        dept = event.get("department", "")
        output = event.get("output", {})
        if dept in company_state["departments"]:
            ds = company_state["departments"][dept]
            ds["outputs"] += 1
            ds["status"] = "working"
            ds["last"] = output.get("title", "—")
        entry = push_feed("📝", dept.upper(), f"Output: {output.get('title', '—')[:80]}", "magenta")
        await manager.broadcast({"type": "output", "data": {"dept": dept, "output": output, "feed": entry}})

    bus.subscribe("agent.all", on_agent_msg)
    bus.subscribe("heartbeat", on_heartbeat)
    bus.subscribe("revenue_event", on_revenue)
    bus.subscribe("company_event", on_company_event)
    bus.subscribe("output_ready", on_output)

    _init_agent_registry()

    yield


app = FastAPI(title="NexGen AI Corp", lifespan=lifespan)

# Serve static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return (Path(__file__).parent / "static" / "index.html").read_text()


@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    return (Path(__file__).parent / "static" / "setup.html").read_text()


@app.get("/api/state")
async def get_state():
    settings = get_settings()
    return JSONResponse({
        **company_state,
        "company_name": settings.company_name,
        "uptime": _uptime(),
    })


@app.post("/api/keys")
async def save_keys(body: dict):
    """Save API keys to .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(Path(".env.example").read_text())

    lines = env_path.read_text().splitlines()
    updated = {k: v for k, v in body.items() if v}

    new_lines = []
    replaced = set()
    for line in lines:
        found = False
        for key, val in updated.items():
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                new_lines.append(f"{key}={val}")
                replaced.add(key)
                found = True
                break
        if not found:
            new_lines.append(line)

    for key, val in updated.items():
        if key not in replaced:
            new_lines.append(f"{key}={val}")

    env_path.write_text("\n".join(new_lines) + "\n")
    return JSONResponse({"ok": True, "saved": list(updated.keys())})


@app.get("/api/check-keys")
async def check_keys():
    """Check which API keys are configured."""
    settings = get_settings()
    return JSONResponse({
        "anthropic": bool(settings.anthropic_api_key),
        "google": bool(settings.google_api_key),
        "tavily": bool(settings.tavily_api_key),
        "tiktok": bool(settings.tiktok_access_token),
        "youtube": bool(settings.youtube_refresh_token),
        "netlify": bool(settings.netlify_auth_token),
        "shopify": bool(settings.shopify_access_token),
    })


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send current state immediately on connect
    settings = get_settings()
    await ws.send_json({"type": "init", "data": {
        **company_state,
        "company_name": settings.company_name,
        "uptime": _uptime(),
    }})
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "user_msg":
                    to = msg.get("to", "Marcus")
                    message = msg.get("message", "").strip()
                    if message:
                        asyncio.create_task(handle_user_message(to, message))
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        manager.disconnect(ws)


def _uptime() -> str:
    start = company_state.get("start_time")
    if not start:
        return "—"
    delta = datetime.utcnow() - datetime.fromisoformat(start)
    h, r = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


async def start_web_server(host: str = "127.0.0.1", port: int = 8080):
    """Start the uvicorn server."""
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
