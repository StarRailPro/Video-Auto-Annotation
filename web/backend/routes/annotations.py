import json
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import Task, VideoAnnotationRecord
from ..schemas import (
    VideoAnnotationResponse,
    AnnotationExportResponse,
    MessageResponse,
)
from ..services.task_manager import TaskManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/annotations", tags=["Annotations"])


@router.get("/task/{task_id}", response_model=List[VideoAnnotationResponse])
def get_task_annotations(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = TaskManager.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")

    annotations = TaskManager.get_task_annotations(db, task_id)
    return [VideoAnnotationResponse.model_validate(a) for a in annotations]


@router.get("/task/{task_id}/summary", response_model=AnnotationExportResponse)
def get_task_annotation_summary(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = TaskManager.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")

    annotations = TaskManager.get_task_annotations(db, task_id)
    annotation_responses = [VideoAnnotationResponse.model_validate(a) for a in annotations]

    successful = sum(1 for a in annotations if a.status == "completed" and not a.is_abnormal)
    failed = sum(1 for a in annotations if a.status == "failed")

    return AnnotationExportResponse(
        task_id=task.id,
        task_name=task.name,
        total_videos_processed=task.total_videos,
        successful_annotations=successful,
        failed_annotations=failed,
        annotations=annotation_responses,
        processing_start_time=task.started_at,
        processing_end_time=task.completed_at,
        export_timestamp=datetime.utcnow(),
    )


@router.get("/task/{task_id}/download")
def download_task_annotations(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = TaskManager.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")

    annotations = TaskManager.get_task_annotations(db, task_id)

    successful = sum(1 for a in annotations if a.status == "completed" and not a.is_abnormal)
    failed = sum(1 for a in annotations if a.status == "failed")

    export_data = {
        "task_id": task.id,
        "task_name": task.name,
        "total_videos_processed": task.total_videos,
        "successful_annotations": successful,
        "failed_annotations": failed,
        "processing_start_time": task.started_at.isoformat() if task.started_at else None,
        "processing_end_time": task.completed_at.isoformat() if task.completed_at else None,
        "annotations": [
            {
                "file_name": a.file_name,
                "file_path": a.file_path,
                "status": a.status,
                "description": a.description,
                "tags": a.tags if a.tags else [],
                "duration_seconds": a.duration_seconds,
                "is_abnormal": a.is_abnormal,
                "abnormality_reason": a.abnormality_reason,
                "confidence_scores": a.confidence_scores,
                "processing_timestamp": a.processing_timestamp.isoformat() if a.processing_timestamp else None,
                "error_message": a.error_message,
            }
            for a in annotations
        ],
    }

    json_content = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
    filename = f"annotations_task_{task_id}.json"

    return StreamingResponse(
        iter([json_content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get("/video/{annotation_id}", response_model=VideoAnnotationResponse)
def get_single_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(VideoAnnotationRecord).where(VideoAnnotationRecord.id == annotation_id)
    )
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise HTTPException(status_code=404, detail=f"Annotation with id {annotation_id} not found")
    return VideoAnnotationResponse.model_validate(annotation)
