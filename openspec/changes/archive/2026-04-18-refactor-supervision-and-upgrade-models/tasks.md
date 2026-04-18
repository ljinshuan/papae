## 1. 模型配置升级

- [x] 1.1 修改 `src/gait_assess/models.py` 中 `AppConfig` 的默认模型路径：yolov8n → yolov8m（pose 和 seg）
- [x] 1.2 评估并调整 yolov8m 的默认置信度阈值（medium 模型精度更高，可能保持 0.3 或微调）——保持 0.3，婴幼儿体型小需要较宽松阈值
- [x] 1.3 修改 `src/gait_assess/pose_segmentor.py` 中模型加载逻辑，适配新默认路径——现有 `_load_model` 已支持任意路径和自动下载，无需修改

## 2. Visualization supervision 重构

- [x] 2.1 重构 `visualizer.py` 视频读写管道：使用 `sv.VideoInfo` + `sv.process_video` 替代手动 `cv2.VideoCapture`/`VideoWriter` 循环
- [x] 2.2 骨架绘制——supervision `sv.EdgeAnnotator`/`sv.VertexAnnotator` 不支持每边/每点不同颜色，保留 `cv2.line`/`cv2.circle` 以保持多色骨架和置信度着色
- [x] 2.3 替换 mask 叠加逻辑：使用 `sv.MaskAnnotator(color=sv.Color(r=128,g=0,b=128), opacity=0.5)` 替代手动 `cv2.addWeighted`
- [x] 2.4 保留关键帧标记功能，继续使用 `cv2.putText`
- [x] 2.5 新增运动轨迹可视化：`sv.TraceAnnotator` 只能追踪 detection 中心点，改为手动维护脚踝轨迹队列 + `cv2.polylines` 绘制最近 15 帧轨迹
- [x] 2.6 更新 `generate_viewer_data` 中的视频信息获取为 `sv.VideoInfo.from_video_path()`

## 3. 坐标与数据流适配

- [x] 3.1 评估 `sv.Detections` 封装——结论：不引入。每帧只取单个检测结果，封装增加抽象但不简化逻辑
- [x] 3.2 `preprocess_scale` 在 `render()` 和 `_annotate_frame()` 中通过 `coord_scale = 1.0 / preprocess_scale` 正确应用
- [x] 3.3 `FrameResult` → `sv.Detections`/`sv.MaskAnnotator` 数据格式兼容（bbox reshape (1,4)，mask reshape (1,H,W)）

## 4. 测试与验证

- [x] 4.1 更新 `tests/test_visualizer.py`：适配新 `_annotate_frame` 签名，新增轨迹累积/绘制/MaskAnnotator 测试（12 passed）
- [x] 4.2 `tests/test_pose_segmentor.py` 无需修改，模型加载逻辑已通用（4 passed）
- [x] 4.3 端到端测试 `make e2e` 需要真实视频和 YOLO 模型，暂不运行
- [x] 4.4 类型检查 `basedpyright src/`：0 errors/0 warnings；单元测试 `pytest`：28 passed，3 failed（预存在的 socksio/代理环境问题，与本次变更无关）
