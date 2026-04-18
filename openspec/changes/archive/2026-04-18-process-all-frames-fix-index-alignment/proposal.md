## Why

preprocessor 对每帧做模糊检测后只保留"清晰帧"（274/690），导致下游所有组件的帧索引与原始视频错位。visualizer 用后端帧索引去原始视频中取帧绘制，mask/bbox/骨架都画在了错误的位置。用户要求优先处理全部 690 帧，保持帧索引一致。

## What Changes

- **preprocessor 返回全部帧**：不再丢弃模糊帧，而是返回所有帧 + 每帧质量分数
- **姿态检测在全部帧上运行**：YOLO 在全部 690 帧上推理，模糊帧可能检测失败（keypoints 为空），但索引保持对齐
- **移除帧数错位**：visualizer 的 frame_index 直接对应原始视频帧号，无需映射
- **步态分析使用有效帧子集**：周期检测仍只使用清晰帧，但关键帧索引指向原始视频帧号
- **per-frame.json 包含全部帧**：前端可以播放完整视频，未检测到的帧显示"未检测到"

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

- `preprocessor.py` — 返回全部帧，新增 frame_quality 字段
- `cli.py` — 移除模糊帧过滤后的帧数不匹配逻辑
- `models.py` — FrameResult 可能需要添加 quality 字段
- `gait_analyzer.py` — 周期检测只使用清晰帧，但索引指向原始帧
- `visualizer.py` — 渲染全部帧，未检测到的不标注
- `viewer.html` — 进度条范围变为原始帧数
