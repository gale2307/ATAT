"""Shared Socket.IO server instance."""
import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


async def emit_progress(job_id: str, progress: int, status: str):
    await sio.emit(
        "job:progress",
        {"jobId": job_id, "progress": progress, "status": status},
        room=f"job:{job_id}",
    )


async def emit_done(
    job_id: str,
    output_url: str | None = None,
    subtitle_url: str | None = None,
    srt_url: str | None = None,
    embed_url: str | None = None,
):
    await sio.emit(
        "job:done",
        {
            "jobId": job_id,
            "outputUrl": output_url,
            "subtitleUrl": subtitle_url,
            "srtUrl": srt_url,
            "embedUrl": embed_url,
        },
        room=f"job:{job_id}",
    )


async def emit_error(job_id: str, error: str):
    await sio.emit(
        "job:error",
        {"jobId": job_id, "error": error},
        room=f"job:{job_id}",
    )
