## Why

预处理时将视频缩放到 `target_height`（默认 720px）后运行姿态检测，生成的 bbox/keypoints/mask 坐标基于缩放后的分辨率。但可视化阶段（annotated_video.mp4 和 viewer.html）使用原始尺寸视频，导致坐标系统不匹配，绘制位置完全错误。此外，低分辨率视频（高度 <= target_height）时，坐标被反向缩小，问题更严重。分割高亮（mask overlay）在前端查看器中未生效，需要排查修复。

## What Changes

- **修复 `preprocess_scale` 计算逻辑**：低分辨率视频（原始高度 <= target_height）时不应缩放坐标
- **修复 `Visualizer.render()` 坐标系统**：annotated_video.mp4 的骨架/bbox/mask 绘制也需要缩放回原始视频尺寸
- **修复 mask 尺寸对齐**：`generate_viewer_data()` 中的 mask 需缩放回原始视频分辨率，或在 per-frame.json 中标注 mask 原始尺寸
- **修复前端 mask 高亮**：排查 viewer.html 中 mask 未渲染的问题并修复
- **修复步宽等像素指标的坐标系统**：gait_analyzer 的步宽计算基于预处理坐标，需明确含义或修复

## Capabilities

### New Capabilities

（无新增功能，纯 bug 修复）

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

- `src/gait_assess/cli.py` — `preprocess_scale` 计算逻辑
- `src/gait_assess/visualizer.py` — `render()` 和 `generate_viewer_data()` 的坐标缩放
- `src/gait_assess/viewer.html` — mask 渲染逻辑
- `src/gait_assess/gait_analyzer.py` — 步宽等像素指标的含义（可选）
