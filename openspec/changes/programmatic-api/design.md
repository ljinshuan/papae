## Context

当前流水线编排逻辑全部硬编码在 `cli.py` 的 `main()` 函数中，各组件按顺序实例化并调用。CLI 同时负责：参数解析、配置构造、流水线执行、错误处理、输出打印。这种紧耦合使得无法在其他上下文中复用流水线。

## Goals / Non-Goals

**Goals:**
1. 将流水线编排逻辑从 CLI 中提取到独立的 `api.py` 模块
2. 提供高级 `assess()` 函数封装完整流水线
3. 提供模式专用函数 `assess_gait()` / `assess_developmental()` / `assess_posture()`
4. `__init__.py` 导出所有公共 API，支持 `from gait_assess import ...`
5. CLI 重构为轻量级参数解析层，调用 api.py 执行实际工作

**Non-Goals:**
- 不改各组件（preprocessor/segmentor/analyzer 等）的内部实现
- 不引入异步 API（保持同步接口）
- 不改现有的 Pydantic 数据模型
- 不提供 Web 框架集成（如 FastAPI 路由）

## Decisions

### 1. API 分层设计
**选择：两层 API（高级 + 低级）**

- 高级 API：`assess(video, config)` — 一键完成整个流水线，返回结果字典
- 低级 API：直接实例化各组件类，手动控制流水线步骤

选择理由：高级 API 满足 80% 的用例（"给我评估结果"）；低级 API 满足高级用例（自定义步骤、调试、部分复用）。

### 2. 结果返回格式
**选择：返回 `dict[str, Any]`，包含所有输出路径和结构化数据**

```python
{
    "report_path": Path("results/report.md"),
    "video_path": Path("results/annotated_video.mp4"),
    "viewer_path": Path("results/viewer.html"),
    "assessment": AssessmentResult,
    "gait_cycle": GaitCycle,
    "config": AppConfig,
}
```

替代方案：返回自定义 Pydantic 模型。

选择理由：字典足够简单直观，不需要引入新的模型类；用户可直接访问各字段。

### 3. CLI 重构策略
**选择：CLI 调用 `api.py` 中的高级函数，保留现有 CLI 行为不变**

`cli.py` 负责：参数解析 → 构造 `AppConfig` → 调用 `api.assess()` → 打印结果

这样 CLI 代码大幅简化，且保证 CLI 和 API 行为一致。

### 4. 错误处理
**选择：API 层捕获所有异常并包装为 `AssessmentError`**

API 调用者可以统一捕获 `AssessmentError`，也可以通过异常链访问原始异常。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| CLI 重构引入 regression | CLI 测试保持不变，确保重构前后行为一致 |
| API 暴露的符号过多导致维护负担 | 仅导出核心类 + 高级函数，内部实现细节不导出 |
| `assess()` 函数参数过多 | 使用 `AppConfig` 作为单一配置入口，API 只接受 video + config |

## Migration Plan

1. 创建 `api.py`，实现 `assess()` 函数（提取 cli.py 中的流水线逻辑）
2. 重构 `cli.py`，调用 `api.assess()`
3. 更新 `__init__.py`，导出公共 API
4. 新增 `test_api.py` 测试
5. 运行全部测试确保无 regression
6. 更新 README 添加 Python API 示例

## Open Questions

1. 是否需要支持生成结果但不写入文件（返回内存中的数据）？
2. API 是否应该支持传入已预处理的帧列表（跳过预处理步骤）？
