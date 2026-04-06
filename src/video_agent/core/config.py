from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional, Union
from pathlib import Path
import os
from dotenv import load_dotenv

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables or .env file.
    Uses Pydantic for validation and type safety.
    """
    # MCP Configuration (GLM4.6v)
    mcp_server_name: str = "zai-mcp-server"
    mcp_zai_api_key: str = ""
    mcp_zai_mode: str = "ZHIPU"

    # Video Processing Configuration
    min_video_duration_seconds: float = 3.0
    max_video_duration_seconds: Optional[Union[float, str]] = None # Optional: for very long videos
    keyframe_extract_count: int = 10 # Number of keyframes to extract per video
    supported_video_extensions: Union[str, List[str]] = [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"]

    # Annotation Configuration
    predefined_tags: List[str] = [
        "daily_activity",
        "illegal_intrusion",
        "property_damage",
        "social_gathering",
        "vehicle_movement",
        "animal_activity",
        "emergency_situation",
        "normal_operation",
        "abnormal_video" # For videos that are too short, corrupted, or unclassifiable
    ]
    max_description_words: int = 50

    # File Paths
    input_video_directory: str = "data/input"
    output_json_directory: str = "data/output"

    # Logging Configuration
    log_level: str = "INFO"
    log_file: Optional[str] = "video_annotation_agent.log"

    @field_validator('max_video_duration_seconds', mode='before')
    @classmethod
    def parse_max_duration(cls, v):
        if v is None or v == '' or (isinstance(v, str) and v.strip() == ''):
            return None
        return float(v)

    @field_validator('supported_video_extensions', mode='before')
    @classmethod
    def parse_supported_video_extensions(cls, v):
        if isinstance(v, str):
            # Parse comma-separated string
            return [ext.strip() for ext in v.split(',')]
        return v

    def __init__(self, **kwargs):
        # Load .env file manually BEFORE calling super().__init__()
        # The .env file is in the project root (VedioAutoMark)
        # __file__ is at src/video_agent/core/config.py
        # We need to go up 4 levels to reach VedioAutoMark
        env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        
        # Fallback: try current directory if the above doesn't work
        if not env_path.exists():
            # Try to find .env in the current working directory or parent directories
            cwd = Path.cwd()
            for parent in [cwd] + list(cwd.parents):
                candidate = parent / ".env"
                if candidate.exists():
                    env_path = candidate
                    break
        
        if env_path.exists():
            load_dotenv(env_path, encoding="utf-8")
        
        # Now initialize parent (Pydantic) which will read from environment variables
        super().__init__(**kwargs)
        # Ensure output directory exists
        os.makedirs(self.output_json_directory, exist_ok=True)
        # Ensure input directory exists (or at least, its parent)
        os.makedirs(self.input_video_directory, exist_ok=True)
        
        # Validate configuration
        logger = __import__('logging').getLogger(__name__)
        if not self.mcp_zai_api_key or self.mcp_zai_api_key == "":
            logger.warning(f"MCP API key is not configured. Please check your .env file at: {env_path}")
        else:
            logger.info("Using MCP (GLM4.6v) for AI analysis")

# Instantiate the settings object
settings = Settings()

# Example of a prompt template that can be used in ai_analyzer.py
# This can be further refined or made more dynamic if needed
PROMPT_TEMPLATE = """
Analyze the provided video frames and metadata to generate a concise description and classify the video.

Video Metadata:
- Duration: {duration_seconds} seconds
- Is Abnormal: {is_abnormal}

Instructions:
1. Description: Provide a brief description of the video content in no more than {max_description_words} English words.
2. Classification: Choose the most appropriate tag(s) from the predefined list: {predefined_tags}.
   - If the video is marked as 'abnormal_video' (e.g., too short, corrupted, or unclassifiable content), please ONLY assign the 'abnormal_video' tag.
   - Otherwise, select up to two most relevant tags.

Predefined Tags: {predefined_tags}

Please respond in a JSON format with the following structure:
{{
    "description": "Your video description here.",
    "tags": ["tag1", "tag2"]
}}
"""
