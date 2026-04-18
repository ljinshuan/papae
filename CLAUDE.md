# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

婴幼儿姿态评估系统。命令行工具，输入家长录制的宝宝视频，支持三种评估模式：

- **gait（走路步态）**：基于步态周期分析，检测走路姿态异常
- **developmental（运动发育筛查）**：按月龄匹配运动里程碑，筛查发育延迟
- **posture（姿势矫正）**：分析静态站立姿态的脊柱/肩膀/骨盆对称性

输出结构化 Markdown 评估报告（含风险徽章、发现卡片、建议卡片）和带骨架/分割叠加的可视化视频。

核心技术栈：Python >= 3.13, uv, YOLOv8-pose + YOLOv8-seg, supervision, Jinja2, 全模态 LLM (Qwen-VL)。

## Development Commands

```bash
# Install dependencies (including dev)
uv sync --extra dev

# Run static type check
uv run basedpyright src/

# Run tests
uv run pytest

# Run single test file
uv run pytest tests/test_gait_analyzer.py

# Run single test
uv run pytest tests/test_preprocessor.py::test_video_reading -v

# Install package in editable mode
uv pip install -e ".[dev]"

# Run the CLI
uv run gait-assess --video ./baby.mp4 --output ./results/

# Developmental mode
uv run gait-assess --video ./baby.mp4 --mode developmental --age-months 12

# Posture mode
uv run gait-assess --video ./baby.mp4 --mode posture
```

或使用 Makefile：

```bash
make install   # 安装依赖
make test      # 运行测试
make typecheck # 类型检查
make e2e       # 端到端验证（跳过 LLM）
```

## Model Weights

YOLO 模型权重文件（*.pt）存放于 `models/` 目录，默认配置自动使用该目录下的模型：
- `models/yolov8n-pose.pt` — 姿态检测
- `models/yolov8n-seg.pt` — 人体分割

首次运行时会自动下载（需联网）。也可手动下载后放入该目录。

## Architecture

单向流水线（Pipeline），组件依次执行：

```
cli.py ──► api.py ──► preprocessor.py ──► pose_segmentor.py ──► gait_analyzer.py
                          │                           │
                          └──────► pose_utils.py ◄────┘
                                              │
report_generator.py ◄── visualizer.py ◄── llm_assessor.py
```

`api.py` 提供程序化接口层（`assess()` 及各模式专用函数），封装完整流水线供其他 Python 项目导入使用。CLI 入口也可通过 `api.assess()` 调用，实现命令行与程序化接口统一。

数据通过 Pydantic 模型在组件间传递（定义在 `models.py`）：
- `FrameResult` — 每帧的姿态关键点、分割 mask、检测框
- `KeyFrame` — 步态相位关键帧（含帧索引、相位名称、图像、关键点）
- `GaitCycle` — 关键帧列表、周期起止、步态指标
- `PoseMetrics` — 关节角度、对称性指数、时序轨迹等详细姿态指标
- `AssessmentResult` — LLM 返回的风险等级、发现、建议、原始响应、详细指标、置信度
- `AppConfig` — CLI 参数与 Pydantic Settings 统一配置（含 assessment_mode、child_age_months）。LLM 配置（api_key、model、base_url）通过 `.env` 文件或环境变量读取，不通过 CLI 参数传递。

### Key Design Decisions

1. **视频 + 姿态数据双通道输入**：LLM 接收完整视频（base64 编码，保留时序连续性）+ 结构化姿态数据文本（关键帧坐标、关节角度、时序指标），视频给上下文理解，姿态数据给精确坐标，互相校验。视频比 8 张关键帧图片更省 token。
2. **Jinja2 提示词模板**：提示词外置为 `prompts/*.jinja.md` 文件，每个评估模式独立模板，支持变量插值和条件判断。新增模式只需新增模板文件，无需修改代码。
3. **三种评估模式切换**：CLI `--mode` 参数（gait/developmental/posture）+ 模板文件命名约定，`llm_assessor.py` 根据 `config.assessment_mode` 加载对应模板并渲染。默认 gait 模式保持向后兼容。
4. **关键帧策略（gait 模式）**：优先基于脚踝 Y 坐标轨迹检测步态周期，提取 4 个相位帧（脚跟着地、站立中期、脚尖离地、摆动中期）。检测失败时退化为均匀采样 8 帧。
5. **姿态计算通用化**：关节角度（膝、踝、脊柱）、对称性指标（肩高差、骨盆倾斜）等计算提取到 `pose_utils.py`，供三种模式复用。
6. **婴幼儿适配**：YOLO 默认置信度阈值从 0.5 下调到 0.3（婴幼儿体型小）。只保留 bbox 面积最大的人形。
7. **优先使用 supervision 进行可视化处理**：视频管道使用 `sv.VideoInfo` + `sv.process_video` 替代手动 `cv2.VideoCapture/Writer` 循环；分割 mask 使用 `sv.MaskAnnotator` 绘制；骨架/关键点/运动轨迹在 supervision annotator 不支持每边/每点不同颜色时退化为手动 `cv2` 绘制。
8. **报告美化**：通过 HTML 标签（`<div class="badge-risk-normal">`）和 CSS 片段实现风险徽章、发现卡片、建议卡片的视觉美化，在 `viewer.html` 中自动渲染。
9. **错误处理**：各阶段失败时保留已生成的中间结果，报告失败原因和中间文件路径。

## Project Structure

```
src/gait_assess/
  __init__.py
  api.py              # 程序化接口层（assess() 及模式专用函数）
  cli.py              # 命令行入口与流水线编排
  models.py           # Pydantic 数据模型
  preprocessor.py     # 视频拆帧、模糊过滤、标准化
  pose_segmentor.py   # YOLO-pose + YOLO-seg 推理
  gait_analyzer.py    # 步态周期检测、关键帧提取
  pose_utils.py       # 关节角度、对称性、时序轨迹计算工具
  llm_assessor.py     # 多模态 LLM 调用（视频+姿态数据）、Jinja2 模板渲染
  visualizer.py       # 骨架/mask 叠加、视频编码
  report_generator.py # Markdown 报告生成（多模式、美化样式）
  prompts/            # Jinja2 提示词模板
    gait.jinja.md
    developmental.jinja.md
    posture.jinja.md
models/               # YOLO 模型权重文件（*.pt，被 .gitignore 忽略）
tests/
  fixtures/           # 测试视频
  test_*.py           # 各模块单元测试
```

## Spec-Driven Development

本项目使用 openspec 进行 spec-driven 开发：

- 初始设计文档：`docs/superpowers/specs/2026-04-18-infant-gait-assessment-design.md`
- openspec changes：
  - `openspec/changes/infant-gait-assessment/` — 初始项目实现
    - `proposal.md` — 项目提案
    - `design.md` — 技术设计
    - `specs/*/` — 7 个 capability 的详细 spec
    - `tasks.md` — 实现任务清单
  - `openspec/changes/expand-developmental-posture-assessment/` — 扩展三模式评估
    - `proposal.md` / `design.md` / `specs/*/` / `tasks.md`

运行 `openspec status --change <change-name>` 查看变更状态。
