## 1. 修复 preprocessor 返回缩放比例

- [x] 1.1 `VideoPreprocessor.process()` 返回 `(frames, fps, scale)`，scale 为实际缩放比例
- [x] 1.2 当原始高度 <= target_height 时，scale = 1.0
- [x] 1.3 更新 cli.py 中调用处，使用返回的 scale 替代重新计算

## 2. 修复 Visualizer 坐标缩放

- [x] 2.1 `Visualizer.render()` 接收 `preprocess_scale` 参数
- [x] 2.2 `render()` 中将 keypoints、bbox 坐标缩放回原始尺寸后再绘制
- [x] 2.3 `render()` 中将 mask 通过 cv2.resize 缩放到原始帧尺寸
- [x] 2.4 更新 cli.py 中 `render()` 调用，传入 scale

## 3. 修复 generate_viewer_data 中的 mask 缩放

- [x] 3.1 `generate_viewer_data()` 将 mask 缩放到原始视频分辨率
- [x] 3.2 per-frame.json 中标注 mask 的原始尺寸（供前端校验）
- [x] 3.3 验证低分辨率视频时 coord_scale = 1.0，坐标不被错误缩小

## 4. 修复前端 mask 高亮

- [x] 4.1 排查 viewer.html 中 mask 未渲染的原因
- [x] 4.2 修复 mask 绘制逻辑（处理异步加载、尺寸问题）
- [x] 4.3 验证不同分辨率视频下 mask 高亮正常显示

## 5. 验证

- [x] 5.1 运行 e2e 测试验证修复效果
- [x] 5.2 检查不同类型视频（高分辨率、低分辨率、竖屏）的渲染结果
