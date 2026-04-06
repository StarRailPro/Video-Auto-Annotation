"""
Security usage examples for Video Annotation Agent
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.video_agent.utils.security_utils import (
    APIKeyManager,
    InputValidator,
    SensitiveDataFilter,
    SecureLogger,
    create_secure_env_file
)


def example_api_key_management():
    """API密钥管理示例"""
    print("=" * 60)
    print("API密钥管理示例")
    print("=" * 60)
    
    manager = APIKeyManager(master_password="my_secure_master_password_12345")
    
    api_key = "sk-test-api-key-1234567890abcdef"
    
    print(f"\n原始API密钥: {api_key}")
    
    encrypted_key, salt = manager.encrypt_api_key(api_key)
    print(f"\n加密后的密钥: {encrypted_key}")
    print(f"盐值: {salt}")
    
    decrypted_key = manager.decrypt_api_key(encrypted_key, salt)
    print(f"\n解密后的密钥: {decrypted_key}")
    
    is_valid = manager.validate_api_key(api_key)
    print(f"\n密钥验证结果: {'有效' if is_valid else '无效'}")
    
    print("\n" + "=" * 60)


def example_input_validation():
    """输入验证示例"""
    print("\n" + "=" * 60)
    print("输入验证示例")
    print("=" * 60)
    
    test_file = "test_video.mp4"
    
    print(f"\n验证文件路径: {test_file}")
    valid, error = InputValidator.validate_file_path(test_file)
    print(f"结果: {'有效' if valid else '无效'}")
    if not valid:
        print(f"错误: {error}")
    
    print("\n验证文件扩展名:")
    valid, error = InputValidator.validate_file_extension("test.mp4")
    print(f"test.mp4: {'有效' if valid else '无效'} - {error}")
    
    valid, error = InputValidator.validate_file_extension("test.txt")
    print(f"test.txt: {'有效' if valid else '无效'} - {error}")
    
    print("\n" + "=" * 60)


def example_sensitive_data_filter():
    """敏感数据过滤示例"""
    print("\n" + "=" * 60)
    print("敏感数据过滤示例")
    print("=" * 60)
    
    test_messages = [
        "API_KEY=sk-1234567890abcdef1234567890abcdef",
        "Password: mysecretpassword123",
        "User email: user@example.com",
        "Credit card: 1234-5678-9012-3456",
        "Normal log message without sensitive data"
    ]
    
    print("\n原始消息 -> 过滤后消息:")
    print("-" * 60)
    
    for message in test_messages:
        filtered = SensitiveDataFilter.filter_sensitive_data(message)
        print(f"{message}")
        print(f"  -> {filtered}")
        print()
    
    print("=" * 60)


def example_secure_logger():
    """安全日志记录器示例"""
    print("\n" + "=" * 60)
    print("安全日志记录器示例")
    print("=" * 60)
    
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    logger = SecureLogger("example")
    
    print("\n记录包含敏感信息的日志:")
    logger.info("API_KEY=sk-1234567890abcdef1234567890abcdef")
    logger.info("User password: mysecretpassword123")
    logger.info("Processing video: test.mp4")
    
    print("\n" + "=" * 60)


def example_create_secure_env():
    """创建安全.env文件示例"""
    print("\n" + "=" * 60)
    print("创建安全.env文件示例")
    print("=" * 60)
    
    api_keys = {
        "MCP_ZAI_API_KEY": "sk-test-api-key-1234567890abcdef",
        "OPENAI_API_KEY": "sk-openai-key-0987654321fedcba"
    }
    
    env_path = "test_secure.env"
    
    print(f"\n创建加密的.env文件: {env_path}")
    print(f"API密钥: {list(api_keys.keys())}")
    
    create_secure_env_file(env_path, api_keys, master_password="test_master_password")
    
    print(f"\n.env文件已创建，内容:")
    with open(env_path, 'r') as f:
        print(f.read())
    
    os.remove(env_path)
    print("测试文件已删除")
    
    print("=" * 60)


def example_security_best_practices():
    """安全最佳实践示例"""
    print("\n" + "=" * 60)
    print("安全最佳实践")
    print("=" * 60)
    
    print("\n1. API密钥管理:")
    print("   - 使用环境变量存储API密钥")
    print("   - 使用主密码加密敏感数据")
    print("   - 定期轮换API密钥")
    print("   - 不要在代码中硬编码密钥")
    
    print("\n2. 输入验证:")
    print("   - 验证所有用户输入")
    print("   - 检查文件路径和大小")
    print("   - 防止路径遍历攻击")
    print("   - 限制文件类型和大小")
    
    print("\n3. 日志安全:")
    print("   - 过滤日志中的敏感信息")
    print("   - 使用安全的日志记录器")
    print("   - 不要记录API密钥或密码")
    print("   - 定期审计日志")
    
    print("\n4. 文件安全:")
    print("   - 使用.gitignore排除敏感文件")
    print("   - 加密存储敏感配置")
    print("   - 限制文件访问权限")
    print("   - 定期备份重要数据")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n" + "🔒 " * 20)
    print("Video Annotation Agent - 安全功能演示")
    print("🔒 " * 20 + "\n")
    
    example_api_key_management()
    example_input_validation()
    example_sensitive_data_filter()
    example_secure_logger()
    example_create_secure_env()
    example_security_best_practices()
    
    print("\n✅ 所有安全功能演示完成！\n")
