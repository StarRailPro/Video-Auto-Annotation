from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from ..models import Tag
from ..schemas import TagCreate, TagUpdate


class TagManager:

    @staticmethod
    def get_all_tags(db: Session, active_only: bool = False) -> List[Tag]:
        query = select(Tag)
        if active_only:
            query = query.where(Tag.is_active.is_(True))
        query = query.order_by(Tag.is_system.desc(), Tag.created_at.asc())
        result = db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def get_tag_by_id(db: Session, tag_id: int) -> Optional[Tag]:
        result = db.execute(select(Tag).where(Tag.id == tag_id))
        return result.scalar_one_or_none()

    @staticmethod
    def get_tag_by_value(db: Session, value: str) -> Optional[Tag]:
        result = db.execute(select(Tag).where(Tag.value == value))
        return result.scalar_one_or_none()

    @staticmethod
    def get_active_tag_values(db: Session) -> List[str]:
        result = db.execute(select(Tag.value).where(Tag.is_active.is_(True)))
        return list(result.scalars().all())

    @staticmethod
    def create_tag(db: Session, tag_data: TagCreate) -> Tag:
        existing = db.execute(
            select(Tag).where((Tag.name == tag_data.name) | (Tag.value == tag_data.value))
        ).scalar_one_or_none()
        if existing:
            raise ValueError(f"Tag with name '{tag_data.name}' or value '{tag_data.value}' already exists")

        tag = Tag(
            name=tag_data.name,
            value=tag_data.value,
            description=tag_data.description,
            is_system=False,
            is_active=True,
        )
        db.add(tag)
        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def update_tag(db: Session, tag_id: int, tag_data: TagUpdate) -> Tag:
        tag = TagManager.get_tag_by_id(db, tag_id)
        if not tag:
            raise ValueError(f"Tag with id {tag_id} not found")

        if tag.is_system and tag_data.is_active is False:
            raise ValueError("Cannot deactivate system tags")

        if tag_data.name is not None:
            tag.name = tag_data.name
        if tag_data.description is not None:
            tag.description = tag_data.description
        if tag_data.is_active is not None:
            tag.is_active = tag_data.is_active

        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def delete_tag(db: Session, tag_id: int) -> bool:
        tag = TagManager.get_tag_by_id(db, tag_id)
        if not tag:
            raise ValueError(f"Tag with id {tag_id} not found")

        if tag.is_system:
            raise ValueError("Cannot delete system tags")

        db.delete(tag)
        db.commit()
        return True

    @staticmethod
    def validate_tags(db: Session, tag_values: List[str]) -> List[str]:
        active_values = TagManager.get_active_tag_values(db)
        validated = []
        for tv in tag_values:
            if tv in active_values:
                validated.append(tv)
            else:
                raise ValueError(f"Tag '{tv}' is not a valid active tag")
        return validated

    @staticmethod
    def ensure_abnormal_video_tag(db: Session) -> Tag:
        tag = db.execute(select(Tag).where(Tag.value == "abnormal_video")).scalar_one_or_none()
        if not tag:
            tag = Tag(
                name="异常视频",
                value="abnormal_video",
                description="视频文件异常（过短、损坏等）",
                is_system=True,
                is_active=True,
            )
            db.add(tag)
            db.commit()
            db.refresh(tag)
        return tag


tag_manager = TagManager()
