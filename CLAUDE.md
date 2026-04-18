# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

婴幼儿走路姿态评估系统。命令行工具，输入家长录制的宝宝走路视频，输出 Markdown 评估报告和带骨架/分割叠加的可视化视频。

核心技术栈：Python >= 3.13, uv, YOLOv8-pose + YOLOv8-seg, supervision, 全模态 LLM (Qwen-VL)。

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

单向流水线（Pipeline），7 个组件依次执行：

```
cli.py ──► preprocessor.py ──► pose_segmentor.py ──► gait_analyzer.py
                                                                │
report_generator.py ◄── visualizer.py ◄── llm_assessor.py ◄─────┘
```

数据通过 Pydantic 模型在组件间传递（定义在 `models.py`）：
- `FrameResult` — 每帧的姿态关键点、分割 mask、检测框
- `KeyFrame` — 步态相位关键帧（含帧索引、相位名称、图像、关键点）
- `GaitCycle` — 关键帧列表、周期起止、步态指标
- `AssessmentResult` — LLM 返回的风险等级、发现、建议、原始响应
- `AppConfig` — CLI 参数与 Pydantic Settings 统一配置

### Key Design Decisions

1. **关键帧策略**：优先基于脚踝 Y 坐标轨迹检测步态周期，提取 4 个相位帧（脚跟着地、站立中期、脚尖离地、摆动中期）。检测失败时退化为均匀采样 8 帧。只将关键帧传给 LLM，控制 token 成本。
2. **LLM 端到端判断**：不预设医学阈值，将关键帧图像 + 姿态数据直接发给全模态 LLM，由模型自行判断异常。
3. **婴幼儿适配**：YOLO 默认置信度阈值从 0.5 下调到 0.3（婴幼儿体型小）。只保留 bbox 面积最大的人形。
4. **优先使用 supervision 进行可视化处理**：视频管道使用 `sv.VideoInfo` + `sv.process_video` 替代手动 `cv2.VideoCapture/Writer` 循环；分割 mask 使用 `sv.MaskAnnotator` 绘制；骨架/关键点/运动轨迹在 supervision annotator 不支持每边/每点不同颜色时退化为手动 `cv2` 绘制。5. **错误处理**：各阶段失败时保留已生成的中间结果，报告失败原因和中间文件路径。

## Project Structure

```
src/gait_assess/
  __init__.py
  cli.py              # 命令行入口与流水线编排
  models.py           # Pydantic 数据模型
  preprocessor.py     # 视频拆帧、模糊过滤、标准化
  pose_segmentor.py   # YOLO-pose + YOLO-seg 推理
  gait_analyzer.py    # 步态周期检测、关键帧提取
  llm_assessor.py     # 多模态 LLM 调用与解析
  visualizer.py       # 骨架/mask 叠加、视频编码
  report_generator.py # Markdown 报告生成
models/               # YOLO 模型权重文件（*.pt，被 .gitignore 忽略）
tests/
  fixtures/           # 测试视频
  test_*.py
```

## Spec-Driven Development

本项目使用 openspec 进行 spec-driven 开发：

- 设计文档：`docs/superpowers/specs/2026-04-18-infant-gait-assessment-design.md`
- openspec changes：`openspec/changes/infant-gait-assessment/`
  - `proposal.md` — 项目提案
  - `design.md` — 技术设计
  - `specs/*/` — 7 个 capability 的详细 spec
  - `tasks.md` — 实现任务清单

运行 `openspec status --change infant-gait-assessment` 查看变更状态。
