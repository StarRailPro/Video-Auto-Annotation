import cv2
import os
import logging
import tempfile
import shutil
import hashlib
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from pathlib import Path

# Assuming config.py and schemas.py are in the parent directory structure
from ..core.config import settings
from ..models.schemas import TagEnum

# Configure logging
logger = logging.getLogger(__name__)

class VideoProcessingError(Exception):
    """Custom exception for video processing errors."""
    pass

def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Retrieves basic information about a video file using OpenCV.
    Handles potential errors during video file reading.

    Args:
        video_path: The path to the video file.

    Returns:
        A dictionary containing video information (duration, frame_count, fps, width, height).
        Returns an empty dictionary if the video cannot be opened or an error occurs.
    """
    video_info = {}
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Could not open video file: {video_path}")
            return {}

        # Get frame count and FPS
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Calculate duration
        duration = frame_count / fps if fps > 0 else 0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        video_info = {
            "duration_seconds": duration,
            "frame_count": frame_count,
            "fps": fps,
            "width": width,
            "height": height,
        }
        logger.debug(f"Video info for {video_path}: {video_info}")
    except cv2.error as e:
        logger.error(f"OpenCV error while reading {video_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while reading {video_path}: {e}")
    finally:
        if cap is not None:
            cap.release()
    return video_info

def is_video_abnormal(video_path: str, video_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Checks if a video is abnormal based on its duration and other factors.
    A video is considered abnormal if:
    - It cannot be opened (video_info is empty).
    - Its duration is less than `min_video_duration_seconds` from settings.

    Args:
        video_path: The path to the video file (for logging purposes).
        video_info: A dictionary containing video information from `get_video_info`.

    Returns:
        A tuple (is_abnormal: bool, reason: Optional[str]).
    """
    if not video_info:
        return True, "Could not open or decode video file."

    duration = video_info.get("duration_seconds", 0)
    if duration < settings.min_video_duration_seconds:
        return True, f"Duration {duration:.2f}s is less than minimum {settings.min_video_duration_seconds}s."

    return False, None

def extract_keyframes(
    video_path: str, 
    num_frames: int,
    output_dir: Optional[str] = None
) -> Tuple[List[str], Optional[str]]:
    """
    提取关键帧
    
    Args:
        video_path: 视频文件路径
        num_frames: 要提取的关键帧数量
        output_dir: 输出目录（如果为None，使用临时目录）
    
    Returns:
        (keyframe_paths, temp_dir):
            - keyframe_paths: 关键帧文件路径列表
            - temp_dir: 临时目录路径（如果使用了临时目录），否则为None
    
    Example:
        # 使用临时目录（推荐）
        keyframes, temp_dir = extract_keyframes(video_path, 10)
        try:
            # 使用关键帧...
            pass
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        # 使用指定目录
        keyframes, _ = extract_keyframes(video_path, 10, output_dir="/custom/dir")
    """
    keyframe_paths: List[str] = []
    cap = None
    use_temp_dir = output_dir is None
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Could not open video for keyframe extraction: {video_path}")
            return [], None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if total_frames == 0 or num_frames == 0:
            logger.warning(f"Video {video_path} has 0 frames or num_frames is 0. Skipping extraction.")
            return [], None

        interval = max(1, total_frames // num_frames) if num_frames > 0 else total_frames
        frame_indices = list(range(0, total_frames, interval))[:num_frames]

        # 创建输出目录
        if use_temp_dir:
            output_dir = tempfile.mkdtemp(prefix="keyframes_")
            logger.debug(f"Created temporary directory: {output_dir}")
        else:
            if output_dir is None:
                output_dir = tempfile.mkdtemp(prefix="keyframes_")
                use_temp_dir = True
            else:
                os.makedirs(output_dir, exist_ok=True)

        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                # 使用唯一文件名，避免并发冲突
                video_hash = hashlib.md5(video_path.encode()).hexdigest()[:8]
                keyframe_filename = f"keyframe_{video_hash}_{i+1:03d}.jpg"
                keyframe_path = os.path.join(output_dir, keyframe_filename)
                cv2.imwrite(keyframe_path, frame)
                keyframe_paths.append(keyframe_path)
            else:
                logger.warning(f"Could not read frame at index {frame_idx} from {video_path}")
        
        logger.info(f"Extracted {len(keyframe_paths)} keyframes to {output_dir}")
        return keyframe_paths, output_dir if use_temp_dir else None
        
    except cv2.error as e:
        logger.error(f"OpenCV error during keyframe extraction for {video_path}: {e}")
        return [], None
    except Exception as e:
        logger.error(f"Unexpected error during keyframe extraction for {video_path}: {e}")
        return [], None
    finally:
        if cap is not None:
            cap.release()

def process_video_file(video_path: str) -> Dict[str, Any]:
    """
    处理单个视频文件
    
    Args:
        video_path: 视频文件路径
    
    Returns:
        处理结果字典，包含：
        - file_path: 视频文件路径
        - is_abnormal: 是否异常
        - abnormality_reason: 异常原因
        - duration_seconds: 视频时长
        - keyframe_paths: 关键帧路径列表
        - temp_dir: 临时目录路径（需要调用者清理）
        - video_info: 视频信息
    """
    result: Dict[str, Any] = {
        "file_path": video_path,
        "is_abnormal": False,
        "abnormality_reason": None,
        "duration_seconds": None,
        "keyframe_paths": [],
        "temp_dir": None,
        "video_info": {},
    }

    logger.info(f"Processing video: {video_path}")

    # Step 1: Get video information
    video_info = get_video_info(video_path)
    result["video_info"] = video_info

    # Step 2: Check for abnormalities
    is_abnormal, reason = is_video_abnormal(video_path, video_info)
    result["is_abnormal"] = is_abnormal
    result["abnormality_reason"] = reason

    if is_abnormal:
        logger.warning(f"Video {video_path} is abnormal. Reason: {reason}")
        return result

    # Step 3: Extract keyframes (only if not abnormal)
    duration = video_info.get("duration_seconds", 0)
    effective_num_frames = min(settings.keyframe_extract_count, max(1, int(duration / 2)))
    if duration < settings.min_video_duration_seconds * 2 and duration >= settings.min_video_duration_seconds:
        effective_num_frames = max(1, settings.keyframe_extract_count // 2)

    keyframes, temp_dir = extract_keyframes(video_path, effective_num_frames)
    result["keyframe_paths"] = keyframes
    result["temp_dir"] = temp_dir
    result["duration_seconds"] = duration

    if not keyframes and not is_abnormal:
        logger.warning(f"Failed to extract keyframes for {video_path}, though video was not marked abnormal.")

    logger.info(f"Successfully processed video: {video_path}. Extracted {len(keyframes)} keyframes.")
    return result

def find_video_files(directory: str) -> List[str]:
    """
    Recursively finds all supported video files in a given directory.

    Args:
        directory: The path to the directory to search.

    Returns:
        A list of full paths to video files.
    """
    video_files: List[str] = []
    if not os.path.isdir(directory):
        logger.error(f"Input directory not found: {directory}")
        return video_files

    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in settings.supported_video_extensions):
                video_files.append(os.path.join(root, file))
    logger.info(f"Found {len(video_files)} video files in {directory}.")
    return video_files

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Create a dummy video for testing (optional)
    # You would replace this with actual video paths
    # For now, let's assume 'data/input' has some videos or we pass a specific path.
    
    # Ensure dummy input/output directories for testing
    test_input_dir = settings.input_video_directory
    test_output_dir = settings.output_json_directory
    os.makedirs(test_input_dir, exist_ok=True)
    os.makedirs(os.path.join(test_output_dir, "temp_keyframes"), exist_ok=True)

    # Define fourcc codec for test videos
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # type: ignore

    # If no videos in input, create a dummy one for testing
    dummy_video_path = os.path.join(test_input_dir, "dummy_video.mp4")
    if not os.path.exists(dummy_video_path):
        logger.info("Creating a dummy video for testing...")
        # Create a dummy video using OpenCV (requires FFmpeg backend)
        out = cv2.VideoWriter(dummy_video_path, fourcc, 20.0, (640, 480))
        for i in range(100): # 100 frames
            frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
            out.write(frame)
        out.release()
        logger.info(f"Dummy video created at {dummy_video_path}")

    # Also create a very short video
    short_video_path = os.path.join(test_input_dir, "very_short_video.mp4")
    if not os.path.exists(short_video_path):
        logger.info("Creating a very short video for testing...")
        out = cv2.VideoWriter(short_video_path, fourcc, 20.0, (640, 480))
        out.write(np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)) # 1 frame
        out.release()
        logger.info(f"Short dummy video created at {short_video_path}")

    # Also create a corrupted video file (e.g., just text)
    corrupted_video_path = os.path.join(test_input_dir, "corrupted_video.mp4")
    if not os.path.exists(corrupted_video_path):
        logger.info("Creating a corrupted video file for testing...")
        with open(corrupted_video_path, "w") as f:
            f.write("This is not a valid video file.")
        logger.info(f"Corrupted dummy file created at {corrupted_video_path}")


    video_files_to_process = find_video_files(test_input_dir)

    if not video_files_to_process:
        logger.warning("No video files found in the input directory for testing.")
    else:
        for video_file in video_files_to_process:
            logger.info(f"\n--- Processing: {video_file} ---")
            processed_data = process_video_file(video_file)
            logger.info(f"--- Result for {video_file} ---")
            logger.info(f"  Is Abnormal: {processed_data['is_abnormal']}")
            logger.info(f"  Reason: {processed_data['abnormality_reason']}")
            logger.info(f"  Duration: {processed_data['duration_seconds']}")
            logger.info(f"  Keyframes Extracted: {len(processed_data['keyframe_paths'])}")
            # print(processed_data) # For more detailed inspection
