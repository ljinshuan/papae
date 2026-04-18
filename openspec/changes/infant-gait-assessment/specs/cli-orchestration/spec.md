## ADDED Requirements

### Requirement: 命令行参数解析
系统 SHALL 提供清晰的命令行接口，支持所有必要参数。

#### Scenario: 最小参数调用
- **WHEN** 用户执行 `python gait_assess.py --video ./baby.mp4`
- **THEN** 系统使用默认值处理视频，输出到当前目录

#### Scenario: 完整参数调用
- **WHEN** 用户指定所有可选参数
- **THEN** 系统使用用户指定的值：
  ```bash
  python gait_assess.py \
    --video ./baby.mp4 \
    --output ./results/ \
    --llm-api-key $KEY \
    --llm-model qwen-vl-max \
    --yolo-pose-model yolov8n-pose.pt \
    --yolo-seg-model yolov8n-seg.pt \
    --conf-threshold 0.3
  ```

### Requirement: 必需参数验证
系统 SHALL 验证必需参数是否存在且有效。

#### Scenario: 缺少必需参数
- **WHEN** 用户未提供 `--video` 参数
- **THEN** 系统显示帮助信息并退出，返回非零状态码

#### Scenario: 无效视频路径
- **WHEN** 提供的视频路径不存在或不可读
- **THEN** 系统报错并退出

### Requirement: 环境变量支持
系统 SHALL 支持通过环境变量配置敏感信息。

#### Scenario: API 密钥环境变量
- **WHEN** 环境变量 `QWEN_API_KEY` 已设置
- **THEN** 用户无需在命令行中传递 `--llm-api-key`

### Requirement: 执行摘要输出
系统 SHALL 在流水线完成后输出执行摘要。

#### Scenario: 成功执行
- **WHEN** 所有阶段成功完成
- **THEN** 系统打印：
  - 处理帧数
  - 检测到的步态周期数
  - 提取的关键帧数
  - 输出文件路径（报告 + 可视化视频）
  - 风险等级

#### Scenario: 部分失败
- **WHEN** 某阶段失败但中间结果已保留
- **THEN** 系统打印失败原因和已生成的中间文件路径

### Requirement: 进度显示
系统 SHALL 在处理过程中显示各阶段进度。

#### Scenario: 阶段进度
- **WHEN** 系统正在执行耗时操作（如 YOLO 推理）
- **THEN** 终端显示当前阶段名称和进度（如帧处理进度条）

### Requirement: 退出状态码
系统 SHALL 使用标准 Unix 退出状态码。

#### Scenario: 成功退出
- **WHEN** 所有阶段成功完成
- **THEN** 返回状态码 0

#### Scenario: 失败退出
- **WHEN** 任何阶段失败
- **THEN** 返回非零状态码（1 = 一般错误，2 = 参数错误，3 = 视频错误，4 = 模型错误，5 = LLM API 错误）
