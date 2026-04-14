import os
import shutil
import logging
import threading
from datetime import datetime
from typing import List, Optional, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session
from sqlalchemy import select, update

from ..models import Task, VideoAnnotationRecord, Tag
from ..database import SessionLocal
from .tag_manager import TagManager

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "src")))

from src.video_agent.core.video_processor import process_video_file
from src.video_agent.core.ai_analyzer import analyze_video_with_ai
from src.video_agent.utils.mcp_client import MCPClient, MCPClientError

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


class TaskManager:

    _running_tasks: Dict[int, bool] = {}
    _task_threads: Dict[int, threading.Thread] = {}
    _lock = threading.Lock()

    @staticmethod
    def create_task(
        db: Session,
        name: str,
        video_paths: Optional[List[str]] = None,
        uploaded_files: Optional[List[Dict[str, str]]] = None,
        max_workers: int = 5,
    ) -> Task:
        task = Task(
            name=name,
            status="pending",
            total_videos=0,
            processed_videos=0,
            successful_videos=0,
            failed_videos=0,
            max_workers=max_workers,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        all_video_paths: List[str] = []

        if video_paths:
            for vp in video_paths:
                if os.path.isfile(vp):
                    all_video_paths.append(vp)

        if uploaded_files:
            _ensure_upload_dir()
            for uf in uploaded_files:
                src = uf.get("temp_path", "")
                original_name = uf.get("filename", "unknown")
                if not src or not os.path.isfile(src):
                    continue
                dest_dir = os.path.join(UPLOAD_DIR, str(task.id))
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, original_name)
                shutil.copy2(src, dest_path)
                all_video_paths.append(dest_path)

        supported_ext = [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"]
        for vp in all_video_paths:
            ext = os.path.splitext(vp)[1].lower()
            if ext not in supported_ext:
                logger.warning(f"Skipping unsupported file: {vp}")
                continue
            file_name = os.path.basename(vp)
            record = VideoAnnotationRecord(
                task_id=task.id,
                file_path=vp,
                file_name=file_name,
                status="pending",
            )
            db.add(record)

        task.total_videos = len(db.execute(
            select(VideoAnnotationRecord).where(VideoAnnotationRecord.task_id == task.id)
        ).scalars().all())
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_task(db: Session, task_id: int) -> Optional[Task]:
        result = db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    def list_tasks(db: Session, skip: int = 0, limit: int = 50) -> List[Task]:
        result = db.execute(
            select(Task).order_by(Task.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        task = TaskManager.get_task(db, task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        if task.status == "processing":
            TaskManager.cancel_task(task_id)

        upload_dir = os.path.join(UPLOAD_DIR, str(task_id))
        if os.path.isdir(upload_dir):
            shutil.rmtree(upload_dir, ignore_errors=True)

        db.delete(task)
        db.commit()
        return True

    @staticmethod
    def start_task(
        task_id: int,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        with TaskManager._lock:
            if task_id in TaskManager._running_tasks and TaskManager._running_tasks[task_id]:
                raise ValueError(f"Task {task_id} is already running")

        thread = threading.Thread(
            target=TaskManager._run_task,
            args=(task_id, progress_callback),
            daemon=True,
        )
        with TaskManager._lock:
            TaskManager._running_tasks[task_id] = True
            TaskManager._task_threads[task_id] = thread
        thread.start()
        return True

    @staticmethod
    def cancel_task(task_id: int) -> bool:
        with TaskManager._lock:
            TaskManager._running_tasks[task_id] = False
        logger.info(f"Task {task_id} cancellation requested")
        return True

    @staticmethod
    def is_task_running(task_id: int) -> bool:
        return TaskManager._running_tasks.get(task_id, False)

    @staticmethod
    def retry_failed(db: Session, task_id: int) -> Task:
        task = TaskManager.get_task(db, task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        if TaskManager.is_task_running(task_id):
            raise ValueError(f"Task {task_id} is currently running, cannot retry")

        failed_records = db.execute(
            select(VideoAnnotationRecord).where(
                VideoAnnotationRecord.task_id == task_id,
                VideoAnnotationRecord.status == "failed",
            )
        ).scalars().all()

        if not failed_records:
            raise ValueError(f"No failed videos found in task {task_id}")

        for record in failed_records:
            record.status = "pending"
            record.error_message = None
            record.description = None
            record.tags = []
            record.confidence_scores = None

        task.status = "pending"
        task.processed_videos = task.successful_videos
        task.failed_videos = 0
        task.current_video = None
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_task_annotations(db: Session, task_id: int) -> List[VideoAnnotationRecord]:
        result = db.execute(
            select(VideoAnnotationRecord)
            .where(VideoAnnotationRecord.task_id == task_id)
            .order_by(VideoAnnotationRecord.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _run_task(
        task_id: int,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        db: Session = SessionLocal()
        try:
            task = TaskManager.get_task(db, task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            task.status = "processing"
            task.started_at = datetime.utcnow()
            db.commit()

            _notify(progress_callback, {
                "task_id": task_id,
                "status": "processing",
                "total_videos": task.total_videos,
                "processed_videos": task.processed_videos,
                "successful_videos": task.successful_videos,
                "failed_videos": task.failed_videos,
                "progress": 0.0,
                "message": "Task started",
            })

            active_tags = TagManager.get_active_tag_values(db)

            api_key = TaskManager._get_api_key(db)
            if not api_key:
                task.status = "failed"
                db.commit()
                _notify(progress_callback, {
                    "task_id": task_id,
                    "status": "failed",
                    "message": "API key not configured",
                })
                return

            try:
                ai_client = MCPClient(
                    api_key=api_key,
                    mode=TaskManager._get_mcp_mode(db),
                )
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                task.status = "failed"
                db.commit()
                _notify(progress_callback, {
                    "task_id": task_id,
                    "status": "failed",
                    "message": f"MCP client init failed: {e}",
                })
                return

            pending_records = db.execute(
                select(VideoAnnotationRecord).where(
                    VideoAnnotationRecord.task_id == task_id,
                    VideoAnnotationRecord.status == "pending",
                )
            ).scalars().all()

            max_workers = task.max_workers or 5

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_record = {}
                for record in pending_records:
                    if not TaskManager._running_tasks.get(task_id, False):
                        break
                    future = executor.submit(
                        TaskManager._process_single_video,
                        record.id,
                        record.file_path,
                        ai_client,
                        active_tags,
                        progress_callback,
                    )
                    future_to_record[future] = record.id

                for future in as_completed(future_to_record):
                    record_id = future_to_record[future]
                    if not TaskManager._running_tasks.get(task_id, False):
                        logger.info(f"Task {task_id} cancelled, stopping workers")
                        break

                    try:
                        result_data = future.result()
                        TaskManager._update_record_success(db, record_id, result_data)
                    except Exception as e:
                        logger.error(f"Error processing video record {record_id}: {e}")
                        TaskManager._update_record_failed(db, record_id, str(e))

                    TaskManager._update_task_progress(db, task_id, progress_callback)

            cancelled = not TaskManager._running_tasks.get(task_id, False)
            task = TaskManager.get_task(db, task_id)
            if task:
                if cancelled:
                    task.status = "cancelled"
                elif task.failed_videos > 0 and task.successful_videos > 0:
                    task.status = "partial"
                elif task.failed_videos > 0 and task.successful_videos == 0:
                    task.status = "failed"
                else:
                    task.status = "completed"
                task.completed_at = datetime.utcnow()
                db.commit()

            _notify(progress_callback, {
                "task_id": task_id,
                "status": task.status if task else "unknown",
                "message": f"Task {'cancelled' if cancelled else 'completed'}",
            })

        except Exception as e:
            logger.error(f"Task {task_id} execution error: {e}", exc_info=True)
            try:
                task = TaskManager.get_task(db, task_id)
                if task:
                    task.status = "failed"
                    task.completed_at = datetime.utcnow()
                    db.commit()
            except Exception:
                pass
            _notify(progress_callback, {
                "task_id": task_id,
                "status": "failed",
                "message": str(e),
            })
        finally:
            with TaskManager._lock:
                TaskManager._running_tasks.pop(task_id, None)
                TaskManager._task_threads.pop(task_id, None)
            db.close()

    @staticmethod
    def _process_single_video(
        record_id: int,
        file_path: str,
        ai_client: Any,
        active_tags: List[str],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            db.execute(
                update(VideoAnnotationRecord)
                .where(VideoAnnotationRecord.id == record_id)
                .values(status="processing")
            )
            db.commit()

            video_data = process_video_file(file_path)

            try:
                ai_result = analyze_video_with_ai(
                    video_data,
                    client=ai_client,
                    predefined_tags=active_tags,
                )
            except MCPClientError as e:
                error_str = str(e)
                if "retry" in error_str.lower() or "retries" in error_str.lower():
                    _notify(progress_callback, {
                        "task_id": db.execute(
                            select(VideoAnnotationRecord.task_id).where(
                                VideoAnnotationRecord.id == record_id
                            )
                        ).scalar(),
                        "status": "processing",
                        "message": f"AI 分析失败，正在自动重试: {error_str[:100]}",
                    })
                raise

            result = {
                "description": ai_result.get("description", ""),
                "tags": ai_result.get("tags", []),
                "duration_seconds": video_data.get("duration_seconds"),
                "is_abnormal": video_data.get("is_abnormal", False),
                "abnormality_reason": video_data.get("abnormality_reason"),
                "confidence_scores": ai_result.get("confidence_scores"),
            }

            temp_dir = video_data.get("temp_dir")
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

            return result

        except Exception as e:
            logger.error(f"Error in _process_single_video for record {record_id}: {e}")
            raise
        finally:
            db.close()

    @staticmethod
    def _update_record_success(db: Session, record_id: int, result_data: Dict[str, Any]):
        db.execute(
            update(VideoAnnotationRecord)
            .where(VideoAnnotationRecord.id == record_id)
            .values(
                status="completed",
                description=result_data.get("description", ""),
                tags=result_data.get("tags", []),
                duration_seconds=result_data.get("duration_seconds"),
                is_abnormal=result_data.get("is_abnormal", False),
                abnormality_reason=result_data.get("abnormality_reason"),
                confidence_scores=result_data.get("confidence_scores"),
                processing_timestamp=datetime.utcnow(),
            )
        )
        db.commit()

    @staticmethod
    def _update_record_failed(db: Session, record_id: int, error_message: str):
        db.execute(
            update(VideoAnnotationRecord)
            .where(VideoAnnotationRecord.id == record_id)
            .values(
                status="failed",
                error_message=error_message,
                processing_timestamp=datetime.utcnow(),
            )
        )
        db.commit()

    @staticmethod
    def _update_task_progress(
        db: Session,
        task_id: int,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        task = TaskManager.get_task(db, task_id)
        if not task:
            return

        completed_count = db.execute(
            select(VideoAnnotationRecord).where(
                VideoAnnotationRecord.task_id == task_id,
                VideoAnnotationRecord.status == "completed",
            )
        ).scalars().all()

        failed_count = db.execute(
            select(VideoAnnotationRecord).where(
                VideoAnnotationRecord.task_id == task_id,
                VideoAnnotationRecord.status == "failed",
            )
        ).scalars().all()

        processing = db.execute(
            select(VideoAnnotationRecord).where(
                VideoAnnotationRecord.task_id == task_id,
                VideoAnnotationRecord.status == "processing",
            )
        ).scalars().all()

        task.processed_videos = len(completed_count) + len(failed_count)
        task.successful_videos = len(completed_count)
        task.failed_videos = len(failed_count)
        if processing:
            task.current_video = processing[0].file_name
        else:
            pending = db.execute(
                select(VideoAnnotationRecord).where(
                    VideoAnnotationRecord.task_id == task_id,
                    VideoAnnotationRecord.status == "pending",
                )
            ).scalars().first()
            task.current_video = pending.file_name if pending else None
        db.commit()

        progress = 0.0
        if task.total_videos > 0:
            progress = round((task.processed_videos / task.total_videos) * 100, 1)

        _notify(progress_callback, {
            "task_id": task_id,
            "status": "processing",
            "current_video": task.current_video,
            "processed_videos": task.processed_videos,
            "total_videos": task.total_videos,
            "successful_videos": task.successful_videos,
            "failed_videos": task.failed_videos,
            "progress": progress,
        })

    @staticmethod
    def _get_api_key(db: Session) -> Optional[str]:
        from ..models import Setting
        result = db.execute(select(Setting).where(Setting.key == "api_key")).scalar_one_or_none()
        if result and result.value:
            return result.value
        return None

    @staticmethod
    def _get_mcp_mode(db: Session) -> str:
        from ..models import Setting
        result = db.execute(select(Setting).where(Setting.key == "mcp_mode")).scalar_one_or_none()
        if result and result.value:
            return result.value
        return "ZHIPU"


def _notify(
    callback: Optional[Callable[[Dict[str, Any]], None]],
    data: Dict[str, Any],
):
    if callback:
        try:
            callback(data)
        except Exception as e:
            logger.error(f"Progress callback error: {e}")


task_manager = TaskManager()
