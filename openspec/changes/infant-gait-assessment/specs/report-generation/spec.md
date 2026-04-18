## ADDED Requirements

### Requirement: Markdown 报告生成
系统 SHALL 生成结构化的 Markdown 格式评估报告。

#### Scenario: 标准报告
- **WHEN** 评估完成且结果有效
- **THEN** 系统生成包含以下部分的 Markdown 文件：
  - 评估摘要（风险等级、日期、视频信息）
  - 步态基础指标表格
  - LLM 发现列表
  - 建议措施列表
  - 关键帧缩略图（如可能）
  - 免责声明

### Requirement: 风险等级可视化
系统 SHALL 在报告中使用视觉元素突出显示风险等级。

#### Scenario: 高风险标记
- **WHEN** risk_level = "建议就医"
- **THEN** 报告中使用醒目的格式（如加粗、引用块）突出显示该等级

### Requirement: 关键帧嵌入
系统 SHALL 在报告中嵌入关键帧的图片。

#### Scenario: 嵌入关键帧
- **WHEN** 关键帧图片文件可用
- **THEN** 报告中以表格或画廊形式展示关键帧，每张标注相位名称

### Requirement: 报告输出路径
系统 SHALL 支持自定义报告输出路径。

#### Scenario: 默认路径
- **WHEN** 用户未指定输出路径
- **THEN** 报告保存到当前工作目录的 `report.md`

#### Scenario: 自定义路径
- **WHEN** 用户通过 CLI 指定输出目录
- **THEN** 报告保存到指定目录的 `report.md`

### Requirement: 免责声明
系统 SHALL 在报告中包含免责声明。

#### Scenario: 标准免责声明
- **WHEN** 报告生成
- **THEN** 报告末尾包含"本评估仅供参考，不构成医学诊断。如有疑虑请咨询专业医生。"
