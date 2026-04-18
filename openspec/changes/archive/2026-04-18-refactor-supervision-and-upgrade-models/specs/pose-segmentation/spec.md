## MODIFIED Requirements

### Requirement: 人体姿态检测
系统 SHALL 对每帧图像运行 YOLO-pose 模型，检测人体并输出 17 个 COCO 格式关键点。

#### Scenario: 单人物检测
- **WHEN** 帧中有一个宝宝全身可见
- **THEN** 系统返回 1 个人的 17 个关键点坐标（x, y, confidence）

#### Scenario: 未检测到人体
- **WHEN** 帧中没有检测到人体，或置信度低于阈值
- **THEN** 系统跳过该帧，并在最终报告中提示"部分帧未检测到人物"

#### Scenario: 检测到多个人
- **WHEN** 帧中检测到多个人
- **THEN** 系统只保留 bbox 面积最大的人，其余忽略

### Requirement: 人体实例分割
系统 SHALL 对每帧图像运行 YOLO-seg 模型，输出每个人体的分割 mask。

#### Scenario: 正常分割
- **WHEN** 帧中检测到人体
- **THEN** 系统返回对应的分割 mask（二值掩码，与输入帧同尺寸）

#### Scenario: 分割与姿态对齐
- **WHEN** 同一人同时被 YOLO-pose 和 YOLO-seg 检测
- **THEN** 两个模型的输出基于同一 bbox 对应到同一人

### Requirement: 模型权重加载
系统 SHALL 支持加载本地或自动下载 YOLO 模型权重。

#### Scenario: 本地权重
- **WHEN** 用户指定本地 .pt 文件路径
- **THEN** 系统从该路径加载模型

#### Scenario: 自动下载
- **WHEN** 用户未指定权重路径
- **THEN** 系统自动下载默认模型（yolov8m-pose.pt, yolov8m-seg.pt）
