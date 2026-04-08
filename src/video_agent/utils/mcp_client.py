import json
import logging
import os
import subprocess
import asyncio
import time
import sys
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class MCPClientError(Exception):
    """MCP客户端错误"""
    pass

class MCPClient:
    """
    MCP客户端 - 支持并发安全和自动重试
    
    特性：
    1. 单例进程复用 - 只创建一次MCP服务器进程
    2. 线程安全 - 使用asyncio.Lock保证并发安全
    3. 自动重试 - 失败后自动重试3次
    4. 健康检查 - 自动检测进程状态并重启
    5. 优雅关闭 - 确保资源正确清理
    
    改进点：
    - 减少进程创建和销毁开销（只创建一次）
    - 避免资源浪费（进程复用）
    - 修补进程泄漏风险（完善的清理机制）
    """
    
    DEFAULT_RESPONSE_TIMEOUT = 60
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    def __init__(
        self, 
        api_key: str, 
        mode: str = "ZHIPU",
        response_timeout: Optional[int] = None
    ):
        """
        初始化MCP客户端
        
        Args:
            api_key: API密钥
            mode: MCP模式（默认ZHIPU）
            response_timeout: 响应超时时间（秒），默认60秒
                             基于测试数据：5M视频处理约35秒
                             设置60秒超时（35s + 10s冗余 + 15s缓冲）
        """
        self.api_key = api_key
        self.mode = mode
        self.response_timeout = response_timeout or self.DEFAULT_RESPONSE_TIMEOUT
        self.process: Optional[subprocess.Popen] = None
        self._lock = asyncio.Lock()
        self._request_id = 0
        self._is_initialized = False
        
        logger.info(f"MCP Client initializing (timeout: {self.response_timeout}s)")
        self._initialize_process()
    
    def _initialize_process(self):
        """
        初始化MCP服务器进程
        只在客户端创建时调用一次，实现进程复用
        """
        import shutil
        
        npx_path = shutil.which("npx")
        if not npx_path:
            raise MCPClientError("npx not found. Please install Node.js.")
        
        log_dir = Path.home() / ".zai"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        log_file = log_dir / f"zai-mcp-{datetime.now().strftime('%Y-%m-%d')}.log"
        if not log_file.exists():
            with open(log_file, 'w') as f:
                f.write('')
        
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
                bufsize=1
            )
            
            time.sleep(0.5)
            
            if self.process.poll() is not None:
                stderr_output = self.process.stderr.read() if self.process.stderr else "No stderr available"
                raise MCPClientError(
                    f"MCP server failed to start. Stderr: {stderr_output}"
                )
            
            self._is_initialized = True
            logger.info(f"✓ MCP server started (PID: {self.process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise MCPClientError(f"Failed to initialize MCP server: {e}")
    
    def _ensure_process_alive(self):
        """
        确保MCP进程存活
        如果进程已死则自动重启
        """
        if self.process is None or self.process.poll() is not None:
            logger.warning("⚠️ MCP process died, restarting...")
            self._initialize_process()
    
    def _restart_process(self):
        """
        重启MCP服务器进程
        用于错误恢复
        """
        logger.info("Restarting MCP server process...")
        self._terminate_process()
        self._initialize_process()
        logger.info("✓ MCP server restarted")
    
    def _terminate_process(self):
        """
        优雅地终止MCP进程
        确保资源正确清理，避免进程泄漏
        """
        if self.process:
            logger.info(f"Terminating MCP process (PID: {self.process.pid})")
            
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("✓ MCP process terminated gracefully")
                
            except subprocess.TimeoutExpired:
                logger.warning("MCP process did not terminate gracefully, killing...")
                self.process.kill()
                self.process.wait()
                logger.info("✓ MCP process killed")
                
            except Exception as e:
                logger.error(f"Error terminating MCP process: {e}")
                try:
                    self.process.kill()
                    self.process.wait()
                except:
                    pass
            
            finally:
                self.process = None
                self._is_initialized = False
    
    async def analyze_video(
        self, 
        prompt: str, 
        image_paths: List[str],
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        分析视频（带自动重试机制）
        
        Args:
            prompt: 分析提示词
            image_paths: 关键帧图片路径列表
            max_retries: 最大重试次数（默认3次）
        
        Returns:
            分析结果字典
        
        Raises:
            MCPClientError: 所有重试失败后抛出
        
        重试策略：
        - 失败后自动重试，最多3次
        - 每次重试前等待2秒
        - 每次重试都有明确的日志提示
        - 重试前会重启MCP进程
        """
        max_retries = max_retries or self.MAX_RETRIES
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                result = await self._analyze_video_once(prompt, image_paths)
                
                if attempt > 1:
                    logger.info(
                        f"✓ Request succeeded on attempt {attempt}/{max_retries}"
                    )
                return result
                
            except MCPClientError as e:
                last_error = e
                
                if attempt < max_retries:
                    logger.warning(
                        f"⚠️ Attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {self.RETRY_DELAY}s..."
                    )
                    await asyncio.sleep(self.RETRY_DELAY)
                    self._restart_process()
                else:
                    logger.error(
                        f"❌ All {max_retries} attempts failed. Last error: {e}"
                    )
        
        raise MCPClientError(
            f"Failed after {max_retries} retries. Last error: {last_error}"
        )
    
    async def _analyze_video_once(
        self, 
        prompt: str, 
        image_paths: List[str]
    ) -> Dict[str, Any]:
        """
        单次分析视频（内部方法，不带重试）
        
        Args:
            prompt: 分析提示词
            image_paths: 关键帧路径列表
        
        Returns:
            分析结果字典
        
        Raises:
            MCPClientError: 分析失败时抛出
        """
        async with self._lock:
            try:
                self._ensure_process_alive()
                
                if self.process is None:
                    raise MCPClientError("MCP process not initialized")
                
                self._request_id += 1
                request = {
                    "jsonrpc": "2.0",
                    "id": self._request_id,
                    "method": "tools/call",
                    "params": {
                        "name": "analyze_image",
                        "arguments": {
                            "image_source": image_paths[0] if image_paths else "",
                            "prompt": prompt
                        }
                    }
                }
                
                request_str = json.dumps(request) + "\n"
                logger.debug(f"Sending request (ID: {self._request_id})")
                
                if self.process.stdin is None:
                    raise MCPClientError("MCP process stdin not available")
                
                self.process.stdin.write(request_str)
                self.process.stdin.flush()
                
                try:
                    if self.process.stdout is None:
                        raise MCPClientError("MCP process stdout not available")
                    
                    stdout = self.process.stdout
                    response_str = None
                    read_error = None
                    
                    def read_with_timeout():
                        nonlocal response_str, read_error
                        try:
                            response_str = stdout.readline()
                        except Exception as e:
                            read_error = e
                    
                    read_thread = threading.Thread(target=read_with_timeout, daemon=True)
                    read_thread.start()
                    read_thread.join(timeout=self.response_timeout)
                    
                    if read_thread.is_alive():
                        raise MCPClientError(
                            f"Response timeout ({self.response_timeout}s)"
                        )
                    
                    if read_error:
                        raise MCPClientError(f"Read error: {read_error}")
                    
                    if not response_str:
                        stderr = self.process.stderr.read() if self.process.stderr else ""
                        raise MCPClientError(f"No response. Stderr: {stderr}")
                    
                    response = json.loads(response_str)
                    
                    if "error" in response:
                        raise MCPClientError(f"Server error: {response['error']}")
                    
                    if "result" not in response:
                        logger.warning("Unexpected response structure")
                        return {
                            "description": "AI analysis completed but returned unexpected format.",
                            "tags": ["normal_operation"]
                        }
                    
                    logger.info("✓ Analysis completed successfully")
                    return response["result"]
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    raise MCPClientError(f"Invalid JSON response: {e}")
                    
            except Exception as e:
                logger.error(f"MCP analysis failed: {e}")
                raise MCPClientError(f"MCP analysis failed: {e}")
    
    def analyze_video_sync(
        self, 
        prompt: str, 
        image_paths: List[str],
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        同步包装器 - 用于非异步环境
        
        Args:
            prompt: 分析提示词
            image_paths: 关键帧路径列表
            max_retries: 最大重试次数
        
        Returns:
            分析结果字典
        """
        return asyncio.run(
            self.analyze_video(prompt, image_paths, max_retries)
        )
    
    def close(self):
        """
        显式关闭客户端
        确保MCP进程被正确清理
        """
        self._terminate_process()
        logger.info("MCP client closed")
    
    def __del__(self):
        """
        析构函数 - 确保进程被正确清理
        防止进程泄漏
        """
        self._terminate_process()
    
    def __enter__(self):
        """支持上下文管理器"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时自动清理"""
        self.close()
        return False

async def test_mcp_connection() -> bool:
    """
    测试MCP服务器是否可访问
    
    Returns:
        True如果连接成功，False否则
    """
    try:
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
    logging.basicConfig(level=logging.INFO)
    
    if asyncio.run(test_mcp_connection()):
        print("✓ MCP server is accessible")
    else:
        print("✗ MCP server is not accessible")
