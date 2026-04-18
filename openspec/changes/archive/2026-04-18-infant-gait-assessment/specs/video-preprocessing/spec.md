## ADDED Requirements

### Requirement: 视频文件读取
系统 SHALL 支持从本地文件系统读取常见视频格式（MP4, AVI, MOV）。

#### Scenario: 读取 MP4 视频
- **WHEN** 用户提供一个有效的 MP4 文件路径
- **THEN** 系统成功读取视频并获取其帧序列和帧率

#### Scenario: 读取不存在的文件
- **WHEN** 用户提供一个不存在的文件路径
- **THEN** 系统抛出 FileNotFoundError 并提示文件不存在

### Requirement: 视频拆帧
系统 SHALL 将视频拆分为连续的帧序列，保留原始帧率信息。

#### Scenario: 标准视频拆帧
- **WHEN** 输入一个 30fps、时长 5 秒的视频
- **THEN** 系统输出约 150 帧的图像序列，并记录 fps 为 30.0

### Requirement: 模糊帧过滤
系统 SHALL 检测并过滤模糊帧，使用拉普拉斯方差作为清晰度指标。

#### Scenario: 过滤运动模糊帧
- **WHEN** 帧的拉普拉斯方差低于配置的阈值（默认 100.0）
- **THEN** 该帧被丢弃，不计入有效帧

#### Scenario: 保留清晰帧
- **WHEN** 帧的拉普拉斯方差高于或等于阈值
- **THEN** 该帧被保留进入后续处理

### Requirement: 分辨率标准化
系统 SHALL 将帧统一缩放到固定高度（默认 720 像素），保持原始宽高比。

#### Scenario: 高分辨率视频缩放
- **WHEN** 输入 4K 视频（3840x2160）
- **THEN** 输出帧被缩放到 1280x720，保持宽高比

#### Scenario: 低分辨率视频保持
- **WHEN** 输入 640x480 视频
- **THEN** 输出帧保持原始尺寸（不放大）

### Requirement: 有效帧比例检查
系统 SHALL 在预处理后检查有效帧比例，若过低则报错退出。

#### Scenario: 有效帧充足
- **WHEN** 有效帧比例大于等于 30%
- **THEN** 预处理正常完成，返回帧序列

#### Scenario: 有效帧不足
- **WHEN** 有效帧比例低于 30%
- **THEN** 系统报错并提示"视频质量过低，无法评估"

### Requirement: 视频时长检查
系统 SHALL 拒绝过短的视频输入。

#### Scenario: 视频过短
- **WHEN** 输入视频时长小于 3 秒
- **THEN** 系统报错并提示"视频过短，无法评估步态"
