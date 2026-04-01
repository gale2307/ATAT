import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.database import get_session
from app.models.job import Job, JobStatus
from app.pipeline import run_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

SessionDep = Annotated[Session, Depends(get_session)]


class JobCreate(BaseModel):
    url: str
    stt_model: str = "whisper-large-v3"
    translation_engine: str = "qwen-mt"
    domain: str = "general"
    src_lang: str = "ko"
    tgt_lang: str = "en"


class JobResponse(BaseModel):
    jobId: str
    status: str
    progress: int
    outputUrl: str | None
    subtitleUrl: str | None
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
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(run_job, job_id)

    return JobResponse(
        jobId=job.job_id,
        status=job.status,
        progress=job.progress,
        outputUrl=None,
        subtitleUrl=None,
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
        outputUrl=f"/files/{job.job_id}/output.mp4" if job.output_path else None,
        subtitleUrl=f"/files/{job.job_id}/subtitles.srt" if job.subtitle_path else None,
        error=job.error,
    )


@router.get("")
async def list_jobs(session: SessionDep):
    jobs = session.exec(select(Job).order_by(Job.created_at.desc()).limit(50)).all()
    return [
        {"jobId": j.job_id, "status": j.status, "url": j.url, "domain": j.domain, "createdAt": j.created_at}
        for j in jobs
    ]
