## Context

当前流水线：preprocessor 模糊过滤后只返回 274 帧，下游把这 274 帧当作原始视频处理，导致 visualizer 在渲染原始 690 帧视频时索引错位。

## Goals / Non-Goals

**Goals:**
- 后端帧索引与原始视频帧号 1:1 对齐
- 姿态检测覆盖全部帧
- visualizer 和前端直接按原始帧号渲染

**Non-Goals:**
- 不修改 YOLO 推理逻辑
- 不修改 viewer.html 的 UI 布局
- 不修改报告生成逻辑

## Decisions

**Decision 1: preprocessor 返回全部帧 + 质量列表**
- `process()` 返回 `(frames, fps, scale, frame_qualities)`
- `frame_qualities[i]` 是第 i 帧的 Laplacian 方差值
- 清晰帧阈值仍为 `blur_threshold`，但只做标记不做丢弃

**Decision 2: 下游组件接收全部帧**
- `PoseSegmentor.infer()` 在全部帧上运行
- 模糊帧可能检测为空，但 `frame_results[i]` 对应原始第 i 帧
- `Visualizer.render()` 按顺序处理全部帧，有检测结果就画，没有就跳过

**Decision 3: 步态分析只使用清晰帧**
- `GaitAnalyzer.extract_cycles()` 遍历全部帧，但只把清晰帧加入 ankle_y 轨迹
- 关键帧索引指向原始视频帧号
- 退化的均匀采样也在全部帧范围内进行

**Decision 4: per-frame.json 包含全部帧**
- `frame_count` = 原始视频帧数（690）
- 未检测到人物的帧：bbox=[]、keypoints=null、mask=null
- 前端进度条直接显示原始帧号

## Risks / Trade-offs

- [Risk] YOLO 在全部 690 帧上推理时间增加约 2.5 倍 → Mitigation: 这是正确性的代价，无更好方案
- [Risk] 大量模糊帧的检测结果为空，可能影响步态周期检测准确性 → Mitigation: 周期检测只使用清晰帧的轨迹
