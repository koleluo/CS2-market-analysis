"""FastAPI web UI + REST API server.

Start: python main.py --serve-only
       or: uvicorn server:app --reload
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

_root = Path(__file__).parent
load_dotenv(_root / ".env")

from api.routes import router

app = FastAPI(title="CS2 Skin Tracker", version="1.0.0")
app.include_router(router)

_static = _root / "webui" / "static"
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

_index = _root / "webui" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index():
    if _index.exists():
        return HTMLResponse(_index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>CS2 Skin Tracker</h1><p>WebUI not found.</p>")
