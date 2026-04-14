# 视频数据自动化标注 Agent

一个健壮的、生产级的自动化视频标注系统，可以处理视频文件、提取关键帧，并使用 AI 视觉模型（MCP GLM4.6v）生成简洁的描述并将视频分类到预定义的类别中。

提供 **Web 界面** 和 **命令行** 两种使用方式。

## 功能特性

### 核心功能
- **自动化视频处理**：递归处理任意目录中的视频文件
- **并发执行**：多线程处理以高效处理大批量视频
- **AI 驱动分析**：使用 MCP (GLM4.6v) 进行智能视频理解
- **健壮的错误处理**：优雅地处理损坏、过短或有问题的视频
- **结构化输出**：结果以良好定义的 JSON 格式保存

### Web 界面功能
- **文件输入**：支持上传视频文件或输入本地路径两种方式
- **实时进度**：WebSocket 推送进度条 + 当前处理文件名
- **状态标注**：待处理 / 处理中 / 已完成 / 失败 状态标签
- **标注预览**：卡片展示每个视频的描述、标签、置信度、异常信息
- **JSON 下载**：所有结果打包成一个 JSON 下载
- **标签管理器**：展示现有标签、支持增删自定义标签、启用/停用
- **设置页面**：API Key 配置、MCP 模式选择、并发数调整
- **失败重试**：处理失败的视频统一提示，支持一键重试
- **历史记录**：保留历史处理记录（SQLite 持久化）

## 项目结构

```
Video-Auto-Annotation/
├── run_web.py                     # Web 应用一键启动脚本
├── src/
│   └── video_agent/
│       ├── __init__.py
│       ├── main.py                 # 命令行主入口
│       ├── core/
│       │   ├── config.py           # 配置管理
│       │   ├── video_processor.py  # 视频处理和关键帧提取
│       │   └── ai_analyzer.py      # AI 分析 (MCP GLM4.6v)
│       ├── models/
│       │   └── schemas.py          # Pydantic 数据模型
│       └── utils/
│           ├── mcp_client.py       # MCP 客户端封装
│           └── security_utils.py   # 安全工具函数
├── web/
│   ├── backend/                    # FastAPI 后端
│   │   ├── app.py                  # 应用入口 + WebSocket + 静态文件
│   │   ├── database.py             # SQLite 数据库配置
│   │   ├── models.py               # SQLAlchemy ORM 模型
│   │   ├── schemas.py              # Pydantic 请求/响应模型
│   │   ├── routes/                 # API 路由
│   │   │   ├── tasks.py            # 任务管理
│   │   │   ├── annotations.py      # 标注预览与下载
│   │   │   ├── tags.py             # 标签管理
│   │   │   └── settings.py         # 设置管理
│   │   └── services/               # 业务逻辑
│   │       ├── task_manager.py     # 任务处理引擎
│   │       ├── tag_manager.py      # 标签管理服务
│   │       └── ws_manager.py       # WebSocket 连接管理
│   └── frontend/                   # Vue3 + Naive UI 前端
│       ├── src/
│       │   ├── views/              # 页面组件
│       │   ├── stores/             # Pinia 状态管理
│       │   ├── api/                # API 客户端
│       │   ├── composables/        # 组合式函数
│       │   ├── router/             # 路由配置
│       │   └── types/              # TypeScript 类型
│       └── dist/                   # 构建产物（后端自动 serve）
├── data/
│   ├── input/                      # 在这里放置您的视频
│   └── output/                     # 命令行模式的结果输出
├── tests/                          # 单元测试
├── docs/                           # 文档
├── requirements.txt                # Python 依赖
├── .env.example                    # 环境变量示例
└── README.md                       # 本文件
```

## 安装

### 前置要求

- Python 3.8 或更高版本
- Node.js 18+ 和 npm（Web 界面构建需要）
- FFmpeg（OpenCV 视频处理需要）
  - Windows：从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载并添加到 PATH
  - macOS：`brew install ffmpeg`
  - Linux：`sudo apt-get install ffmpeg`

### 安装步骤

1. **克隆或导航到项目目录**：
```bash
cd Video-Auto-Annotation
```

2. **创建虚拟环境**（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **安装 Python 依赖**：
```bash
pip install -r requirements.txt
```

4. **安装前端依赖并构建**（Web 界面需要）：
```bash
cd web/frontend
npm install
npm run build
cd ../..
```

5. **配置环境变量**：

在项目根目录创建 `.env` 文件：

```env
# MCP 配置
MCP_ZAI_API_KEY=your_zai_api_key_here
MCP_ZAI_MODE=ZHIPU
```

## 使用方法

### 方式一：Web 界面（推荐）

一键启动 Web 应用：

```bash
python run_web.py
```

启动后访问：
- **Web 界面**：http://localhost:8000/
- **API 文档**：http://localhost:8000/docs

环境变量配置：
```bash
# 自定义端口
VA_PORT=9000 python run_web.py

# 开发模式（自动重载）
VA_RELOAD=1 python run_web.py

# 自定义主机
VA_HOST=127.0.0.1 python run_web.py
```

Web 界面使用流程：
1. 在 **设置** 页面配置 API Key
2. 在 **任务管理** 页面创建新任务（上传文件或输入路径）
3. 点击 **开始** 启动处理，实时查看进度
4. 处理完成后在 **标注预览** 页面查看结果
5. 点击 **下载标注** 导出 JSON 文件
6. 在 **标签管理** 页面管理标签分类

### 方式二：命令行

要处理目录中的所有视频：

```bash
python src/video_agent/main.py /path/to/your/videos
```

指定自定义输出路径和工作线程数：

```bash
python src/video_agent/main.py /path/to/your/videos --output /custom/output/results.json --workers 10
```

### 命令行参数

- `input_directory`（必需）：包含视频文件的目录路径
- `--output`（可选）：输出 JSON 文件的自定义路径。默认：`data/output/annotation_results_TIMESTAMP.json`
- `--workers`（可选）：并发工作线程数。默认：5

## 输出格式

应用程序生成具有以下结构的 JSON 文件：

```json
{
  "total_videos_processed": 100,
  "successful_annotations": 95,
  "failed_annotations": 5,
  "annotations": [
    {
      "file_path": "/path/to/video1.mp4",
      "description": "A person walking through a park with trees.",
      "tags": ["daily_activity"],
      "duration_seconds": 30.5,
      "is_abnormal": false,
      "abnormality_reason": null,
      "processing_timestamp": "2026-03-27T10:30:00.123456",
      "confidence_scores": {
        "daily_activity": 0.95
      }
    }
  ],
  "processing_start_time": "2026-03-27T10:00:00.123456",
  "processing_end_time": "2026-03-27T10:10:23.123456"
}
```

## 配置选项

### 环境变量

| 设置 | 默认值 | 描述 |
|---------|--------|-------------|
| `MCP_ZAI_API_KEY` | 必需 | ZAI API 密钥 |
| `MCP_ZAI_MODE` | `ZHIPU` | MCP 模式设置 |
| `MIN_VIDEO_DURATION_SECONDS` | `3.0` | 最小视频时长（秒） |
| `KEYFRAME_EXTRACT_COUNT` | `10` | 每个视频提取的关键帧数 |
| `LOG_LEVEL` | `INFO` | 日志详细程度 |

### Web 应用环境变量

| 设置 | 默认值 | 描述 |
|---------|--------|-------------|
| `VA_HOST` | `0.0.0.0` | 服务器监听地址 |
| `VA_PORT` | `8000` | 服务器端口 |
| `VA_RELOAD` | `0` | 是否启用自动重载（开发模式） |

## AI 提供商

本项目使用 MCP (GLM4.6v) 进行视频分析：
- 使用智谱 GLM-4V 6.0 视觉模型
- 需要有效的 ZAI API 密钥
- 通过 MCP 协议进行通信
- 需要安装 Node.js 和 npm

## 支持的视频格式

MP4、MOV、AVI、MKV、FLV、WMV

## 标签类别

系统内置以下标签分类：

| 标签 | 标识 | 描述 |
|------|------|------|
| 日常活动 | `daily_activity` | 常规的日常活动 |
| 非法入侵 | `illegal_intrusion` | 未经授权的进入或可疑行为 |
| 财产损坏 | `property_damage` | 财产损失或破坏公物 |
| 社交聚会 | `social_gathering` | 人群聚集 |
| 车辆移动 | `vehicle_movement` | 汽车或其他车辆 |
| 动物活动 | `animal_activity` | 视频中的动物 |
| 紧急情况 | `emergency_situation` | 火灾、医疗紧急情况、事故 |
| 正常操作 | `normal_operation` | 标准业务或运营活动 |
| 异常视频 | `abnormal_video` | 损坏、过短或无法处理的视频 |

可在 Web 界面的 **标签管理** 页面添加自定义标签。

## 技术栈

### 后端
- **FastAPI** - 高性能异步 Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **SQLite** - 轻量级持久化存储
- **Pydantic** - 数据验证
- **WebSocket** - 实时进度推送
- **Uvicorn** - ASGI 服务器

### 前端
- **Vue 3** - 渐进式前端框架
- **Naive UI** - Vue3 组件库
- **Pinia** - 状态管理
- **Vue Router** - 前端路由
- **Axios** - HTTP 客户端
- **TypeScript** - 类型安全
- **Vite** - 构建工具

## 故障排查

### 问题："OpenCV Error: Failed to read frame"
**解决方案**：确保 FFmpeg 已正确安装并在系统 PATH 中可访问

### 问题："MCP API Error"
**解决方案**：验证您的 ZAI API 密钥正确且您有足够的配额

### 问题："No video files found"
**解决方案**：检查输入目录路径是否正确且包含支持的视频文件

### 问题：前端页面无法访问
**解决方案**：确认已执行 `npm run build`，`web/frontend/dist/` 目录存在

### 问题：WebSocket 连接失败
**解决方案**：检查后端是否正常运行，确认没有代理或防火墙阻止 WebSocket 连接

## 开发

### 运行测试

```bash
pytest tests/
```

### 前端开发

```bash
cd web/frontend
npm run dev    # 启动开发服务器 (http://localhost:3000)
npm run build  # 构建生产版本
```

开发时前端会自动代理 API 请求到 `http://localhost:8000`。

### 代码风格

项目使用 Black、Flake8、Mypy 进行代码质量检查：

```bash
black src/video_agent/
flake8 src/video_agent/
mypy src/video_agent/
```

## 贡献

欢迎贡献！请确保：
1. 代码遵循现有风格
2. 所有测试通过
3. 新功能包含适当的测试
4. 文档已更新

## 许可证

[在此指定您的许可证]
