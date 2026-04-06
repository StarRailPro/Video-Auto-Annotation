import argparse
import logging
import sys
import os
import json
import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.video_agent.core.config import settings
from src.video_agent.core.video_processor import find_video_files, process_video_file
from src.video_agent.core.ai_analyzer import analyze_video_with_ai, AIAnalysisError
from src.video_agent.models.schemas import VideoAnnotation, AnnotationResult, TagEnum
from src.video_agent.utils.mcp_client import MCPClient

# Configure logging
def setup_logging():
    """Configures logging based on settings."""
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if settings.log_file:
        handlers.append(logging.FileHandler(settings.log_file))
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=log_format,
        handlers=handlers
    )

logger = logging.getLogger(__name__)

def process_single_video(video_path: str, ai_client: MCPClient) -> VideoAnnotation:
    """
    Processes a single video: extracts info/frames and analyzes with AI.
    This function is designed to be run in a thread pool.
    
    Args:
        video_path: Path to the video file.
        ai_client: A shared AI client instance (OpenAI or MCP) for thread-safety.
        
    Returns:
        A VideoAnnotation object.
    """
    try:
        # Step 1: Video Processing (Preprocessing)
        video_data = process_video_file(video_path)
        
        # Step 2: AI Analysis
        # If video is abnormal, we might skip AI analysis or use a simpler prompt.
        # The ai_analyzer handles this based on video_data.
        ai_result = analyze_video_with_ai(video_data, client=ai_client)
        
        # Step 3: Construct VideoAnnotation
        # Validate tags against TagEnum
        validated_tags = []
        for tag_str in ai_result.get("tags", []):
            try:
                validated_tags.append(TagEnum(tag_str))
            except ValueError:
                logger.warning(f"Tag '{tag_str}' not recognized for {video_path}. Skipping.")
        
        # If video was marked abnormal by video_processor, ensure tag is 'abnormal_video'
        if video_data.get("is_abnormal"):
            validated_tags = [TagEnum.ABNORMAL_VIDEO]
        
        annotation = VideoAnnotation(
            file_path=video_data["file_path"],
            description=ai_result.get("description", "No description generated."),
            tags=validated_tags,
            duration_seconds=video_data.get("duration_seconds"),
            is_abnormal=video_data.get("is_abnormal", False),
            abnormality_reason=video_data.get("abnormality_reason"),
            confidence_scores=ai_result.get("confidence_scores")
        )
        
        return annotation
        
    except AIAnalysisError as e:
        logger.error(f"AI Analysis failed for {video_path}: {e}")
        # Return a failed annotation if AI fails, to keep count correct
        return VideoAnnotation(
            file_path=video_path,
            description="AI Analysis Failed",
            tags=[TagEnum.ABNORMAL_VIDEO], # Treat as abnormal
            duration_seconds=None,
            is_abnormal=True,
            abnormality_reason=f"AI Analysis Error: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing {video_path}: {e}", exc_info=True)
        return VideoAnnotation(
            file_path=video_path,
            description="Processing Failed",
            tags=[TagEnum.ABNORMAL_VIDEO],
            duration_seconds=None,
            is_abnormal=True,
            abnormality_reason=f"Unexpected Error: {e}"
        )

def main(input_directory: str, output_json_path: Optional[str] = None, max_workers: int = 5):
    """
    Main execution function.
    
    Args:
        input_directory: Directory containing video files.
        output_json_path: Path to save the output JSON. If None, uses default.
        max_workers: Maximum number of concurrent threads for video processing.
    """
    start_time = datetime.datetime.utcnow()
    
    logger.info(f"Starting Video Annotation Agent")
    logger.info(f"Input Directory: {input_directory}")
    logger.info(f"Output Directory: {settings.output_json_directory}")
    logger.info(f"Max Workers: {max_workers}")
    logger.info(f"Using MCP (GLM4.6v) for AI analysis")

    # Step 1: Find all video files
    video_files = find_video_files(input_directory)
    
    if not video_files:
        logger.warning("No video files found in the input directory. Exiting.")
        return

    logger.info(f"Found {len(video_files)} video files to process.")

    # Initialize AI Client (shared across threads)
    ai_client = None
    try:
        ai_client = MCPClient(
            api_key=settings.mcp_zai_api_key,
            mode=settings.mcp_zai_mode
        )
        logger.info("MCP Client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MCP Client: {e}")
        return

    # Step 2: Process videos concurrently
    annotations = []
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a future for each video file
        future_to_video = {
            executor.submit(process_single_video, video_path, ai_client): video_path
            for video_path in video_files
        }
        
        # Use tqdm to show progress
        with tqdm(total=len(video_files), desc="Processing Videos", unit="video") as pbar:
            for future in as_completed(future_to_video):
                video_path = future_to_video[future]
                try:
                    annotation = future.result()
                    annotations.append(annotation)
                    
                    # Update progress bar description based on status
                    if annotation.is_abnormal:
                        pbar.set_postfix_str(f"Success: {len(annotations) - failed_count}, Abnormal: {failed_count}")
                    else:
                        pbar.set_postfix_str(f"Success: {len(annotations) - failed_count}, Failed: {failed_count}")
                        
                    pbar.update(1)
                    
                    # Log abnormal videos specifically
                    if annotation.is_abnormal:
                        failed_count += 1
                        logger.debug(f"Marked abnormal: {annotation.file_path} - {annotation.abnormality_reason}")
                        
                except Exception as e:
                    logger.error(f"Exception in future for {video_path}: {e}")
                    failed_count += 1
                    pbar.update(1)

    # Step 3: Aggregate results into AnnotationResult
    end_time = datetime.datetime.utcnow()
    successful_count = len(annotations) - failed_count
    
    try:
        final_result = AnnotationResult(
            total_videos_processed=len(video_files),
            successful_annotations=successful_count,
            failed_annotations=failed_count,
            annotations=annotations,
            processing_start_time=start_time,
            processing_end_time=end_time,
            execution_metadata={
                "ai_provider": "MCP (GLM4.6v)",
                "model": "GLM4.6v",
                "max_workers": max_workers,
                "input_directory": input_directory
            }
        )
        
        # Step 4: Save to JSON
        if output_json_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_json_path = os.path.join(settings.output_json_directory, f"annotation_results_{timestamp}.json")
        
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(final_result.model_dump(mode='json'), f, indent=4, ensure_ascii=False, default=str)
        
        logger.info(f"\nProcessing Complete!")
        logger.info(f"Total Videos: {final_result.total_videos_processed}")
        logger.info(f"Successful: {final_result.successful_annotations}")
        logger.info(f"Failed/Abnormal: {final_result.failed_annotations}")
        logger.info(f"Duration: {end_time - start_time}")
        logger.info(f"Results saved to: {output_json_path}")
        
    except Exception as e:
        logger.error(f"Error aggregating or saving results: {e}", exc_info=True)

if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser(description="Video Annotation Agent - Automated video tagging and description.")
    parser.add_argument(
        "input_directory",
        type=str,
        help="Path to the directory containing video files to process."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional: Path to save the output JSON file. Defaults to data/output/annotation_results_TIMESTAMP.json"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Optional: Number of concurrent worker threads. Default is 5."
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.isdir(args.input_directory):
        logger.error(f"Input directory does not exist: {args.input_directory}")
        sys.exit(1)
    
    try:
        main(args.input_directory, args.output, args.workers)
    except KeyboardInterrupt:
        logger.warning("\nProcessing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}", exc_info=True)
        sys.exit(1)
