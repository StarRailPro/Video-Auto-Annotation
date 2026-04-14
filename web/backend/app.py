from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from .database import init_db, engine, Base
from .models import Task, VideoAnnotationRecord, Tag, Setting
from .services.ws_manager import ws_manager
from .routes.tags import router as tags_router
from .routes.tasks import router as tasks_router
from .routes.annotations import router as annotations_router
from .routes.settings import router as settings_router

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    _init_default_data()
    logger.info("Database initialized successfully")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Video Auto Annotation API",
    description="Web API for video annotation with AI analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tags_router)
app.include_router(tasks_router)
app.include_router(annotations_router)
app.include_router(settings_router)


def _init_default_data():
    from sqlalchemy.orm import Session
    from .database import SessionLocal
    
    db: Session = SessionLocal()
    try:
        existing_tags = db.query(Tag).count()
        if existing_tags == 0:
            default_tags = [
                {"name": "日常活动", "value": "daily_activity", "description": "日常生活中的常规活动", "is_system": True},
                {"name": "非法入侵", "value": "illegal_intrusion", "description": "未经授权进入限制区域", "is_system": True},
                {"name": "财产损坏", "value": "property_damage", "description": "对财产造成损坏的行为", "is_system": True},
                {"name": "社交聚会", "value": "social_gathering", "description": "多人聚集的社交活动", "is_system": True},
                {"name": "车辆移动", "value": "vehicle_movement", "description": "车辆的移动行为", "is_system": True},
                {"name": "动物活动", "value": "animal_activity", "description": "动物的相关活动", "is_system": True},
                {"name": "紧急情况", "value": "emergency_situation", "description": "需要紧急处理的危险情况", "is_system": True},
                {"name": "正常操作", "value": "normal_operation", "description": "正常的操作流程", "is_system": True},
                {"name": "异常视频", "value": "abnormal_video", "description": "视频文件异常（过短、损坏等）", "is_system": True},
            ]
            for tag_data in default_tags:
                tag = Tag(**tag_data)
                db.add(tag)
            db.commit()
            logger.info(f"Initialized {len(default_tags)} default tags")
        
        existing_settings = db.query(Setting).count()
        if existing_settings == 0:
            default_settings = [
                {"key": "api_key", "value": "", "encrypted": True},
                {"key": "max_workers", "value": "5", "encrypted": False},
                {"key": "mcp_mode", "value": "ZHIPU", "encrypted": False},
            ]
            for setting_data in default_settings:
                setting = Setting(**setting_data)
                db.add(setting)
            db.commit()
            logger.info(f"Initialized {len(default_settings)} default settings")
    except Exception as e:
        logger.error(f"Error initializing default data: {e}")
        db.rollback()
    finally:
        db.close()


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Video Annotation API is running"}


@app.get("/api")
async def api_root():
    return {
        "message": "Video Auto Annotation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.websocket("/api/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: int):
    await ws_manager.connect(websocket, task_id)
    try:
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.warning(f"WebSocket error for task {task_id}: {e}")
    finally:
        await ws_manager.disconnect(websocket, task_id)


def get_progress_callback(task_id: int):
    """
    Create a progress callback that broadcasts updates via WebSocket.
    This bridges the sync TaskManager thread to the async WebSocket layer.
    """
    def callback(data: dict):
        ws_manager.broadcast_sync(task_id, data)
    return callback


if FRONTEND_DIST.exists() and FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
    logger.info(f"Frontend static files mounted from {FRONTEND_DIST}")
else:
    logger.info(f"Frontend dist not found at {FRONTEND_DIST}, API-only mode")
