import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.database import get_session
from app.models.job import Job, JobStatus
from app.pipeline import run_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])

SessionDep = Annotated[Session, Depends(get_session)]


class JobCreate(BaseModel):
    url: str
    stt_model: str = "whisper-large-v3"
    translation_engine: str = "qwen-mt"
    domain: str = "general"
    src_lang: str = "ko"
    tgt_lang: str = "en"
    download_mode: str = "audio_only"


class JobResponse(BaseModel):
    jobId: str
    status: str
    progress: int
    outputUrl: str | None
    subtitleUrl: str | None
    srtUrl: str | None
    embedUrl: str | None
    error: str | None


@router.post("", response_model=JobResponse)
async def create_job(payload: JobCreate, background_tasks: BackgroundTasks, session: SessionDep):
    job_id = str(uuid.uuid4())
    job = Job(
        job_id=job_id,
        url=payload.url,
        stt_model=payload.stt_model,
        translation_engine=payload.translation_engine,
        domain=payload.domain,
        src_lang=payload.src_lang,
        tgt_lang=payload.tgt_lang,
        download_mode=payload.download_mode,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    logger.info(
        "[%s] Job queued — url=%s model=%s engine=%s domain=%s %s→%s mode=%s",
        job_id, payload.url, payload.stt_model, payload.translation_engine,
        payload.domain, payload.src_lang, payload.tgt_lang, payload.download_mode,
    )
    background_tasks.add_task(run_job, job_id)

    return JobResponse(
        jobId=job.job_id,
        status=job.status,
        progress=job.progress,
        outputUrl=None,
        subtitleUrl=None,
        srtUrl=None,
        embedUrl=None,
        error=None,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, session: SessionDep):
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        jobId=job.job_id,
        status=job.status,
        progress=job.progress,
        outputUrl=f"/files/{job.job_id}/video.mp4" if job.output_path and job.download_mode == "video" else None,
        subtitleUrl=f"/files/{job.job_id}/subtitles.vtt" if job.subtitle_path and job.download_mode == "video" else None,
        srtUrl=f"/files/{job.job_id}/subtitles.srt" if job.subtitle_path else None,
        embedUrl=job.url if job.download_mode == "audio_only" and job.subtitle_path else None,
        error=job.error,
    )


@router.get("")
async def list_jobs(session: SessionDep):
    jobs = session.exec(select(Job).order_by(Job.created_at.desc()).limit(50)).all()
    return [
        {"jobId": j.job_id, "status": j.status, "url": j.url, "domain": j.domain, "createdAt": j.created_at}
        for j in jobs
    ]
