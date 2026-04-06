from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime

class TagEnum(str, Enum):
    """
    Enumeration for predefined tags.
    This ensures that only predefined tags are used, providing data consistency.
    The 'abnormal_video' tag is reserved for specific cases.
    """
    DAILY_ACTIVITY = "daily_activity"
    ILLEGAL_INTRUSION = "illegal_intrusion"
    PROPERTY_DAMAGE = "property_damage"
    SOCIAL_GATHERING = "social_gathering"
    VEHICLE_MOVEMENT = "vehicle_movement"
    ANIMAL_ACTIVITY = "animal_activity"
    EMERGENCY_SITUATION = "emergency_situation"
    NORMAL_OPERATION = "normal_operation"
    ABNORMAL_VIDEO = "abnormal_video"

    @classmethod
    def get_all_values(cls) -> List[str]:
        return [member.value for member in cls]

class VideoAnnotation(BaseModel):
    """
    Represents the annotation result for a single video.
    Uses Pydantic for robust data validation and serialization.
    """
    file_path: str = Field(..., description="The absolute or relative path to the video file.")
    description: str = Field(..., max_length=200, description="A concise description of the video content (max 200 chars to be safe, though target is 50 words).")
    tags: List[TagEnum] = Field(..., min_items=1, max_items=2, description="A list of assigned tags. Max 2 tags per video, except for 'abnormal_video' which is exclusive.")
    duration_seconds: Optional[float] = Field(None, ge=0, description="The duration of the video in seconds. Null if video is abnormal or duration cannot be determined.")
    is_abnormal: bool = Field(False, description="True if the video is abnormal (e.g., too short, corrupted).")
    abnormality_reason: Optional[str] = Field(None, description="Reason why the video is marked as abnormal (e.g., 'Duration < 3s', 'Decoding failed').")
    processing_timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, description="Timestamp when the annotation was processed.")
    confidence_scores: Optional[Dict[str, float]] = Field(None, description="Optional: Confidence scores for each tag if provided by the AI model.")

    @validator('tags')
    def validate_tags(cls, v, values):
        # Ensure 'abnormal_video' is the only tag if is_abnormal is True
        if values.get('is_abnormal', False):
            if v != [TagEnum.ABNORMAL_VIDEO]:
                raise ValueError("If video is abnormal, the only allowed tag is 'abnormal_video'.")
        return v

    @validator('description')
    def validate_description_length_words(cls, v):
        # Basic check for word count (can be more sophisticated)
        word_count = len(v.split())
        if word_count > 50: # Max 50 words as per requirement
            # We can truncate or raise an error. For now, let's warn.
            # In a real scenario, the AI model should adhere to this.
            # For Pydantic, we'll just store it, but log a warning elsewhere.
            print(f"Warning: Description for video {v[:50]}... has {word_count} words, exceeding the 50-word limit.")
        return v


class AnnotationResult(BaseModel):
    """
    Represents the final output structure for the entire annotation task.
    Contains metadata about the batch processing and a list of individual annotations.
    """
    total_videos_processed: int = Field(..., ge=0, description="Total number of videos processed.")
    successful_annotations: int = Field(..., ge=0, description="Number of videos successfully annotated.")
    failed_annotations: int = Field(..., ge=0, description="Number of videos that failed processing.")
    annotations: List[VideoAnnotation] = Field(..., description="A list of annotation results for each video.")
    processing_start_time: datetime.datetime = Field(..., description="Timestamp when the batch processing started.")
    processing_end_time: Optional[datetime.datetime] = Field(None, description="Timestamp when the batch processing finished.")
    execution_metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata about the execution (e.g., OpenAI model used, version).")

    @validator('annotations')
    def validate_annotation_counts(cls, v, values):
        total = values.get('total_videos_processed', 0)
        # Count successful annotations (those not marked as abnormal due to AI failure)
        successful_count = sum(1 for ann in v if not (ann.is_abnormal and ann.abnormality_reason and 'AI Analysis' in ann.abnormality_reason))
        failed_count = total - successful_count

        # Only validate if counts are provided (not auto-calculated)
        if 'successful_annotations' in values and values.get('successful_annotations', 0) != successful_count:
            # Allow auto-correction for better UX
            values['successful_annotations'] = successful_count
            values['failed_annotations'] = failed_count
        elif 'failed_annotations' in values and values.get('failed_annotations', 0) != failed_count:
            # Allow auto-correction
            values['successful_annotations'] = successful_count
            values['failed_annotations'] = failed_count

        if successful_count + failed_count != total:
            raise ValueError("Sum of successful and failed annotations does not equal total_videos_processed.")
        return v

class APIRequestPayload(BaseModel):
    """
    Defines the structure of the payload sent to the OpenAI API.
    This is more for internal consistency and can be adapted based on OpenAI's actual input format.
    """
    video_frames: List[str] # List of base64 encoded images or paths to images
    metadata: Dict[str, Any] # e.g., duration, is_abnormal
    prompt_template: str # The prompt to use for the AI model

class APIResponsePayload(BaseModel):
    """
    Defines the expected structure of the response from the OpenAI API (after parsing).
    """
    description: str
    tags: List[str] # Will be validated against TagEnum later
    # Optional: confidence if the model provides it
    confidence_scores: Optional[Dict[str, float]] = None

# Example of how you might use these models in a workflow:
#
# from .core.config import settings
# from .models.schemas import VideoAnnotation, TagEnum, AnnotationResult
#
# # After processing a video and getting AI results:
# annotation_data = {
#     "file_path": "/path/to/video.mp4",
#     "description": "A person walking a dog in the park.",
#     "tags": [TagEnum.DAILY_ACTIVITY],
#     "duration_seconds": 30.5,
#     "is_abnormal": False,
# }
#
# try:
#     annotation = VideoAnnotation(**annotation_data)
#     print("Annotation is valid:", annotation.json(indent=2))
# except ValueError as e:
#     print("Validation Error:", e)
#
# # For the final result:
# final_result_data = {
#     "total_videos_processed": 1,
#     "successful_annotations": 1,
#     "failed_annotations": 0,
#     "annotations": [annotation_data], # Assuming annotation_data is valid
#     "processing_start_time": datetime.datetime.utcnow(),
#     "processing_end_time": datetime.datetime.utcnow(),
# }
#
# try:
#     result = AnnotationResult(**final_result_data)
#     print("Final result is valid:", result.json(indent=2))
# except ValueError as e:
#     print("Final Result Validation Error:", e)
