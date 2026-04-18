## Context

当前 `visualizer.py` 虽然导入了 `supervision`，但所有骨架绘制、关键点标注、mask 叠加和文字标记均使用原始 OpenCV (`cv2.line`, `cv2.circle`, `cv2.addWeighted`, `cv2.putText`) 手动实现。这种方式虽然灵活，但代码冗长（约 230 行），且未利用 supervision 提供的标准化 annotator 和轨迹追踪能力。

同时，婴幼儿体型较小、动作较快，YOLOv8 nano 模型（yolov8n-pose/seg）在关键点定位精度和分割边缘质量上存在瓶颈，容易导致步态周期检测误差和 LLM 评估输入质量下降。

## Goals / Non-Goals

**Goals:**
- 将 `visualizer.py` 中的手动 OpenCV 绘制逻辑替换为 supervision annotator，保持视觉输出风格一致或更优
- 新增运动轨迹可视化（脚踝/脚跟轨迹），提升步态分析的可解释性
- 使用 `sv.process_video` / `sv.VideoInfo` 简化视频读写管道
- 将默认模型从 yolov8n 升级到 yolov8m，提升关键点精度和分割质量
- 适配新模型的置信度阈值和预处理参数

**Non-Goals:**
- 不修改 LLM 评估逻辑或报告格式
- 不修改步态周期检测算法（gait_analyzer.py 的核心逻辑不变，只受益于更好的输入数据）
- 不引入新的外部依赖
- 不改变 CLI 用户接口（参数名和默认值不变，仅内部默认值变化）

## Decisions

### 1. 使用 supervision annotator 替代手动 cv2 绘制
- **选择**: `sv.EdgeAnnotator` + `sv.VertexAnnotator` 绘制骨架和关键点；`sv.MaskAnnotator` 或 `sv.PolygonAnnotator` 处理分割；`sv.TraceAnnotator` 绘制轨迹
- **理由**: supervision 的 annotator 封装了坐标变换、颜色管理和批量绘制，代码更简洁，且自动处理高 DPI 和半透明混合。`TraceAnnotator` 可以追踪关键点的时序轨迹，对步态分析有独特价值（手动实现需要维护历史坐标队列）。
- **替代方案**: 保留手动 cv2 绘制（保持现状），但代码维护成本高，且无法复用 supervision 的高级功能。

### 2. 使用 `sv.process_video` 替代手动 VideoCapture 循环
- **选择**: `sv.process_video(source_path, target_path, callback)` 管道
- **理由**: 自动处理视频编码器选择、帧率保持、多线程解码，减少样板代码约 30 行。`sv.VideoInfo` 替代手动的 `cv2.VideoCapture` 属性读取。
- **替代方案**: 保留手动循环，更灵活但冗余。

### 3. 模型升级到 yolov8m
- **选择**: 默认 pose/seg 模型从 nano (yolov8n) 升级到 medium (yolov8m)
- **理由**: yolov8m 在 COCO keypoints 上的 AP 比 yolov8n 高约 8-10 个百分点，分割 mask 边缘更平滑。婴幼儿体型小，nano 模型在远处/低分辨率下容易漏检或关键点漂移。
- **权衡**: 推理延迟增加约 3-4 倍（nano ~5ms/frame → medium ~18ms/frame），但仍在可接受范围（30fps 视频每帧 33ms 预算）。GPU 显存占用增加约 4 倍。
- **替代方案**: 升级到 yolov8s（small，折中方案），但 medium 的精度提升对医学评估类应用更有价值。

### 4. 保留预处理缩放策略不变
- **选择**: `preprocessor.py` 的视频缩放逻辑不变，supervision 负责在可视化阶段将坐标缩放回原始尺寸
- **理由**: 预处理缩放是为了加速推理，不应因可视化重构而改变。supervision 的 `sv.Detections` 和 annotator 支持坐标变换。

## Risks / Trade-offs

- **[风险] 轨迹可视化过于复杂，影响视频可读性** → **缓解**: `TraceAnnotator` 配置较短的轨迹长度（如最近 15 帧），使用半透明颜色，仅在关键帧附近显示
- **[风险] yolov8m 推理速度过慢，导致视频处理时间翻倍** → **缓解**: 提供配置项允许用户回退到 nano 模型；在文档中注明性能差异
- **[风险] supervision annotator 的默认样式与现有风格差异过大** → **缓解**: 通过 `sv.ColorPalette` 和自定义颜色映射保持与现有 COCO_SKELETON 配色方案一致
- **[风险] mask annotator 的叠加方式与当前半透明紫色不同** → **缓解**: supervision 的 `sv.MaskAnnotator` 支持自定义颜色和透明度，可匹配现有视觉风格

## Migration Plan

1. **开发阶段**: 在 feature branch 上完成重构，保持现有测试通过
2. **验证阶段**: 使用相同测试视频对比 nano 和 medium 模型的输出质量
3. **部署阶段**: 合并到 main，CI 通过即可
4. **回滚策略**: 模型路径和阈值通过 `AppConfig` 配置，紧急回滚只需修改配置文件

## Open Questions

- `sv.TraceAnnotator` 是否支持只对特定关键点（如脚踝）追踪，还是会对所有检测到的点追踪？需要验证 API 行为。
- yolov8m 在婴幼儿数据集上的实际精度提升幅度需通过端到端测试验证。
