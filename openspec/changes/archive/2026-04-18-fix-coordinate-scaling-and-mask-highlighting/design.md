## Context

当前流水线：
1. `preprocessor` 将视频缩放到 `target_height`（默认 720px），保持宽高比
2. `pose_segmentor` 在缩放后的帧上运行 YOLO，bbox/keypoints 坐标基于缩放尺寸
3. `visualizer.render()` 读取原始尺寸帧，但坐标是缩放后的 —— 绘制位置错误
4. `visualizer.generate_viewer_data()` 通过 `preprocess_scale` 将坐标放大回原始尺寸，但 `preprocess_scale` 计算逻辑在低分辨率视频时错误
5. 前端 viewer.html 中 mask 高亮未生效

## Goals / Non-Goals

**Goals:**
- 所有坐标（bbox、keypoints、mask）在最终输出（annotated_video.mp4、per-frame.json、viewer.html）中统一对齐到原始视频尺寸
- 低分辨率视频（高度 <= target_height）时，坐标不被错误缩放
- 前端 mask 高亮正常显示

**Non-Goals:**
- 修改预处理策略（仍保持 target_height 缩放）
- 修改 YOLO 推理逻辑
- 修改步态周期检测算法

## Decisions

**Decision 1: 将 `preprocess_scale` 从 cli.py 移到 preprocessor.py**
- `VideoPreprocessor.process()` 返回 `(frames, fps, scale)`，scale 为实际缩放比例
- 优势：preprocessor 最清楚是否进行了缩放，避免 cli.py 重新计算导致的不一致
- 当原始高度 <= target_height 时，scale = 1.0（不缩放）

**Decision 2: `Visualizer.render()` 接收 scale 参数**
- 在绘制前将 keypoints 和 bbox 坐标放大到原始尺寸
- mask 通过 cv2.resize 缩放到原始帧尺寸

**Decision 3: `generate_viewer_data()` 中的 mask 同步缩放**
- mask 从预处理分辨率缩放到原始视频尺寸
- 在 per-frame.json 中标注 mask 的原始尺寸，供前端校验

**Decision 4: 前端 mask 渲染修复**
- viewer.html 中 mask 的 `img.width/height` 可能为 0 或异步加载未完成
- 改用 `naturalWidth/naturalHeight`，并在 drawImage 时传入目标尺寸

## Risks / Trade-offs

- [Risk] mask resize 可能引入轻微模糊 → Mitigation: 使用 cv2.INTER_NEAREST 保持二值化特性
- [Risk] 低分辨率视频的步宽指标仍基于预处理坐标 → 当前不修改，因为步宽只用于相对比较
