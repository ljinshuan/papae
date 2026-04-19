# 婴幼儿姿态评估系统

<p align="center">
  <img src="logo.png" alt="婴幼儿姿态评估系统 Logo">
</p>

[English](README.md) | 中文

基于 YOLOv8-pose + YOLOv8-seg 和全模态大语言模型（Qwen-VL）的婴幼儿姿态评估命令行工具。

支持三种评估模式：走路步态分析、运动发育筛查、姿势矫正评估。输入家长录制的宝宝视频，输出结构化 Markdown 评估报告和带骨架/分割叠加的可视化视频。

## 目录

- [快速开始](#快速开始)
- [功能特性](#功能特性)
- [用户指南](#用户指南)
  - [评估模式详解](#评估模式详解)
  - [拍摄建议](#拍摄建议)
  - [如何理解评估报告](#如何理解评估报告)
- [开发者指南](#开发者指南)
  - [安装](#安装)
  - [Python API](#python-api)
  - [输出文件](#输出文件)
  - [架构](#架构)
  - [项目结构](#项目结构)
  - [开发](#开发)
- [免责声明](#免责声明)
- [许可证](#许可证)

## 快速开始

需要 Python >= 3.13。

```bash
# 克隆并安装
uv sync --extra dev

# 快速评估（默认 gait 模式，需要 LLM API key）
uv run gait-assess --video ./baby_walking.mp4 --output ./results/

# 无需 API key 体验 —— 生成可视化视频和报告框架
uv run gait-assess --video ./baby_walking.mp4 --output ./results/ --skip-llm

# 运动发育筛查（需指定月龄）
uv run gait-assess --video ./baby_walking.mp4 --mode developmental --age-months 12 --output ./results/

# 姿势矫正评估
uv run gait-assess --video ./baby_standing.mp4 --mode posture --output ./results/
```

### 环境配置

LLM 相关配置通过环境变量或 `.env` 文件读取：

```bash
cat > .env << 'EOF'
QWEN_API_KEY=your-api-key
GAIT_LLM_MODEL=qwen-vl-max
GAIT_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EOF
```

## 功能特性

- **三种评估模式**：
  - `gait` — 走路步态分析：基于步态周期检测，评估走路姿态异常
  - `developmental` — 运动发育筛查：按月龄匹配里程碑，筛查发育延迟风险
  - `posture` — 姿势矫正评估：分析静态站立姿态的脊柱/肩膀/骨盆对称性
- **视频预处理**：自动拆帧、模糊过滤、分辨率标准化
- **姿态检测**：YOLOv8-pose 提取 17 个 COCO 关键点
- **人体分割**：YOLOv8-seg 生成分割 mask
- **步态分析**：基于脚踝轨迹检测步态周期，提取 4 个关键相位帧
- **姿态计算**：膝关节角、踝关节角、脊柱倾角、骨盆倾斜、肩高差等
- **LLM 评估**：多模态大模型端到端判断，视频 + 结构化姿态数据双通道输入
- **可视化输出**：骨架连线、mask 叠加、关键帧标记
- **交互式查看器**：`viewer.html` 支持逐帧骨架/分割播放和关键帧画廊浏览
- **报告生成**：结构化 Markdown 报告，含风险徽章、发现卡片、建议卡片、嵌入关键帧图片

## 用户指南

### 评估模式详解

#### `gait` — 走路步态分析（默认）

适用场景：已能独立行走的宝宝。

工具基于脚踝轨迹检测步态周期，提取 4 个关键相位帧（脚跟着地、站立中期、脚尖离地、摆动中期），计算关节角度和对称性指标，再将视频和结构化数据送入 LLM 进行综合评估。

```bash
uv run gait-assess --video ./baby_walking.mp4 --mode gait --output ./results/
```

#### `developmental` — 运动发育筛查

适用场景：按月龄筛查发育延迟风险。

需要 `--age-months` 参数（如 12 表示 1 岁）。LLM 将观察到的姿态和运动模式与该月龄的标准里程碑进行对比评估。

```bash
uv run gait-assess --video ./baby.mp4 --mode developmental --age-months 12 --output ./results/
```

#### `posture` — 姿势矫正评估

适用场景：静态站立姿态分析。

重点关注脊柱对齐、肩高对称性和骨盆倾斜。被评估者应面向镜头静止站立 3–5 秒。

```bash
uv run gait-assess --video ./baby_standing.mp4 --mode posture --output ./results/
```

### 拍摄建议

为获得最佳评估效果，请按以下建议录制视频：

- **光线**：选择光线充足、均匀的环境，避免逆光或强阴影
- **距离**：手机/相机距离宝宝 2-3 米，确保全身入镜
- **视角**：镜头高度与宝宝腰部平齐，正侧面拍摄效果最佳
- **背景**：选择简洁背景，避免多人同时入镜
- **时长**：录制至少 5-10 秒连续走路视频，让宝宝走 3-5 步以上
- **服装**：避免过于宽松的衣物，建议短袖/短裤以便观察肢体

### 如何理解评估报告

生成的 `report.md` 包含三个主要部分：

**风险徽章** — 顶部的颜色编码指示器：
- 🟢 **正常** — 未检测到明显异常
- 🟡 **轻度** — 轻微偏差，建议 2–4 周后复评观察
- 🟠 **中度** — 存在明显发现，建议咨询儿科医生
- 🔴 **重度** — 显著异常，请尽快寻求专业评估

**发现** — 基于视频和姿态分析的具体观察，例如手臂摆动不对称、膝内翻/外翻、脚跟着地延迟等。

**建议** — 针对发现定制的可操作建议，例如针对性运动、活动建议或随访时间线。

> ⚠️ 本工具仅供参考，不构成医学诊断。如有任何疑虑，请务必咨询专业儿科医生或康复治疗师。

## 开发者指南

### 安装

```bash
# 安装依赖（含开发依赖）
uv sync --extra dev

# 或安装到当前环境
uv pip install -e ".[dev]"
```

YOLO 模型权重文件（`.pt`）存放于 `models/` 目录。首次运行时会自动从 Ultralytics Hub 下载（需联网）。也可手动下载后放入该目录。

### Python API

除了命令行，你也可以在 Python 代码中直接调用评估流水线。

#### 基本用法

```python
from pathlib import Path
from gait_assess import assess, AppConfig

config = AppConfig(
    video=Path("./baby.mp4"),
    output=Path("./results"),
    llm_api_key="your-api-key",
)

result = assess("./baby.mp4", config)

print(result["report_path"])       # Path('.../report.md')
print(result["video_path"])        # Path('.../annotated_video.mp4')
print(result["assessment"].risk_level)  # "正常"
```

#### 模式专用函数

```python
from gait_assess import assess_gait, assess_developmental, assess_posture

# 走路步态评估
gait_result = assess_gait("./baby.mp4", config)

# 运动发育筛查（可省略 age_months，自动从姿态推断）
dev_result = assess_developmental("./baby.mp4", config)

# 姿势矫正评估
posture_result = assess_posture("./baby.mp4", config)
```

#### 返回结果字段

`assess()` 及各模式函数返回包含以下字段的字典：

| 字段 | 类型 | 说明 |
|------|------|------|
| `report_path` | `Path` | Markdown 评估报告文件路径 |
| `video_path` | `Path` | 带标注的可视化视频路径 |
| `viewer_video_path` | `Path` | 交互式查看器用视频路径 |
| `viewer_data_path` | `Path` | 每帧 JSON 数据路径 |
| `viewer_html_path` | `Path \| None` | viewer.html 路径 |
| `assessment` | `AssessmentResult` | LLM 评估结果（风险等级、发现、建议） |
| `gait_cycle` | `GaitCycle` | 步态周期分析结果 |
| `config` | `AppConfig` | 运行时的配置对象 |
| `frames` | `list[np.ndarray]` | 预处理后的帧列表 |
| `fps` | `float` | 视频帧率 |
| `frame_results` | `list[FrameResult]` | 每帧的姿态检测/分割结果 |

#### 跳过 LLM（离线评估）

```python
result = assess("./baby.mp4", config, skip_llm=True)
# assessment.risk_level == "未知"
```

#### 错误处理

```python
from gait_assess.api import AssessmentError

try:
    result = assess("./baby.mp4", config)
except AssessmentError as e:
    print(f"阶段: {e.stage}")    # "preprocess" / "llm"
    print(f"原因: {e.original}") # 原始异常
```

### 输出文件

```
results/
├── report.md              # Markdown 评估报告（含风险徽章、发现/建议卡片）
├── annotated_video.mp4    # 带标注的可视化视频
├── viewer.html            # 交互式报告查看器（逐帧播放 + 关键帧画廊）
└── key_frames/
    ├── frame_00.jpg       # 关键相位帧图片
    ├── frame_01.jpg
    ├── frame_02.jpg
    └── frame_03.jpg
```

`viewer.html` 提供交互式查看体验：
- 逐帧播放，显示骨架连线和分割叠加
- 关键帧画廊，标注相位名称
- 风险徽章和发现/建议卡片以样式化方式渲染

### 架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据处理流水线                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   输入视频                                                                   │
│       │                                                                     │
│       ▼                                                                     │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│   │  视频预处理   │────▶│ YOLOv8-pose  │────▶│ YOLOv8-seg   │               │
│   │(拆帧、去模糊) │     │(17 个关键点)  │     │ (人体分割)    │               │
│   └──────────────┘     └──────────────┘     └──────────────┘               │
│          │                      │                    │                      │
│          └──────────────────────┼────────────────────┘                      │
│                                 ▼                                           │
│                        ┌────────────────┐                                   │
│                        │   姿态指标计算   │                                   │
│                        │(关节角度、对称性 │                                  │
│                        │ 时序轨迹)        │                                 │
│                        └────────┬───────┘                                   │
│                                 │                                           │
│                    ┌────────────┴────────────┐                              │
│                    ▼                         ▼                              │
│           ┌──────────────┐          ┌─────────────────┐                     │
│           │  步态周期分析  │          │   LLM 评估模块   │                     │
│           │(周期检测、    │          │(视频 + 姿态      │                     │
│           │  关键帧提取)  │          │  数据双通道输入)  │                     │
│           └──────┬───────┘          └────────┬────────┘                     │
│                  │                            │                             │
│                  └────────────┬───────────────┘                             │
│                               ▼                                             │
│                    ┌────────────────────┐                                   │
│                    │  报告生成 + 可视化   │                                   │
│                    └─────────┬──────────┘                                   │
│                              │                                              │
│                    ┌─────────┴──────────┐                                   │
│                    ▼                    ▼                                   │
│              report.md        annotated_video.mp4                           │
│              viewer.html                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

关键设计决策：
- **双通道 LLM 输入**：LLM 同时接收完整视频（base64 编码，保留时序连续性）和结构化姿态数据文本（关键帧坐标、关节角度、时序指标）。视频提供上下文理解，姿态数据提供精确坐标。视频比 8 张独立关键帧图片更省 token。
- **Jinja2 提示词模板**：提示词外置为 `prompts/*.jinja.md` 文件。每种评估模式独立模板。新增模式只需新增模板文件，无需修改代码。
- **婴幼儿适配参数**：YOLO 置信度阈值从默认 0.5 下调至 0.3（婴幼儿体型小）。每帧只保留 bbox 面积最大的人形。

### 项目结构

```
src/gait_assess/
  __init__.py          # 包入口
  api.py               # 程序化接口层（assess() 及各模式专用函数）
  cli.py               # 命令行入口与流水线编排
  models.py            # Pydantic 数据模型
  preprocessor.py      # 视频拆帧、模糊过滤、标准化
  pose_segmentor.py    # YOLO-pose + YOLO-seg 推理
  gait_analyzer.py     # 步态周期检测、关键帧提取
  pose_utils.py        # 关节角度、对称性、时序轨迹计算
  llm_assessor.py      # 多模态 LLM 调用、Jinja2 模板渲染
  visualizer.py        # 骨架/mask 叠加、视频编码
  report_generator.py  # Markdown 报告生成
  prompts/             # Jinja2 提示词模板
    gait.jinja.md
    developmental.jinja.md
    posture.jinja.md
models/                # YOLO 模型权重文件（*.pt，被 .gitignore 忽略）
tests/
  fixtures/            # 测试视频
  test_*.py            # 各模块单元测试
```

### 开发

```bash
# 使用 Makefile
make help      # 查看所有命令
make install   # 安装依赖
make test      # 运行测试
make typecheck # 运行静态类型检查
make lint      # 运行代码 lint 检查（ruff）
make e2e       # 端到端验证（跳过 LLM）
make e2e-full  # 端到端验证（含 LLM，需 API 密钥）
make viewer    # 运行 e2e 并自动打开 viewer.html
make clean     # 清理结果

# 或直接运行
uv run pytest
uv run basedpyright src/
```

### 完整 CLI 参数

```bash
uv run gait-assess \
  --video ./baby_walking.mp4 \
  --output ./results/ \
  --mode gait \
  --age-months 12 \
  --conf-threshold 0.3 \
  --blur-threshold 100.0 \
  --target-height 720 \
  --min-duration 3.0 \
  --skip-llm
```

## 免责声明

本工具仅供参考，不构成医学诊断。评估结果基于计算机视觉和大语言模型的分析，可能存在误差。如对宝宝走路姿态有疑虑，请务必咨询专业儿科医生或康复治疗师。

## 许可证

MIT
