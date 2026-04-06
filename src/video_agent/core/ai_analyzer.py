import os
import logging
import base64
from typing import List, Dict, Any, Optional
from pathlib import Path

# Assuming config.py and schemas.py are in the parent directory structure
from ..core.config import settings, PROMPT_TEMPLATE
from ..models.schemas import TagEnum, APIResponsePayload, VideoAnnotation
from ..utils.mcp_client import MCPClient, MCPClientError

# Configure logging
logger = logging.getLogger(__name__)

class AIAnalysisError(Exception):
    """Custom exception for AI analysis errors."""
    pass

def encode_image(image_path: str) -> str:
    """
    Encodes an image file to a base64 string.
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        raise AIAnalysisError(f"Could not encode image: {image_path}") from e

def analyze_with_mcp(
    video_data: Dict[str, Any],
    client: MCPClient
) -> Dict[str, Any]:
    """
    Analyze video using MCP (GLM4.6v).
    
    Args:
        video_data: Video processing data
        client: MCP client instance
        
    Returns:
        Dictionary with analysis results
    """
    # Prepare prompt
    prompt = PROMPT_TEMPLATE.format(
        duration_seconds=video_data.get("duration_seconds", "N/A"),
        is_abnormal=str(video_data.get("is_abnormal", False)),
        max_description_words=settings.max_description_words,
        predefined_tags=", ".join(TagEnum.get_all_values())
    )

    # Get image paths (MCP handles base64 encoding internally)
    image_paths = video_data.get("keyframe_paths", [])
    
    if not image_paths and not video_data.get("is_abnormal"):
        logger.warning(f"No keyframes for {video_data['file_path']}. Analyzing without images.")

    try:
        logger.info(f"Sending MCP request for: {video_data['file_path']}")
        result = client.analyze_video_sync(prompt, image_paths)
        
        # Parse MCP response - it's in nested format
        # Result format: {'content': [{'type': 'text', 'text': '{"description": "...", "tags": [...]}'}]}
        import json as json_parser
        
        description = ""
        tags = []
        
        # Extract text content from nested structure
        if "content" in result and len(result["content"]) > 0:
            content = result["content"][0]
            if content.get("type") == "text":
                text_content = content.get("text", "")
                logger.info(f"Raw text content from MCP: {text_content[:200]}...")
                
                # Try to parse JSON from the text content
                try:
                    parsed_json = json_parser.loads(text_content)
                    description = parsed_json.get("description", "")
                    tags = parsed_json.get("tags", [])
                    logger.info(f"Parsed description: {description[:100]}...")
                    logger.info(f"Parsed tags: {tags}")
                except json_parser.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from MCP response: {e}")
                    # Fallback: use the text content as description
                    description = text_content.strip()
                    tags = []
        
        # Fallback if no content
        if not description:
            description = result.get("description", "")
            tags = result.get("tags", [])
        
        api_response_payload: APIResponsePayload = {
            "description": description,
            "tags": tags,
            "confidence_scores": result.get("confidence_scores")
        }
        
        return api_response_payload
        
    except MCPClientError as e:
        logger.error(f"MCP error: {e}")
        raise AIAnalysisError(f"MCP error: {e}") from e
    except Exception as e:
        logger.error(f"MCP analysis failed: {e}")
        raise AIAnalysisError(f"MCP analysis failed: {e}") from e

def analyze_video_with_ai(
    video_data: Dict[str, Any],
    client: Optional[MCPClient] = None
) -> Dict[str, Any]:
    """
    Analyzes video data using MCP (GLM4.6v).

    Args:
        video_data: A dictionary containing processed video information from video_processor.
                    Expected keys:
                    - "file_path": str
                    - "is_abnormal": bool
                    - "abnormality_reason": Optional[str]
                    - "duration_seconds": Optional[float]
                    - "keyframe_paths": List[str]
        client: An optional client instance. If None, a new one is created.

    Returns:
        A dictionary containing the AI analysis result:
        - "description": str (max 50 words)
        - "tags": List[str] (from predefined TagEnum)
        - "confidence_scores": Optional[Dict[str, float]]
        - "raw_api_response": Optional[dict] (The raw response from AI provider)
    """
    # Initialize client if not provided
    if client is None:
        try:
            client = MCPClient(
                api_key=settings.mcp_zai_api_key,
                mode=settings.mcp_zai_mode
            )
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            raise AIAnalysisError("MCP client initialization failed.") from e

    # Call MCP analysis function
    try:
        api_response_payload = analyze_with_mcp(video_data, client)  # type: ignore
    except AIAnalysisError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during AI analysis for {video_data['file_path']}: {e}")
        raise AIAnalysisError(f"Unexpected AI analysis error: {e}") from e

    # Validate and normalize tags
    validated_tags: List[str] = []
    for tag in api_response_payload.get("tags", []):
        if tag in TagEnum.get_all_values():
            validated_tags.append(tag)
        else:
            logger.warning(f"Tag '{tag}' not in predefined set. Skipping.")
    
    # Special handling for abnormal videos
    if video_data.get("is_abnormal"):
        if TagEnum.ABNORMAL_VIDEO.value not in validated_tags:
            logger.info(f"Ensuring 'abnormal_video' tag for abnormal video: {video_data['file_path']}")
            validated_tags = [TagEnum.ABNORMAL_VIDEO.value]
        else:
            validated_tags = [TagEnum.ABNORMAL_VIDEO.value]

    # Ensure at least one tag if not abnormal
    if not video_data.get("is_abnormal") and not validated_tags:
        logger.warning(f"No valid tags assigned to {video_data['file_path']}. Assigning default.")
        validated_tags = [TagEnum.NORMAL_OPERATION.value]

    result = {
        "description": api_response_payload.get("description", ""),
        "tags": validated_tags,
        "confidence_scores": api_response_payload.get("confidence_scores"),
        "raw_api_response": api_response_payload
    }
    
    logger.info(f"Successfully analyzed: {video_data['file_path']}")
    return result

if __name__ == '__main__':
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Test with MCP
    logger.info("Testing with MCP (GLM4.6v)")
    try:
        client = MCPClient(settings.mcp_zai_api_key, settings.mcp_zai_mode)
        # Test data
        test_video_data = {
            "file_path": "test_video.mp4",
            "is_abnormal": False,
            "duration_seconds": 10.0,
            "keyframe_paths": []
        }
        result = analyze_video_with_ai(test_video_data, client)
        logger.info(f"MCP Test Result: {result}")
    except Exception as e:
        logger.error(f"MCP test failed: {e}")
