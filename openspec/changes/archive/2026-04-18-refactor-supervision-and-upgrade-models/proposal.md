## Why

当前 `visualizer.py` 虽然导入了 `supervision`，但所有绘制逻辑仍使用原始 OpenCV 手动实现，既未发挥 supervision 在标注抽象、轨迹追踪和视频管道方面的优势，也导致代码冗长。同时，婴幼儿体型较小，YOLOv8 nano 模型（yolov8n-pose/seg）的关键点精度和分割质量有限，升级到 medium 尺寸可显著提升检测质量，使步态评估更可靠。

## What Changes

- **重构可视化**：将 `visualizer.py` 中手写的 OpenCV 绘制逻辑替换为 supervision 的 annotator（骨架/关键点 `sv.EdgeAnnotator` + `sv.VertexAnnotator`，mask `sv.MaskAnnotator`，轨迹 `sv.TraceAnnotator`）。
- **模型升级**：默认模型从 `yolov8n-pose.pt` / `yolov8n-seg.pt` 升级到 `yolov8m-pose.pt` / `yolov8m-seg.pt`。
- **视频管道简化**：使用 `sv.VideoInfo` 和 `sv.process_video` 替代手动的 `cv2.VideoCapture` / `VideoWriter` 循环。
- **坐标处理统一**：借助 supervision 的 `sv.Detections` 及相关变换工具，简化坐标缩放和 mask  resize 逻辑。
- **配置更新**：`AppConfig` 中的默认模型路径和检测阈值相应调整。

## Capabilities

### New Capabilities
- （无新增 capability，本次为纯重构和配置升级）

### Modified Capabilities
- `visualization`: 绘制实现从原始 OpenCV 改为 supervision annotator，新增运动轨迹可视化，简化视频读写管道。
- `pose-segmentation`: 默认模型权重从 nano 升级到 medium，相关置信度阈值和预处理参数需适配新模型特性。

## Impact

- **代码**：`src/gait_assess/visualizer.py`、`src/gait_assess/pose_segmentor.py`、`src/gait_assess/cli.py`、`src/gait_assess/models.py`
- **依赖**：保持 `supervision>=0.22`，实际利用其全部 API
- **性能**：模型更大，推理延迟增加，但精度和 recall 提升
- **模型文件**：`models/` 目录需下载新的 `.pt` 权重（YOLOv8m 约 50MB，nano 约 6MB）
