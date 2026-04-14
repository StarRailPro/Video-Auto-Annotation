from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    TagCreate,
    TagUpdate,
    TagResponse,
    TagListResponse,
    MessageResponse,
)
from ..services.tag_manager import TagManager

router = APIRouter(prefix="/api/tags", tags=["Tags"])


@router.get("", response_model=TagListResponse)
def list_tags(
    active_only: bool = Query(default=False, description="Only return active tags"),
    db: Session = Depends(get_db),
):
    tags = TagManager.get_all_tags(db, active_only=active_only)
    tag_responses = [TagResponse.model_validate(tag) for tag in tags]
    return TagListResponse(tags=tag_responses, total=len(tag_responses))


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: int,
    db: Session = Depends(get_db),
):
    tag = TagManager.get_tag_by_id(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag with id {tag_id} not found")
    return TagResponse.model_validate(tag)


@router.post("", response_model=TagResponse, status_code=201)
def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
):
    try:
        tag = TagManager.create_tag(db, tag_data)
        return TagResponse.model_validate(tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    db: Session = Depends(get_db),
):
    try:
        tag = TagManager.update_tag(db, tag_id, tag_data)
        return TagResponse.model_validate(tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{tag_id}", response_model=MessageResponse)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
):
    try:
        TagManager.delete_tag(db, tag_id)
        return MessageResponse(message="Tag deleted successfully", success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/values/active", response_model=MessageResponse)
def get_active_tag_values(db: Session = Depends(get_db)):
    values = TagManager.get_active_tag_values(db)
    return MessageResponse(
        message="Active tag values retrieved",
        success=True,
        data={"values": values},
    )
