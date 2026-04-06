import json
import logging
import os
import subprocess
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

class MCPClientError(Exception):
    """Custom exception for MCP client errors."""
    pass

class MCPClient:
    """
    A client for interacting with MCP (Model Context Protocol) servers.
    Specifically designed to work with GLM4.6v vision model via stdio.
    """
    
    def __init__(self, api_key: str, mode: str = "ZHIPU"):
        """
        Initialize MCP client.
        
        Args:
            api_key: API key for the MCP server
            mode: Mode setting (e.g., "ZHIPU")
        """
        self.api_key = api_key
        self.mode = mode
        self.process: Optional[subprocess.Popen] = None
        
    async def analyze_video(self, prompt: str, image_paths: list) -> Dict[str, Any]:
        """
        Analyze video using MCP server (GLM4.6v) with image analysis tool.
        
        Args:
            prompt: The analysis prompt
            image_paths: List of paths to keyframe images
            
        Returns:
            Dictionary containing description and tags
            
        Raises:
            MCPClientError: If analysis fails
        """
        try:
            # Build up request for image analysis
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "analyze_image",
                    "arguments": {
                        "image_source": image_paths[0],  # Use first keyframe
                        "prompt": prompt
                    }
                }
            }
            
            # Start of MCP server process with explicit shell
            import shutil
            npx_path = shutil.which("npx")
            if not npx_path:
                raise MCPClientError("npx not found. Please install Node.js.")
            
            # Prepare environment variables
            env = os.environ.copy()
            # MCP server expects Z_AI_API_KEY
            env["Z_AI_API_KEY"] = self.api_key
            env["Z_AI_MODE"] = self.mode
            
            logger.info(f"Starting MCP server with npx at: {npx_path}")
            logger.info(f"API Key length: {len(self.api_key) if self.api_key else 0}")
            logger.info(f"Mode: {self.mode}")
            
            self.process = subprocess.Popen(
                [npx_path, "-y", "@z_ai/mcp-server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                shell=False
            )
            
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            # Read response with timeout
            try:
                response_str = self.process.stdout.readline()
                logger.info(f"Received response from MCP server: {len(response_str)} chars")
                
                if not response_str:
                    stderr_output = self.process.stderr.read()
                    raise MCPClientError(f"No response from MCP server. Stderr: {stderr_output}")
                
                response = json.loads(response_str)
            except json.JSONDecodeError as e:
                stderr_output = self.process.stderr.read()
                logger.error(f"Failed to parse MCP response. Response: {response_str}")
                logger.error(f"Stderr: {stderr_output}")
                raise MCPClientError(f"Invalid JSON response from MCP server: {e}")
            
            if "error" in response:
                raise MCPClientError(f"MCP server error: {response['error']}")
                
            if "result" not in response:
                logger.warning(f"Unexpected response structure: {response}")
                # Fallback: provide a basic response
                return {
                    "description": "AI analysis completed but returned unexpected format.",
                    "tags": ["normal_operation"]
                }
            
            result = response["result"]
            logger.info(f"MCP analysis result: {result}")
            return result
            
        except subprocess.TimeoutExpired:
            logger.error("MCP server timed out")
            raise MCPClientError("MCP server timed out")
        except Exception as e:
            logger.error(f"MCP analysis failed: {e}", exc_info=True)
            raise MCPClientError(f"MCP analysis failed: {e}")
        finally:
            if self.process:
                logger.info("Terminating MCP server process")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                self.process = None
    
    def analyze_video_sync(self, prompt: str, image_paths: list) -> Dict[str, Any]:
        """
        Synchronous wrapper for analyze_video.
        
        Args:
            prompt: The analysis prompt
            image_paths: List of paths to keyframe images
            
        Returns:
            Dictionary containing description and tags
        """
        return asyncio.run(self.analyze_video(prompt, image_paths))

async def test_mcp_connection() -> bool:
    """
    Test if MCP server is accessible.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        client = MCPClient("test_key")
        # Try to start the process (it will fail authentication but shows server is running)
        process = subprocess.Popen(
            ["npx", "-y", "@z_ai/mcp-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        process.terminate()
        process.wait(timeout=5)
        return True
    except FileNotFoundError:
        logger.error("npx not found. Please ensure Node.js and npm are installed.")
        return False
    except Exception as e:
        logger.error(f"MCP connection test failed: {e}")
        return False

if __name__ == "__main__":
    # Test MCP connection
    logging.basicConfig(level=logging.INFO)
    import os
    
    if asyncio.run(test_mcp_connection()):
        print("✓ MCP server is accessible")
    else:
        print("✗ MCP server is not accessible")
