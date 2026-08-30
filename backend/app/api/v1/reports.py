"""Field reports API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import FieldReport
from app.schemas.report import ReportCreate, ReportOut, ReportStatusUpdate

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=201)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)) -> FieldReport:
    exists = db.query(FieldReport).filter(FieldReport.client_id == payload.client_id).one_or_none()
    if exists:
        exists.sync_status = "conflict"
        exists.conflict_with = exists.id
        db.commit()
        return exists
    data = payload.model_dump()
    r = FieldReport(
        **data,
        received_at=datetime.now(timezone.utc),
    )
    db.add(r); db.commit(); db.refresh(r)
    return r


@router.post("/upload", response_model=ReportOut, status_code=201)
def create_report_with_files(
    client_id: str = Form(...),
    report_type: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: str | None = Form(None),
    timestamp: str = Form(...),
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> FieldReport:
    """For common people on low-network: multipart with photo/video (saved locally)."""
    from datetime import datetime

    exists = db.query(FieldReport).filter(FieldReport.client_id == client_id).one_or_none()
    if exists:
        exists.sync_status = "conflict"
        db.commit()
        return exists
    # Save files locally (no cloud needed)
    image_url = None
    video_url = None
    if image and image.filename:
        p = UPLOAD_DIR / f"{client_id}_{image.filename}"
        with open(p, "wb") as f:
            shutil.copyfileobj(image.file, f)
        image_url = str(p)
    if video and video.filename:
        p = UPLOAD_DIR / f"{client_id}_{video.filename}"
        with open(p, "wb") as f:
            shutil.copyfileobj(video.file, f)
        video_url = str(p)
    # Parse timestamp flexibly
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:
        ts = datetime.now(timezone.utc)
    r = FieldReport(
        client_id=client_id,
        report_type=report_type,  # type: ignore
        description=description,
        image_url=image_url,
        video_url=video_url,
        timestamp=ts,
        received_at=datetime.now(timezone.utc),
        latitude=latitude,
        longitude=longitude,
        status="RECEIVED",  # type: ignore
        sync_status="synced" if image_url or video_url else "synced",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.get("", response_model=List[ReportOut])
def list_reports(
    status: Optional[str] = None,
    report_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[FieldReport]:
    stmt = db.query(FieldReport).order_by(desc(FieldReport.timestamp))
    if status:
        stmt = stmt.filter(FieldReport.status == status)
    if report_type:
        stmt = stmt.filter(FieldReport.report_type == report_type)
    return stmt.limit(limit).all()


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)) -> FieldReport:
    r = db.get(FieldReport, report_id)
    if r is None:
        raise NotFoundError(f"report {report_id} not found")
    return r


@router.patch("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: int, payload: ReportStatusUpdate, db: Session = Depends(get_db)
) -> FieldReport:
    r = db.get(FieldReport, report_id)
    if r is None:
        raise NotFoundError(f"report {report_id} not found")
    r.status = payload.status
    db.commit(); db.refresh(r)
    return r
