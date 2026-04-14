import os
import tempfile
import shutil
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    TaskCreate,
    TaskResponse,
    TaskDetailResponse,
    TaskListResponse,
    VideoAnnotationResponse,
    MessageResponse,
)
from ..services.task_manager import TaskManager, UPLOAD_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def _task_to_response(task) -> TaskResponse:
    progress = 0.0
    if task.total_videos > 0:
        progress = round((task.processed_videos / task.total_videos) * 100, 1)
    return TaskResponse(
        id=task.id,
        name=task.name,
        status=task.status,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        total_videos=task.total_videos,
        processed_videos=task.processed_videos,
        successful_videos=task.successful_videos,
        failed_videos=task.failed_videos,
        current_video=task.current_video,
        max_workers=task.max_workers,
        progress=progress,
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    tasks = TaskManager.list_tasks(db, skip=skip, limit=limit)
    task_responses = [_task_to_response(t) for t in tasks]
    return TaskListResponse(tasks=task_responses, total=len(task_responses))


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = TaskManager.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")

    base = _task_to_response(task)
    annotations = TaskManager.get_task_annotations(db, task_id)
    annotation_responses = [
        VideoAnnotationResponse.model_validate(a) for a in annotations
    ]

    return TaskDetailResponse(
        **base.model_dump(),
        video_annotations=annotation_responses,
    )


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
):
    try:
        task = TaskManager.create_task(
            db,
            name=task_data.name,
            video_paths=task_data.video_paths,
            max_workers=task_data.max_workers,
        )
        return _task_to_response(task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload", response_model=TaskResponse, status_code=201)
async def create_task_with_upload(
    name: str = Form(...),
    max_workers: int = Form(default=5),
    video_paths: Optional[str] = Form(default=None),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    parsed_paths: Optional[List[str]] = None
    if video_paths:
        parsed_paths = [p.strip() for p in video_paths.split(",") if p.strip()]

    uploaded_files = []
    temp_dir = tempfile.mkdtemp(prefix="upload_")

    try:
        for f in files:
            if not f.filename:
                continue
            ext = os.path.splitext(f.filename)[1].lower()
            supported = [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"]
            if ext not in supported:
                logger.warning(f"Skipping unsupported file: {f.filename}")
                continue

            temp_path = os.path.join(temp_dir, f.filename)
            with open(temp_path, "wb") as out:
                content = await f.read()
                out.write(content)
            uploaded_files.append({
                "temp_path": temp_path,
                "filename": f.filename,
            })

        task = TaskManager.create_task(
            db,
            name=name,
            video_paths=parsed_paths,
            uploaded_files=uploaded_files if uploaded_files else None,
            max_workers=max_workers,
        )
        return _task_to_response(task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/{task_id}/start", response_model=MessageResponse)
def start_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = TaskManager.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")

    if TaskManager.is_task_running(task_id):
        raise HTTPException(status_code=400, detail=f"Task {task_id} is already running")

    try:
        from ..app import get_progress_callback
        callback = get_progress_callback(task_id)
        TaskManager.start_task(task_id, progress_callback=callback)
        return MessageResponse(message=f"Task {task_id} started", success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/cancel", response_model=MessageResponse)
def cancel_task(task_id: int):
    if not TaskManager.is_task_running(task_id):
        raise HTTPException(status_code=400, detail=f"Task {task_id} is not running")
    TaskManager.cancel_task(task_id)
    return MessageResponse(message=f"Task {task_id} cancellation requested", success=True)


@router.post("/{task_id}/retry", response_model=MessageResponse)
def retry_failed(
    task_id: int,
    db: Session = Depends(get_db),
):
    try:
        task = TaskManager.retry_failed(db, task_id)
        if not TaskManager.is_task_running(task_id):
            from ..app import get_progress_callback
            callback = get_progress_callback(task_id)
            TaskManager.start_task(task_id, progress_callback=callback)
        return MessageResponse(message=f"Task {task_id} retry started", success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}", response_model=MessageResponse)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    try:
        TaskManager.delete_task(db, task_id)
        return MessageResponse(message=f"Task {task_id} deleted", success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
