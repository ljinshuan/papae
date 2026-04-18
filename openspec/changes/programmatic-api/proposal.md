## Why

当前项目虽然已是 pip 包（有 pyproject.toml），但 `__init__.py` 仅暴露 `__version__`，所有功能只能通过 CLI 入口 `gait-assess` 调用。用户希望将项目作为 Python 库被其他项目依赖，在非命令行环境（如 Web 后端、Jupyter Notebook、自动化脚本）中直接调用各组件。

## What Changes

- **暴露核心组件**：在 `__init__.py` 中导出各流水线组件（Preprocessor、PoseSegmentor、GaitAnalyzer、LLMAssessor、Visualizer、ReportGenerator）
- **新增高级 API**：提供 `gait_assess.assess()` 等函数，封装完整流水线，返回结构化结果
- **新增按模式 API**：`assess_gait()`、`assess_developmental()`、`assess_posture()` 等模式专用函数
- **重构 CLI**：CLI 内部调用新的高级 API，避免重复实现流水线编排逻辑
- **更新文档**：README 中添加 Python API 使用示例

## Capabilities

### New Capabilities
- `programmatic-api`: 提供 Python 程序化接口，支持在其他项目中 import 和调用

### Modified Capabilities
- （无现有 spec 需要修改，此为纯实现层面变更）

## Impact

- `src/gait_assess/__init__.py` — 新增导出符号
- `src/gait_assess/api.py`（新增）— 高级 API 封装
- `src/gait_assess/cli.py` — 重构为调用 api.py
- `README.md` — 新增 Python API 使用示例
- `tests/` — 新增 API 测试
