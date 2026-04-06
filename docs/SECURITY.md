# 🔒 安全性改进指南

## 📋 目录

1. [概述](#概述)
2. [安全功能](#安全功能)
3. [API密钥管理](#api密钥管理)
4. [输入验证](#输入验证)
5. [日志安全](#日志安全)
6. [最佳实践](#最佳实践)
7. [配置示例](#配置示例)

---

## 概述

本项目实现了全面的安全改进措施，包括：

- ✅ **API密钥加密存储** - 使用主密码加密API密钥
- ✅ **输入验证** - 防止路径遍历攻击和恶意文件
- ✅ **敏感数据过滤** - 自动过滤日志中的敏感信息
- ✅ **安全日志记录** - 防止敏感信息泄露
- ✅ **文件安全** - 完善的.gitignore规则

---

## 安全功能

### 1. APIKeyManager - API密钥安全管理

**功能**：
- 加密存储API密钥
- 密钥格式验证
- 密钥缓存管理
- 安全的密钥获取

**使用示例**：

```python
from src.video_agent.utils.security_utils import APIKeyManager

# 初始化（可选主密码）
manager = APIKeyManager(master_password="your_master_password")

# 加密API密钥
api_key = "sk-your-api-key-here"
encrypted_key, salt = manager.encrypt_api_key(api_key)

# 解密API密钥
decrypted_key = manager.decrypt_api_key(encrypted_key, salt)

# 验证API密钥
is_valid = manager.validate_api_key(api_key)

# 安全获取API密钥
api_key = manager.get_api_key_safely("MCP_ZAI_API_KEY")
```

---

### 2. InputValidator - 输入验证

**功能**：
- 文件路径验证
- 文件大小验证
- 文件扩展名验证
- 路径遍历攻击防护

**使用示例**：

```python
from src.video_agent.utils.security_utils import InputValidator

# 验证文件路径
valid, error = InputValidator.validate_file_path("/path/to/video.mp4")

# 验证文件大小（默认100MB）
valid, error = InputValidator.validate_file_size("/path/to/video.mp4")

# 验证文件扩展名
valid, error = InputValidator.validate_file_extension("video.mp4")

# 综合验证
valid, errors = InputValidator.validate_video_file("/path/to/video.mp4")
```

---

### 3. SensitiveDataFilter - 敏感数据过滤

**功能**：
- 自动检测敏感数据模式
- 过滤API密钥
- 过滤密码
- 过滤邮箱和信用卡号

**使用示例**：

```python
from src.video_agent.utils.security_utils import SensitiveDataFilter

# 过滤敏感数据
text = "API_KEY=sk-1234567890abcdef"
filtered = SensitiveDataFilter.filter_sensitive_data(text)
# 输出: "API_KEY=***REDACTED***"

# 检测是否包含敏感数据
has_sensitive = SensitiveDataFilter.contains_sensitive_data(text)
```

---

### 4. SecureLogger - 安全日志记录器

**功能**：
- 自动过滤敏感信息
- 支持所有日志级别
- 防止信息泄露

**使用示例**：

```python
from src.video_agent.utils.security_utils import SecureLogger

# 创建安全日志记录器
logger = SecureLogger("my_module")

# 记录日志（自动过滤敏感信息）
logger.info("API_KEY=sk-1234567890abcdef")
# 输出: "API_KEY=***REDACTED***"

logger.error("Password: mysecretpassword123")
# 输出: "Password: ***REDACTED***"
```

---

## API密钥管理

### 方案1：环境变量（推荐）

```bash
# 1. 复制模板文件
cp .env.security.template .env

# 2. 编辑.env文件
nano .env

# 3. 设置API密钥
MCP_ZAI_API_KEY=your_actual_api_key_here

# 4. 设置主密码（可选）
MASTER_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 方案2：加密存储

```python
from src.video_agent.utils.security_utils import create_secure_env_file

# 创建加密的.env文件
api_keys = {
    "MCP_ZAI_API_KEY": "your_api_key_here",
    "OPENAI_API_KEY": "another_api_key"
}

create_secure_env_file(
    env_path=".env",
    api_keys=api_keys,
    master_password="your_master_password"
)
```

---

## 输入验证

### 文件路径验证

```python
from src.video_agent.utils.security_utils import InputValidator

# 基本验证
valid, error = InputValidator.validate_file_path("/path/to/video.mp4")

# 带基础目录的验证（防止路径遍历）
valid, error = InputValidator.validate_file_path(
    "/path/to/video.mp4",
    base_dir="/safe/base/directory"
)
```

### 文件大小验证

```python
# 默认最大100MB
valid, error = InputValidator.validate_file_size("/path/to/video.mp4")

# 自定义最大大小（50MB）
valid, error = InputValidator.validate_file_size(
    "/path/to/video.mp4",
    max_size=50 * 1024 * 1024
)
```

### 文件类型验证

```python
# 使用默认扩展名
valid, error = InputValidator.validate_file_extension("video.mp4")

# 自定义扩展名
valid, error = InputValidator.validate_file_extension(
    "video.mp4",
    allowed_extensions={'.mp4', '.mov', '.avi'}
)
```

---

## 日志安全

### 使用SecureLogger

```python
import logging
from src.video_agent.utils.security_utils import SecureLogger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建安全日志记录器
logger = SecureLogger(__name__)

# 安全记录日志
logger.info("Processing video: test.mp4")
logger.info("API_KEY=sk-1234567890")  # 自动过滤
```

### 过滤敏感数据

```python
from src.video_agent.utils.security_utils import SensitiveDataFilter

# 过滤日志消息
log_message = "User logged in with API_KEY=sk-1234567890"
safe_message = SensitiveDataFilter.filter_sensitive_data(log_message)
print(safe_message)
# 输出: "User logged in with API_KEY=***REDACTED***"
```

---

## 最佳实践

### 1. API密钥管理

✅ **推荐做法**：
- 使用环境变量存储API密钥
- 使用主密码加密敏感数据
- 定期轮换API密钥
- 不要在代码中硬编码密钥

❌ **避免做法**：
- 在代码中硬编码API密钥
- 将.env文件提交到版本控制
- 使用弱密码作为主密码
- 在日志中记录API密钥

### 2. 输入验证

✅ **推荐做法**：
- 验证所有用户输入
- 检查文件路径和大小
- 使用白名单验证文件类型
- 设置合理的文件大小限制

❌ **避免做法**：
- 盲目信任用户输入
- 允许任意文件路径
- 只检查文件扩展名
- 不限制文件大小

### 3. 日志安全

✅ **推荐做法**：
- 使用SecureLogger记录日志
- 过滤敏感信息
- 定期审计日志
- 设置合适的日志级别

❌ **避免做法**：
- 在日志中记录密码
- 记录完整的API密钥
- 使用DEBUG级别记录生产日志
- 不审查日志内容

### 4. 文件安全

✅ **推荐做法**：
- 使用.gitignore排除敏感文件
- 加密存储敏感配置
- 限制文件访问权限
- 定期备份重要数据

❌ **避免做法**：
- 提交.env文件到版本控制
- 明文存储密码
- 使用777权限
- 不备份重要数据

---

## 配置示例

### .env文件示例

```bash
# MCP API Configuration
MCP_ZAI_API_KEY=your_api_key_here
MCP_ZAI_MODE=ZHIPU

# Security Settings
MASTER_PASSWORD=your_master_password_here
ENABLE_KEY_ENCRYPTION=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=video_annotation_agent.log
ENABLE_LOG_FILTERING=true

# Input Validation
MAX_FILE_SIZE_MB=100
STRICT_PATH_VALIDATION=true
```

### 安全配置检查清单

- [ ] API密钥已设置且不在版本控制中
- [ ] 主密码已设置（可选）
- [ ] .env文件已添加到.gitignore
- [ ] 日志过滤已启用
- [ ] 输入验证已启用
- [ ] 文件大小限制已设置
- [ ] 定期密钥轮换计划已制定

---

## 运行安全示例

```bash
# 安装依赖
pip install cryptography

# 运行安全示例
python examples/security_examples.py
```

---

## 安全审计

### 定期检查项

1. **API密钥安全**
   - [ ] 检查API密钥是否泄露
   - [ ] 验证密钥轮换策略
   - [ ] 审查密钥访问日志

2. **输入验证**
   - [ ] 测试路径遍历防护
   - [ ] 验证文件大小限制
   - [ ] 检查文件类型验证

3. **日志安全**
   - [ ] 审查日志内容
   - [ ] 验证敏感数据过滤
   - [ ] 检查日志访问权限

4. **文件安全**
   - [ ] 验证.gitignore规则
   - [ ] 检查文件权限
   - [ ] 审查敏感文件位置

---

## 联系方式

如有安全问题或建议，请联系项目维护者。

---

**注意**：安全性是一个持续的过程，请定期审查和更新安全措施。
