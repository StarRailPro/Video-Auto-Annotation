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
            return [ext.strip() for ext in v.split(',')]
        return v

    @staticmethod
    def _find_env_file() -> Optional[Path]:
        """
        查找.env文件，使用多种策略
        
        查找策略（按优先级）：
        1. 环境变量 DOTENV_PATH
        2. 从当前文件向上查找，直到找到项目根目录标记
        3. 从当前工作目录向上查找
        4. 返回None（使用环境变量）
        
        Returns:
            .env文件的路径，如果找不到则返回None
        """
        logger = __import__('logging').getLogger(__name__)
        
        env_var_path = os.getenv('DOTENV_PATH')
        if env_var_path:
            env_path = Path(env_var_path)
            if env_path.exists():
                logger.debug(f"Found .env via DOTENV_PATH: {env_path}")
                return env_path
            else:
                logger.warning(f"DOTENV_PATH set but file not found: {env_path}")
        
        current_file = Path(__file__).resolve()
        for parent in current_file.parents:
            candidate = parent / ".env"
            if candidate.exists():
                logger.debug(f"Found .env by walking up from config.py: {candidate}")
                return candidate
            
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                logger.debug(f"Reached project root at: {parent}")
                break
        
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            candidate = parent / ".env"
            if candidate.exists():
                logger.debug(f"Found .env by walking up from cwd: {candidate}")
                return candidate
        
        logger.debug("No .env file found, will use environment variables only")
        return None

    def __init__(self, **kwargs):
        env_path = self._find_env_file()
        
        if env_path and env_path.exists():
            load_dotenv(env_path, encoding="utf-8")
            logger = __import__('logging').getLogger(__name__)
            logger.info(f"✓ Loaded .env file from: {env_path}")
        
        super().__init__(**kwargs)
        os.makedirs(self.output_json_directory, exist_ok=True)
        os.makedirs(self.input_video_directory, exist_ok=True)
        
        logger = __import__('logging').getLogger(__name__)
        if not self.mcp_zai_api_key or self.mcp_zai_api_key == "":
            logger.warning(f"MCP API key is not configured. Please check your .env file")
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
