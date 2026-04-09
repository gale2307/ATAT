import logging
import socketio
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
# logging.getLogger("app.services.translator").setLevel(logging.DEBUG)  
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.models.database import create_db_and_tables
from app.routers import domains, jobs, models
from app.socket import sio

# FastAPI app
app = FastAPI(title="ATAT API", debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(models.router)
app.include_router(domains.router)

# Serve generated files (subtitles, output video) as static files
storage = Path(settings.storage_path)
storage.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(storage)), name="files")

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()


@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")


@sio.event
async def subscribe(sid, data):
    job_id = data.get("jobId")
    if job_id:
        await sio.enter_room(sid, f"job:{job_id}")
