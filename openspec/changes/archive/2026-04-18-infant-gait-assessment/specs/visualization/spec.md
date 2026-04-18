## ADDED Requirements

### Requirement: COCO 骨架绘制
系统 SHALL 在视频帧上绘制 COCO 格式的骨架连线。

#### Scenario: 绘制标准骨架
- **WHEN** 帧具有有效的 17 个关键点
- **THEN** 系统按 COCO 连接规则绘制骨骼连线（不同肢体使用不同颜色）

#### Scenario: 关键点置信度可视化
- **WHEN** 某些关键点置信度较低
- **THEN** 低置信度点使用较浅颜色或虚线连接

### Requirement: 分割 mask 叠加
系统 SHALL 在视频帧上叠加半透明的人体分割 mask。

#### Scenario: 正常叠加
- **WHEN** 帧具有有效的分割 mask
- **THEN** mask 区域以半透明彩色覆盖在人物上

### Requirement: 关键帧标记
系统 SHALL 在输出视频的进度条或时间轴上标记关键帧位置。

#### Scenario: 标记关键相位
- **WHEN** 某帧被识别为关键帧（如脚跟着地）
- **THEN** 该帧在视频底部显示标记线和相位名称（如"脚跟着地"）

### Requirement: 视频编码输出
系统 SHALL 将标注后的帧序列编码为 MP4 视频文件。

#### Scenario: 标准输出
- **WHEN** 所有帧标注完成
- **THEN** 系统输出 H.264 编码的 MP4 文件，帧率与原始视频一致

#### Scenario: 输出路径自定义
- **WHEN** 用户指定输出目录
- **THEN** 可视化视频保存到该目录，文件名为 `annotated_video.mp4`

### Requirement: 标注信息持久化
系统 SHALL 支持保存每帧的标注数据（非必须编码为视频）。

#### Scenario: 保存标注数据
- **WHEN** 用户需要二次处理
- **THEN** 系统可选输出每帧的关键点和 mask 为 JSON/CSV 格式
