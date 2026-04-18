## ADDED Requirements

### Requirement: 多模态输入构造
系统 SHALL 将关键帧图像和姿态数据构造为 LLM 可接受的输入格式。

#### Scenario: 构造图文输入
- **WHEN** 关键帧和姿态指标已准备好
- **THEN** 系统生成包含关键帧图片列表 + 文本 prompt 的多模态消息

#### Scenario: 姿态数据序列化
- **WHEN** 步态指标需要传递给 LLM
- **THEN** 指标被序列化为结构化 JSON 或 Markdown 表格附在 prompt 中

### Requirement: LLM API 调用
系统 SHALL 调用全模态 LLM API（如 Qwen-VL）进行评估。

#### Scenario: 成功调用
- **WHEN** API 密钥有效且网络正常
- **THEN** 系统在 60 秒内收到 LLM 响应

#### Scenario: API 超时
- **WHEN** 首次调用在 30 秒内未返回
- **THEN** 系统进行最多 2 次重试，使用指数退避（1s, 2s）

#### Scenario: API 调用彻底失败
- **WHEN** 3 次调用均失败
- **THEN** 系统报错退出，保留已生成的中间结果（预处理帧、姿态数据）

### Requirement: 结构化输出解析
系统 SHALL 从 LLM 响应中提取结构化的评估结果。

#### Scenario: 标准格式响应
- **WHEN** LLM 返回符合预期格式的响应
- **THEN** 系统解析出 risk_level、findings、recommendations

#### Scenario: 非标准格式响应
- **WHEN** LLM 返回格式异常
- **THEN** 系统尝试使用正则表达式提取关键信息，若失败则标记为"解析失败"并附原始响应

### Requirement: 风险分级
系统 SHALL 将评估结果分为三个风险等级。

#### Scenario: 正常等级
- **WHEN** LLM 判断姿态无异常
- **THEN** risk_level = "正常"

#### Scenario: 轻微关注等级
- **WHEN** LLM 检测到轻微姿态偏差但无需就医
- **THEN** risk_level = "轻微关注"

#### Scenario: 建议就医等级
- **WHEN** LLM 检测到明显异常姿态
- **THEN** risk_level = "建议就医"

### Requirement: 评估结果持久化
系统 SHALL 保留 LLM 的原始响应以供调试和复核。

#### Scenario: 保存原始响应
- **WHEN** 评估完成
- **THEN** 原始响应字符串被保存在 AssessmentResult.raw_response 中
