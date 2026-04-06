# 视频数据自动化标注 Agent

一个健壮的、生产级的自动化视频标注系统，可以处理视频文件、提取关键帧，并使用 AI 视觉模型（MCP GLM4.6v）生成简洁的描述并将视频分类到预定义的类别中。

## 功能特性

- **自动化视频处理**：递归处理任意目录中的视频文件
- **并发执行**：多线程处理以高效处理大批量视频
- **AI 驱动分析**：使用 MCP (GLM4.6v) 进行智能视频理解
- **健壮的错误处理**：优雅地处理损坏、过短或有问题的视频
- **进度可视化**：实时进度条显示成功/失败统计
- **结构化输出**：结果以良好定义的 JSON 格式保存
- **可配置**：通过环境变量和设置提供广泛的配置选项

## 项目结构

```
VedioAutoMark/
├── src/
│   └── video_agent/
│       ├── main.py                 # 主入口
│       ├── core/
│       │   ├── config.py           # 配置管理
│       │   ├── video_processor.py  # 视频处理和关键帧提取
│       │   └── ai_analyzer.py       # 使用 MCP (GLM4.6v) 进行 AI 分析
│       └── models/
│           └── schemas.py          # Pydantic 数据模型
├── data/
│   ├── input/                     # 在这里放置您的视频
│   └── output/                    # 结果将保存在这里
├── tests/                         # 单元测试
├── scripts/                        # 工具脚本
├── requirements.txt                # Python 依赖
├── pyproject.toml                 # 项目配置
└── README.md                      # 本文件
```

## 安装

### 前置要求

- Python 3.8 或更高版本
- FFmpeg（OpenCV 视频处理需要）
  - Windows：从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载并添加到 PATH
  - macOS：`brew install ffmpeg`
  - Linux：`sudo apt-get install ffmpeg`
- Node.js 和 npm（必需）
  - 用于运行 MCP 服务器

### 安装步骤

1. **克隆或导航到项目目录**：
```bash
cd VedioAutoMark
```

2. **创建虚拟环境**（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **安装依赖**：
```bash
pip install -r requirements.txt
```

4. **配置环境变量**：

在项目根目录创建 `.env` 文件：

```env
# MCP 配置
MCP_ZAI_API_KEY=your_zai_api_key_here
MCP_ZAI_MODE=ZHIPU
```

#### 其他配置选项：

```env
MIN_VIDEO_DURATION_SECONDS=3.0
KEYFRAME_EXTRACT_COUNT=10
LOG_LEVEL=INFO
```

## 使用方法

### 基本使用

要处理目录中的所有视频：

```bash
python src/video_agent/main.py /path/to/your/videos
```

### 高级使用

指定自定义输出路径和工作线程数：

```bash
python src/video_agent/main.py /path/to/your/videos --output /custom/output/results.json --workers 10
```

### 命令行参数

- `input_directory`（必需）：包含视频文件的目录路径
- `--output`（可选）：输出 JSON 文件的自定义路径。默认：`data/output/annotation_results_TIMESTAMP.json`
- `--workers`（可选）：并发工作线程数。默认：5

### 输出示例

```
Processing Videos: 100%|██████████| 100/100 [10:23<00:00,  6.23s/video, Success: 95, Failed: 5]

2026-03-27 18:45:00 - INFO - Processing Complete!
2026-03-27 18:45:00 - INFO - Total Videos: 100
2026-03-27 18:45:00 - INFO - Successful: 95
2026-03-27 18:45:00 - INFO - Failed/Abnormal: 5
2026-03-27 18:45:00 - INFO - Duration: 0:10:23.123456
2026-03-27 18:45:00 - INFO - Results saved to: data/output/annotation_results_20260327_184500.json
```

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
    },
    {
      "file_path": "/path/to/corrupted_video.mp4",
      "description": "AI Analysis Failed",
      "tags": ["abnormal_video"],
      "duration_seconds": null,
      "is_abnormal": true,
      "abnormality_reason": "Could not open or decode video file.",
      "processing_timestamp": "2026-03-27T10:30:05.123456",
      "confidence_scores": null
    }
  ],
  "processing_start_time": "2026-03-27T10:00:00.123456",
  "processing_end_time": "2026-03-27T10:10:23.123456",
    "execution_metadata": {
    "ai_provider": "MCP (GLM4.6v)",
    "model": "GLM4.6v",
    "max_workers": 5,
    "input_directory": "/path/to/videos"
  }
}
```

## 配置选项

所有配置通过 `src/video_agent/core/config.py` 管理。关键选项：

| 设置 | 默认值 | 描述 |
|---------|--------|-------------|
| `MCP_ZAI_API_KEY` | 必需 | ZAI API 密钥 |
| `MCP_ZAI_MODE` | `ZHIPU` | MCP 模式设置 |
| `MIN_VIDEO_DURATION_SECONDS` | `3.0` | 最小视频时长（秒） |
| `KEYFRAME_EXTRACT_COUNT` | `10` | 每个视频提取的关键帧数 |
| `LOG_LEVEL` | `INFO` | 日志详细程度（DEBUG, INFO, WARNING, ERROR） |

## AI 提供商

本项目使用 MCP (GLM4.6v) 进行视频分析：

### MCP (GLM4.6v)
- 使用智谱 GLM-4V 6.0 视觉模型
- 需要有效的 ZAI API 密钥
- 通过 MCP 协议进行通信
- 需要安装 Node.js 和 npm

## 支持的视频格式

- MP4
- MOV
- AVI
- MKV
- FLV
- WMV

## 标签类别

系统将视频分类为以下类别：

- `daily_activity` - 常规的日常活动
- `illegal_intrusion` - 未经授权的进入或可疑行为
- `property_damage` - 财产损失或破坏公物
- `social_gathering` - 人群聚集
- `vehicle_movement` - 汽车、卡车或其他车辆
- `animal_activity` - 视频中的动物
- `emergency_situation` - 火灾、医疗紧急情况、事故
- `normal_operation` - 标准业务或运营活动
- `abnormal_video` - 损坏、过短或无法处理的视频

## 错误处理

系统设计具有韧性：

- **损坏的视频**：自动检测并标记为 `abnormal_video`
- **过短的视频**：时长小于 3 秒的视频被标记为异常
- **处理失败**：单个视频失败不会停止批处理
- **AI 错误**：优雅处理并提供适当的回退标注
- **网络问题**：API 调用失败被记录并处理为失败

## 性能考虑

- **并发性**：使用 `--workers` 调整并行度。更多工作线程 = 更快处理但更高资源使用
- **关键帧提取**：更少的帧 = 更快处理但可能 AI 分析准确性较低
- **API 速率限制**：相应调整工作线程数
- **内存使用**：大批量可能消耗大量内存来存储关键帧

## 故障排查

### 问题："OpenCV Error: Failed to read frame"
**解决方案**：确保 FFmpeg 已正确安装并在系统 PATH 中可访问

### 问题："MCP API Error"
**解决方案**：验证您的 ZAI API 密钥正确且您有足够的配额

### 问题："No video files found"
**解决方案**：检查输入目录路径是否正确且包含支持的视频文件

### 问题：处理缓慢
**解决方案**：使用 `--workers` 增加工作线程数或在配置中减少 `KEYFRAME_EXTRACT_COUNT`
