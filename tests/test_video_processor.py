"""
Unit tests for video processor module.
"""

import pytest
import os
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from src.video_agent.core.video_processor import (
    extract_keyframes,
    process_video_file,
    find_video_files,
    get_video_info
)


@pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not available")
class TestVideoProcessor:
    """Test cases for video processing functions."""
    
    @pytest.fixture
    def temp_video(self):
        """Create a temporary video file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            video_path = f.name
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') # type: ignore
        out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))
        
        for i in range(100):
            frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
            out.write(frame)
        
        out.release()
        
        yield video_path
        
        if os.path.exists(video_path):
            os.remove(video_path)
    
    def test_get_video_info(self, temp_video):
        """Test video info extraction."""
        info = get_video_info(temp_video)
        
        assert info is not None
        assert 'fps' in info
        assert 'frame_count' in info
        assert 'duration_seconds' in info
        assert info['fps'] > 0
        assert info['frame_count'] == 100
        assert info['duration_seconds'] > 0
    
    def test_extract_keyframes(self, temp_video):
        """Test keyframe extraction."""
        keyframes, temp_dir = extract_keyframes(temp_video, num_frames=5)
        
        assert len(keyframes) == 5
        assert all(os.path.exists(kf) for kf in keyframes)
        
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_process_video_file(self, temp_video):
        """Test video file processing."""
        result = process_video_file(temp_video)
        
        assert 'file_path' in result
        assert 'is_abnormal' in result
        assert 'duration_seconds' in result
        assert 'keyframe_paths' in result
        assert result['is_abnormal'] == False
        assert result['duration_seconds'] > 0
        
        if result.get('temp_dir'):
            import shutil
            shutil.rmtree(result['temp_dir'], ignore_errors=True)
    
    def test_find_video_files(self, temp_video):
        """Test video file discovery."""
        video_dir = os.path.dirname(temp_video)
        video_files = find_video_files(video_dir)
        
        assert len(video_files) >= 1
        assert temp_video in video_files


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
