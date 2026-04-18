## 1. API 模块创建

- [x] 1.1 创建 `src/gait_assess/api.py`，实现 `assess(video, config)` 函数
- [x] 1.2 `api.py`: 实现 `assess_gait(video, config)`、`assess_developmental(video, config)`、`assess_posture(video, config)` 模式函数
- [x] 1.3 `api.py`: 实现统一的错误处理（`AssessmentError`）

## 2. CLI 重构

- [x] 2.1 `cli.py`: 移除流水线执行逻辑，改为调用 `api.assess()`
- [x] 2.2 `cli.py`: 保留参数解析、错误打印、退出码逻辑
- [x] 2.3 运行 CLI 测试确认行为不变

## 3. 包导出

- [x] 3.1 `__init__.py`: 导出 `assess`、`assess_gait`、`assess_developmental`、`assess_posture`
- [x] 3.2 `__init__.py`: 导出所有核心组件类（Preprocessor、Segmentor、Analyzer 等）
- [x] 3.3 `__init__.py`: 导出所有数据模型（AppConfig、AssessmentResult、GaitCycle 等）

## 4. 测试

- [x] 4.1 新增 `test_api.py`: 测试 `assess()` 成功流程
- [x] 4.2 新增 `test_api.py`: 测试模式专用函数
- [x] 4.3 新增 `test_api.py`: 测试错误处理
- [x] 4.4 运行 `uv run pytest` 确保所有测试通过

## 5. 文档

- [x] 5.1 `README.md`: 添加 "Python API" 使用示例
- [x] 5.2 `CLAUDE.md`: 更新架构说明，提及 api.py
