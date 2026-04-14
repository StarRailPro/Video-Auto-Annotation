import json
import logging
import os
import subprocess
import asyncio
import time
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    pass


class MCPClient:

    DEFAULT_RESPONSE_TIMEOUT = 300
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(
        self,
        api_key: str,
        mode: str = "ZHIPU",
        response_timeout: Optional[int] = None,
    ):
        self.api_key = api_key
        self.mode = mode
        self.response_timeout = response_timeout or self.DEFAULT_RESPONSE_TIMEOUT
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._request_id = 0
        self._is_initialized = False

        logger.info(f"MCP Client initializing (timeout: {self.response_timeout}s)")
        self._initialize_process()
        self._handshake()

    def _initialize_process(self):
        import shutil

        npx_path = shutil.which("npx")
        if not npx_path:
            raise MCPClientError("npx not found. Please install Node.js.")

        env = os.environ.copy()
        env["Z_AI_API_KEY"] = self.api_key
        env["Z_AI_MODE"] = self.mode

        logger.info("Starting MCP server process...")
        logger.info(f"Mode: {self.mode}")

        try:
            self.process = subprocess.Popen(
                [npx_path, "-y", "@z_ai/mcp-server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                shell=False,
                bufsize=1,
            )

            time.sleep(1)

            if self.process.poll() is not None:
                stderr_output = (
                    self.process.stderr.read()
                    if self.process.stderr
                    else "No stderr available"
                )
                raise MCPClientError(
                    f"MCP server failed to start. Stderr: {stderr_output}"
                )

            logger.info(f"MCP server started (PID: {self.process.pid})")

        except MCPClientError:
            raise
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise MCPClientError(f"Failed to initialize MCP server: {e}")

    def _handshake(self):
        self._request_id += 1
        init_request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "video-annotation-client", "version": "1.0.0"},
            },
        }

        response = self._send_and_read(init_request)
        if "error" in response:
            raise MCPClientError(
                f"MCP handshake initialize failed: {response['error']}"
            )

        logger.info("MCP handshake initialize succeeded")

        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        self._write_message(initialized_notification)

        self._is_initialized = True
        logger.info("MCP handshake completed")

    def _write_message(self, message: Dict[str, Any]):
        if self.process is None or self.process.stdin is None:
            raise MCPClientError("MCP process stdin not available")

        msg_str = json.dumps(message) + "\n"
        logger.debug(f"Sending: {msg_str.strip()}")
        self.process.stdin.write(msg_str)
        self.process.stdin.flush()

    def _read_response(self, expected_id: Optional[int] = None) -> Dict[str, Any]:
        if self.process is None or self.process.stdout is None:
            raise MCPClientError("MCP process stdout not available")

        stdout = self.process.stdout
        deadline = time.time() + self.response_timeout

        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise MCPClientError(f"Response timeout ({self.response_timeout}s)")

            response_str = None
            read_error = None

            def read_line():
                nonlocal response_str, read_error
                try:
                    response_str = stdout.readline()
                except Exception as e:
                    read_error = e

            read_thread = threading.Thread(target=read_line, daemon=True)
            read_thread.start()
            read_thread.join(timeout=min(remaining, 30))

            if read_thread.is_alive():
                raise MCPClientError(f"Response timeout ({self.response_timeout}s)")

            if read_error:
                raise MCPClientError(f"Read error: {read_error}")

            if not response_str:
                raise MCPClientError("No response from MCP server")

            response_str = response_str.strip()
            if not response_str:
                continue

            try:
                response = json.loads(response_str)
            except json.JSONDecodeError:
                logger.debug(f"Skipping non-JSON line: {response_str[:200]}")
                continue

            if "method" in response and "id" not in response:
                logger.debug(f"Skipping notification: {response.get('method')}")
                continue

            if expected_id is not None and response.get("id") != expected_id:
                logger.debug(
                    f"Skipping response with id {response.get('id')}, expected {expected_id}"
                )
                continue

            return response

        raise MCPClientError(f"Response timeout ({self.response_timeout}s)")

    def _send_and_read(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self._write_message(request)
        return self._read_response(expected_id=request.get("id"))

    def _ensure_process_alive(self):
        if self.process is None or self.process.poll() is not None:
            logger.warning("MCP process died, restarting...")
            self._initialize_process()
            self._handshake()

    def _restart_process(self):
        logger.info("Restarting MCP server process...")
        self._terminate_process()
        self._initialize_process()
        self._handshake()
        logger.info("MCP server restarted")

    def _terminate_process(self):
        if self.process:
            logger.info(f"Terminating MCP process (PID: {self.process.pid})")

            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("MCP process terminated gracefully")

            except subprocess.TimeoutExpired:
                logger.warning("MCP process did not terminate gracefully, killing...")
                self.process.kill()
                self.process.wait()
                logger.info("MCP process killed")

            except Exception as e:
                logger.error(f"Error terminating MCP process: {e}")
                try:
                    self.process.kill()
                    self.process.wait()
                except Exception:
                    pass

            finally:
                self.process = None
                self._is_initialized = False

    def analyze_video(
        self,
        prompt: str,
        image_paths: List[str],
        max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        max_retries = max_retries or self.MAX_RETRIES
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                result = self._analyze_video_once(prompt, image_paths)

                if attempt > 1:
                    logger.info(
                        f"Request succeeded on attempt {attempt}/{max_retries}"
                    )
                return result

            except MCPClientError as e:
                last_error = e

                if attempt < max_retries:
                    logger.warning(
                        f"Attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {self.RETRY_DELAY}s..."
                    )
                    time.sleep(self.RETRY_DELAY)
                    self._restart_process()
                else:
                    logger.error(
                        f"All {max_retries} attempts failed. Last error: {e}"
                    )

        raise MCPClientError(
            f"Failed after {max_retries} retries. Last error: {last_error}"
        )

    def _analyze_video_once(
        self,
        prompt: str,
        image_paths: List[str],
    ) -> Dict[str, Any]:
        with self._lock:
            try:
                self._ensure_process_alive()

                self._request_id += 1
                request = {
                    "jsonrpc": "2.0",
                    "id": self._request_id,
                    "method": "tools/call",
                    "params": {
                        "name": "analyze_image",
                        "arguments": {
                            "image_source": image_paths[0] if image_paths else "",
                            "prompt": prompt,
                        },
                    },
                }

                logger.info(f"Sending analyze request (ID: {self._request_id})")

                response = self._send_and_read(request)

                if "error" in response:
                    error = response["error"]
                    error_msg = (
                        error.get("message", "Unknown error")
                        if isinstance(error, dict)
                        else str(error)
                    )
                    raise MCPClientError(f"Server error: {error_msg}")

                if "result" not in response:
                    logger.warning(
                        f"No 'result' in response. Keys: {list(response.keys())}"
                    )
                    logger.debug(f"Full response: {json.dumps(response, indent=2)[:500]}")
                    raise MCPClientError(
                        f"No 'result' field in MCP response. Got keys: {list(response.keys())}"
                    )

                logger.info("Analysis completed successfully")
                return response["result"]

            except MCPClientError:
                raise
            except Exception as e:
                logger.error(f"MCP analysis failed: {e}")
                raise MCPClientError(f"MCP analysis failed: {e}")

    def analyze_video_sync(
        self,
        prompt: str,
        image_paths: List[str],
        max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self.analyze_video(prompt, image_paths, max_retries)

    def close(self):
        self._terminate_process()
        logger.info("MCP client closed")

    def __del__(self):
        self._terminate_process()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


async def test_mcp_connection() -> bool:
    try:
        client = MCPClient(
            api_key=os.environ.get("Z_AI_API_KEY", "test"),
            mode=os.environ.get("Z_AI_MODE", "ZHIPU"),
        )
        client.close()
        return True
    except Exception as e:
        logger.error(f"MCP connection test failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    if asyncio.run(test_mcp_connection()):
        print("MCP server is accessible")
    else:
        print("MCP server is not accessible")
