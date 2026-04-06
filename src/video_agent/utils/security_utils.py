"""
Security utilities for API key management, input validation, and sensitive data protection.
"""

import os
import re
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Security-related error"""
    pass


class APIKeyManager:
    """
    API密钥安全管理器
    
    功能：
    1. 加密存储API密钥
    2. 密钥验证
    3. 密钥轮换支持
    4. 安全的密钥传递
    """
    
    def __init__(self, master_password: Optional[str] = None):
        """
        初始化API密钥管理器
        
        Args:
            master_password: 主密码，用于加密API密钥
                           如果为None，则从环境变量MASTER_PASSWORD读取
        """
        self.master_password = master_password or os.getenv("MASTER_PASSWORD")
        self._key_cache: Dict[str, str] = {}
        
        if not self.master_password:
            logger.warning(
                "Master password not set. API keys will not be encrypted. "
                "Set MASTER_PASSWORD environment variable for enhanced security."
            )
    
    def _get_encryption_key(self, salt: bytes) -> Optional[bytes]:
        """
        从主密码生成加密密钥
        
        Args:
            salt: 盐值
        
        Returns:
            加密密钥，如果主密码未设置则返回None
        """
        if not self.master_password:
            return None
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
        return key
    
    def encrypt_api_key(self, api_key: str) -> Tuple[str, str]:
        """
        加密API密钥
        
        Args:
            api_key: 原始API密钥
        
        Returns:
            (加密后的密钥, 盐值) - 盐值需要保存用于解密
        """
        if not self.master_password:
            return api_key, ""
        
        salt = secrets.token_bytes(16)
        key = self._get_encryption_key(salt)
        
        if not key:
            return api_key, ""
        
        fernet = Fernet(key)
        encrypted_key = fernet.encrypt(api_key.encode()).decode()
        
        return encrypted_key, base64.urlsafe_b64encode(salt).decode()
    
    def decrypt_api_key(self, encrypted_key: str, salt: str) -> str:
        """
        解密API密钥
        
        Args:
            encrypted_key: 加密的API密钥
            salt: 盐值（base64编码）
        
        Returns:
            原始API密钥
        """
        if not self.master_password or not salt:
            return encrypted_key
        
        try:
            salt_bytes = base64.urlsafe_b64decode(salt.encode())
            key = self._get_encryption_key(salt_bytes)
            
            if not key:
                return encrypted_key
            
            fernet = Fernet(key)
            decrypted_key = fernet.decrypt(encrypted_key.encode()).decode()
            
            return decrypted_key
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise SecurityError("Failed to decrypt API key")
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        验证API密钥格式
        
        Args:
            api_key: API密钥
        
        Returns:
            是否有效
        """
        if not api_key or not isinstance(api_key, str):
            return False
        
        if len(api_key) < 16:
            logger.warning("API key is too short (minimum 16 characters)")
            return False
        
        if len(api_key) > 512:
            logger.warning("API key is too long (maximum 512 characters)")
            return False
        
        if not re.match(r'^[a-zA-Z0-9._-]+$', api_key):
            logger.warning("API key contains invalid characters")
            return False
        
        return True
    
    def get_api_key_safely(self, key_name: str = "MCP_ZAI_API_KEY") -> Optional[str]:
        """
        安全地获取API密钥
        
        Args:
            key_name: 环境变量名称
        
        Returns:
            API密钥，如果不存在或无效则返回None
        """
        if key_name in self._key_cache:
            return self._key_cache[key_name]
        
        api_key = os.getenv(key_name)
        
        if not api_key:
            logger.error(f"API key '{key_name}' not found in environment variables")
            return None
        
        if not self.validate_api_key(api_key):
            logger.error(f"API key '{key_name}' is invalid")
            return None
        
        self._key_cache[key_name] = api_key
        return api_key
    
    def clear_cache(self):
        """清除密钥缓存"""
        self._key_cache.clear()
        logger.info("API key cache cleared")


class InputValidator:
    """
    输入验证器
    
    功能：
    1. 文件路径验证
    2. 文件大小验证
    3. 文件类型验证
    4. 路径遍历攻击防护
    """
    
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv'}
    
    @staticmethod
    def validate_file_path(file_path: str, base_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        验证文件路径安全性
        
        Args:
            file_path: 文件路径
            base_dir: 基础目录（可选），如果提供则检查路径是否在基础目录内
        
        Returns:
            (是否有效, 错误信息)
        """
        if not file_path or not isinstance(file_path, str):
            return False, "Invalid file path: empty or not a string"
        
        try:
            path = Path(file_path).resolve()
            
            if not path.exists():
                return False, f"File does not exist: {file_path}"
            
            if not path.is_file():
                return False, f"Path is not a file: {file_path}"
            
            if base_dir:
                base_path = Path(base_dir).resolve()
                try:
                    path.relative_to(base_path)
                except ValueError:
                    return False, f"File path is outside base directory: {file_path}"
            
            path_str = str(path)
            if '..' in path_str or path_str.startswith('/etc') or path_str.startswith('/root'):
                return False, f"Potential path traversal attack detected: {file_path}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid file path: {e}"
    
    @staticmethod
    def validate_file_size(file_path: str, max_size: int = None) -> Tuple[bool, str]:
        """
        验证文件大小
        
        Args:
            file_path: 文件路径
            max_size: 最大文件大小（字节），默认100MB
        
        Returns:
            (是否有效, 错误信息)
        """
        max_size = max_size or InputValidator.MAX_FILE_SIZE
        
        try:
            file_size = os.path.getsize(file_path)
            
            if file_size == 0:
                return False, "File is empty"
            
            if file_size > max_size:
                size_mb = file_size / (1024 * 1024)
                max_mb = max_size / (1024 * 1024)
                return False, f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_mb:.2f}MB)"
            
            return True, ""
            
        except Exception as e:
            return False, f"Failed to validate file size: {e}"
    
    @staticmethod
    def validate_file_extension(file_path: str, allowed_extensions: set = None) -> Tuple[bool, str]:
        """
        验证文件扩展名
        
        Args:
            file_path: 文件路径
            allowed_extensions: 允许的扩展名集合
        
        Returns:
            (是否有效, 错误信息)
        """
        allowed_extensions = allowed_extensions or InputValidator.ALLOWED_EXTENSIONS
        
        ext = Path(file_path).suffix.lower()
        
        if not ext:
            return False, "File has no extension"
        
        if ext not in allowed_extensions:
            return False, f"File extension '{ext}' is not allowed. Allowed: {', '.join(allowed_extensions)}"
        
        return True, ""
    
    @staticmethod
    def validate_video_file(file_path: str, base_dir: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        综合验证视频文件
        
        Args:
            file_path: 文件路径
            base_dir: 基础目录（可选）
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        valid, error = InputValidator.validate_file_path(file_path, base_dir)
        if not valid:
            errors.append(error)
        
        valid, error = InputValidator.validate_file_size(file_path)
        if not valid:
            errors.append(error)
        
        valid, error = InputValidator.validate_file_extension(file_path)
        if not valid:
            errors.append(error)
        
        return len(errors) == 0, errors


class SensitiveDataFilter:
    """
    敏感数据过滤器
    
    功能：
    1. 过滤日志中的敏感信息
    2. 检测API密钥模式
    3. 检测密码模式
    """
    
    SENSITIVE_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9._-]{16,})', r'\1=***REDACTED***'),
        (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{8,})', r'\1=***REDACTED***'),
        (r'(?i)(secret|token)\s*[=:]\s*["\']?([a-zA-Z0-9._-]{16,})', r'\1=***REDACTED***'),
        (r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', '***EMAIL***'),
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '***CARD***'),
    ]
    
    @staticmethod
    def filter_sensitive_data(text: str) -> str:
        """
        过滤敏感数据
        
        Args:
            text: 原始文本
        
        Returns:
            过滤后的文本
        """
        filtered_text = text
        
        for pattern, replacement in SensitiveDataFilter.SENSITIVE_PATTERNS:
            filtered_text = re.sub(pattern, replacement, filtered_text)
        
        return filtered_text
    
    @staticmethod
    def contains_sensitive_data(text: str) -> bool:
        """
        检查文本是否包含敏感数据
        
        Args:
            text: 待检查文本
        
        Returns:
            是否包含敏感数据
        """
        for pattern, _ in SensitiveDataFilter.SENSITIVE_PATTERNS:
            if re.search(pattern, text):
                return True
        
        return False


class SecureLogger:
    """
    安全日志记录器
    
    功能：
    1. 自动过滤敏感信息
    2. 安全的日志级别控制
    3. 日志审计
    """
    
    def __init__(self, name: str):
        """
        初始化安全日志记录器
        
        Args:
            name: 日志记录器名称
        """
        self.logger = logging.getLogger(name)
        self.filter = SensitiveDataFilter()
    
    def _log_safe(self, level: int, message: str, *args, **kwargs):
        """
        安全地记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            *args: 位置参数
            **kwargs: 关键字参数
        """
        safe_message = self.filter.filter_sensitive_data(message)
        
        if args:
            safe_args = tuple(
                self.filter.filter_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in args
            )
            self.logger.log(level, safe_message, *safe_args, **kwargs)
        else:
            self.logger.log(level, safe_message, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录INFO级别日志"""
        self._log_safe(logging.INFO, message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """记录DEBUG级别日志"""
        self._log_safe(logging.DEBUG, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录WARNING级别日志"""
        self._log_safe(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录ERROR级别日志"""
        self._log_safe(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录CRITICAL级别日志"""
        self._log_safe(logging.CRITICAL, message, *args, **kwargs)


def create_secure_env_file(env_path: str, api_keys: Dict[str, str], master_password: Optional[str] = None):
    """
    创建加密的.env文件
    
    Args:
        env_path: .env文件路径
        api_keys: API密钥字典 {key_name: key_value}
        master_password: 主密码（可选）
    """
    manager = APIKeyManager(master_password)
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write("# Secure Environment Variables\n")
        f.write("# Generated by SecurityUtils\n\n")
        
        for key_name, key_value in api_keys.items():
            if manager.master_password:
                encrypted_key, salt = manager.encrypt_api_key(key_value)
                f.write(f"{key_name}={encrypted_key}\n")
                f.write(f"{key_name}_SALT={salt}\n")
            else:
                f.write(f"{key_name}={key_value}\n")
        
        f.write("\n# Security Configuration\n")
        f.write(f"MASTER_PASSWORD_SET={'true' if master_password else 'false'}\n")
    
    logger.info(f"Secure .env file created at: {env_path}")
