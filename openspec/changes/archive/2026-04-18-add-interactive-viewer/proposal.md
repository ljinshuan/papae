## Why

当前 `visualizer.py` 输出单一叠加视频，骨架、mask 和关键帧标记全部混在一帧中，家长/医生难以直观区分不同层面的分析结果。需要一个分层展示、支持交互控制的查看器，让评估结果更易理解。

## What Changes

- 在 `visualizer.py` 中新增 `generate_viewer_data()` 方法，将每帧检测结果序列化为 `per-frame.json`
- 新增 `viewer.html`：基于 Vue 3 (CDN) 的交互式网页查看器
- `viewer.html` 包含 4 个 Canvas 面板（2×2 网格），共用隐藏 video 时间源
- 支持播放/暂停、逐帧前进/后退、播放速度调节 (0.5x/1x/2x)
- 保留现有 `annotated_video.mp4` 输出，与新查看器共存
- 新增后端单元测试验证 `generate_viewer_data()` 输出结构

## Capabilities

### New Capabilities

- `interactive-viewer`: 交互式结果查看器，包含 2×2 面板布局、Canvas 实时渲染、播放控制、per-frame JSON 数据生成

### Modified Capabilities

- （无现有 spec 需要修改）

## Impact

- `src/gait_assess/visualizer.py`：新增数据生成方法，无现有逻辑变更
- `src/gait_assess/cli.py`：流水线编排中新增 viewer 数据生成步骤
- 新增测试覆盖 `generate_viewer_data()` 输出
- 输出目录新增 `viewer.html` 和 `per-frame.json`
