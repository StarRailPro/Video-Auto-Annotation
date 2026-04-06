"""
Unit tests for configuration module.
"""

import pytest
import os
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.video_agent.core.config import Settings


class TestConfig:
    """Test cases for configuration."""
    
    def test_settings_initialization(self):
        """Test that settings can be initialized."""
        settings = Settings()
        
        assert settings is not None
        assert hasattr(settings, 'mcp_zai_api_key')
        assert hasattr(settings, 'input_video_directory')
        assert hasattr(settings, 'output_json_directory')
    
    def test_find_env_file(self):
        """Test .env file discovery."""
        env_path = Settings._find_env_file()
        
        if env_path:
            assert env_path.exists()
            assert env_path.name == '.env'
    
    def test_default_values(self):
        """Test default configuration values."""
        settings = Settings()
        
        assert settings.min_video_duration_seconds == 3.0
        assert settings.keyframe_extract_count == 10
        assert settings.max_description_words == 50
        assert settings.log_level == "INFO"
    
    def test_supported_video_extensions(self):
        """Test supported video extensions."""
        settings = Settings()
        
        assert isinstance(settings.supported_video_extensions, list)
        assert '.mp4' in settings.supported_video_extensions
        assert '.mov' in settings.supported_video_extensions
    
    def test_directories_creation(self):
        """Test that directories are created."""
        settings = Settings()
        
        assert os.path.exists(settings.input_video_directory)
        assert os.path.exists(settings.output_json_directory)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
