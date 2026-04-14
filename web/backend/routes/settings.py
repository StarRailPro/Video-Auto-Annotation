import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import Setting
from ..schemas import (
    SettingCreate,
    SettingUpdate,
    SettingResponse,
    SettingListResponse,
    MessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=SettingListResponse)
def list_settings(db: Session = Depends(get_db)):
    result = db.execute(select(Setting).order_by(Setting.id.asc()))
    settings = list(result.scalars().all())
    setting_responses = []
    for s in settings:
        setting_responses.append(SettingResponse(
            id=s.id,
            key=s.key,
            value=s.value if not s.encrypted else _mask_value(s.value),
            encrypted=s.encrypted,
            updated_at=s.updated_at,
        ))
    return SettingListResponse(settings=setting_responses, total=len(setting_responses))


@router.get("/{key}", response_model=SettingResponse)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
):
    result = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return SettingResponse(
        id=result.id,
        key=result.key,
        value=result.value if not result.encrypted else _mask_value(result.value),
        encrypted=result.encrypted,
        updated_at=result.updated_at,
    )


@router.put("/{key}", response_model=SettingResponse)
def update_setting(
    key: str,
    setting_data: SettingUpdate,
    db: Session = Depends(get_db),
):
    result = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    result.value = setting_data.value
    db.commit()
    db.refresh(result)

    return SettingResponse(
        id=result.id,
        key=result.key,
        value=result.value if not result.encrypted else _mask_value(result.value),
        encrypted=result.encrypted,
        updated_at=result.updated_at,
    )


@router.post("", response_model=SettingResponse, status_code=201)
def create_setting(
    setting_data: SettingCreate,
    db: Session = Depends(get_db),
):
    existing = db.execute(select(Setting).where(Setting.key == setting_data.key)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Setting '{setting_data.key}' already exists")

    is_encrypted = setting_data.key in ("api_key",)

    setting = Setting(
        key=setting_data.key,
        value=setting_data.value,
        encrypted=is_encrypted,
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)

    return SettingResponse(
        id=setting.id,
        key=setting.key,
        value=setting.value if not setting.encrypted else _mask_value(setting.value),
        encrypted=setting.encrypted,
        updated_at=setting.updated_at,
    )


@router.delete("/{key}", response_model=MessageResponse)
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
):
    result = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    db.delete(result)
    db.commit()
    return MessageResponse(message=f"Setting '{key}' deleted", success=True)


@router.post("/api-key/test", response_model=MessageResponse)
def test_api_key(db: Session = Depends(get_db)):
    result = db.execute(select(Setting).where(Setting.key == "api_key")).scalar_one_or_none()
    if not result or not result.value:
        return MessageResponse(message="API key not configured", success=False)

    try:
        from src.video_agent.utils.mcp_client import MCPClient
        mcp_mode_result = db.execute(select(Setting).where(Setting.key == "mcp_mode")).scalar_one_or_none()
        mode = mcp_mode_result.value if mcp_mode_result and mcp_mode_result.value else "ZHIPU"

        client = MCPClient(api_key=result.value, mode=mode)
        client.close()
        return MessageResponse(message="API key is valid", success=True)
    except Exception as e:
        logger.error(f"API key test failed: {e}")
        return MessageResponse(message=f"API key test failed: {e}", success=False)


def _mask_value(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 6) + value[-3:]
