## 1. 修改 preprocessor 返回全部帧

- [x] 1.1 `VideoPreprocessor.process()` 返回 `(frames, fps, scale, frame_qualities)`
- [x] 1.2 `frame_qualities` 为每帧的 Laplacian 方差列表
- [x] 1.3 不再丢弃模糊帧，只标记质量分数
- [x] 1.4 更新相关单元测试

## 2. 修改 cli.py 使用全部帧

- [x] 2.1 接收 `frame_qualities` 并传给下游组件
- [x] 2.2 移除模糊帧相关的帧数校验逻辑

## 3. 修改 gait_analyzer 适配全部帧

- [x] 3.1 `extract_cycles()` 接收 `frame_qualities` 参数
- [x] 3.2 轨迹提取只使用清晰帧（quality >= threshold）
- [x] 3.3 关键帧索引指向原始视频帧号
- [x] 3.4 退化采样在全部帧范围内均匀采样
- [x] 3.5 更新相关单元测试

## 4. 修改 visualizer 适配全部帧

- [x] 4.1 `render()` 处理全部帧，有检测结果才绘制
- [x] 4.2 `generate_viewer_data()` 输出全部帧（未检测到为空值）
- [x] 4.3 `frame_count` = 原始视频帧数
- [x] 4.4 更新相关单元测试

## 5. 修改前端适配

- [x] 5.1 `viewer.html` 进度条范围设为原始帧数
- [x] 5.2 视频 currentTime 与帧号映射正确

## 6. 端到端验证

- [x] 6.1 运行 e2e，检查 bbox/mask/骨架是否对齐人物
- [x] 6.2 浏览器查看四个面板效果
