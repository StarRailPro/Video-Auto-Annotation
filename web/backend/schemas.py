from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    max_workers: int = Field(default=5, ge=1, le=20, description="Max concurrent workers")
    video_paths: Optional[List[str]] = Field(default=None, description="Local video paths to process")


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    max_workers: Optional[int] = Field(None, ge=1, le=20)


class VideoAnnotationResponse(BaseModel):
    id: int
    task_id: int
    file_path: str
    file_name: str
    status: VideoStatus
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    is_abnormal: bool = False
    abnormality_reason: Optional[str] = None
    confidence_scores: Optional[Dict[str, float]] = None
    processing_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_videos: int = 0
    processed_videos: int = 0
    successful_videos: int = 0
    failed_videos: int = 0
    current_video: Optional[str] = None
    max_workers: int = 5
    progress: float = Field(default=0.0, description="Progress percentage (0-100)")

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_progress(cls, task):
        progress = 0.0
        if task.total_videos > 0:
            progress = round((task.processed_videos / task.total_videos) * 100, 1)
        data = {
            "id": task.id,
            "name": task.name,
            "status": task.status,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "total_videos": task.total_videos,
            "processed_videos": task.processed_videos,
            "successful_videos": task.successful_videos,
            "failed_videos": task.failed_videos,
            "current_video": task.current_video,
            "max_workers": task.max_workers,
            "progress": progress,
        }
        return cls(**data)


class TaskDetailResponse(TaskResponse):
    video_annotations: List[VideoAnnotationResponse] = Field(default_factory=list)


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Display name of the tag")
    value: str = Field(..., min_length=1, max_length=100, description="Value used in API (e.g., 'daily_activity')")
    description: Optional[str] = Field(None, max_length=500, description="Tag description")


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class TagResponse(BaseModel):
    id: int
    name: str
    value: str
    description: Optional[str] = None
    is_system: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    tags: List[TagResponse]
    total: int


class SettingCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., description="Setting value (will be encrypted if sensitive)")


class SettingUpdate(BaseModel):
    value: str = Field(..., description="New setting value")


class SettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str] = Field(None, description="Decrypted value for display")
    encrypted: bool = False
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingListResponse(BaseModel):
    settings: List[SettingResponse]
    total: int


class ProgressUpdate(BaseModel):
    task_id: int
    status: TaskStatus
    current_video: Optional[str] = None
    processed_videos: int = 0
    total_videos: int = 0
    successful_videos: int = 0
    failed_videos: int = 0
    progress: float = 0.0
    message: Optional[str] = None


class VideoProgressUpdate(BaseModel):
    task_id: int
    video_id: int
    file_name: str
    status: VideoStatus
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
    success: bool = True
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    detail: str
    success: bool = False


class FileUploadResponse(BaseModel):
    filename: str
    file_path: str
    size: int
    message: str = "File uploaded successfully"


class AnnotationExportResponse(BaseModel):
    task_id: int
    task_name: str
    total_videos_processed: int
    successful_annotations: int
    failed_annotations: int
    annotations: List[VideoAnnotationResponse]
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    export_timestamp: datetime = Field(default_factory=datetime.utcnow)
