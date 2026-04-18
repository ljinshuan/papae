## MODIFIED Requirements

### Requirement: COCO 骨架绘制
系统 SHALL 使用 supervision 的 annotator 在视频帧上绘制 COCO 格式的骨架连线和关键点。

#### Scenario: 绘制标准骨架
- **WHEN** 帧具有有效的 17 个关键点
- **THEN** 系统使用 `sv.EdgeAnnotator` 和 `sv.VertexAnnotator` 按 COCO 连接规则绘制骨骼连线和关键点（不同肢体使用不同颜色）

#### Scenario: 关键点置信度可视化
- **WHEN** 某些关键点置信度较低
- **THEN** 低置信度点使用较浅颜色或更小半径显示

### Requirement: 分割 mask 叠加
系统 SHALL 使用 supervision 的 `sv.MaskAnnotator` 在视频帧上叠加半透明的人体分割 mask。

#### Scenario: 正常叠加
- **WHEN** 帧具有有效的分割 mask
- **THEN** `sv.MaskAnnotator` 以半透明彩色覆盖在人物上，颜色与现有紫色风格一致

### Requirement: 视频编码输出
系统 SHALL 使用 `sv.process_video` 将标注后的帧序列编码为 MP4 视频文件。

#### Scenario: 标准输出
- **WHEN** 所有帧标注完成
- **THEN** 系统通过 `sv.process_video` 输出 H.264 编码的 MP4 文件，帧率与原始视频一致

#### Scenario: 输出路径自定义
- **WHEN** 用户指定输出目录
- **THEN** 可视化视频保存到该目录，文件名为 `annotated_video.mp4`

## ADDED Requirements

### Requirement: 运动轨迹可视化
系统 SHALL 在关键帧附近绘制脚踝/脚跟的运动轨迹。

#### Scenario: 轨迹绘制
- **WHEN** 连续多帧检测到有效脚踝关键点
- **THEN** 系统使用 `sv.TraceAnnotator` 绘制最近 15 帧的脚踝运动轨迹，轨迹线使用半透明颜色

#### Scenario: 轨迹与关键帧对齐
- **WHEN** 当前帧为步态相位关键帧
- **THEN** 轨迹线终点标记在关键帧位置，直观展示该相位前的运动路径
