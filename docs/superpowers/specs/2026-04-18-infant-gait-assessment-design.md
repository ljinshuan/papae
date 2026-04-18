# 婴幼儿走路姿态评估系统 — 设计文档

**日期：** 2026-04-18  
**状态：** 待实现  
**作者：** AI-assisted design

---

## 1. 概述

### 1.1 目标
开发一个命令行程序，用于评估婴幼儿走路姿态，早期发现走路姿态问题，帮助家长及时关注。

### 1.2 核心功能
- 接受家长预先录制的婴幼儿走路视频
- 提取步态周期关键帧（脚跟着地、站立中期、脚尖离地、摆动中期）
- 使用全模态 LLM（如 Qwen-VL）分析姿态是否存在异常
- 输出结构化评估报告（Markdown）和带骨架/分割叠加的可视化视频

### 1.3 非功能需求
- **隐私：** 当前阶段使用云端 LLM API，后续可扩展本地部署
- **性能：** 本地 CV 推理优先使用 GPU，关键帧策略控制 LLM token 成本
- **易用性：** 命令行工具，参数简洁，输出路径明确

---

## 2. 架构

### 2.1 整体架构

系统采用**流水线（pipeline）架构**，数据单向流动：

```
输入视频
   │
   ▼
┌─────────────────┐
│  视频预处理      │  ──► 拆帧、过滤低质量帧、统一分辨率
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ YOLO-pose +     │  ──► 每帧提取人体关键点（17点 COCO 格式）
│ YOLO-seg        │  ──► 同时输出人体分割 mask
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ 步态周期检测     │  ──► supervision 计算脚踝/脚跟运动轨迹，
│ (关键帧提取)     │      识别完整步态周期，提取关键相位帧
└─────────────────┘
   │
   ▼
┌─────────────────┐
│  LLM 分析        │  ──► 将关键帧图片 + 姿态数据发送给全模态 LLM
│                 │      由模型判断是否存在姿态异常
└─────────────────┘
   │
   ▼
┌─────────────────┐
│  结果输出        │  ──► Markdown 报告 + 叠加骨架/mask 的可视化视频
└─────────────────┘
```

### 2.2 核心决策
- 本地运行 CV 模型（YOLO + supervision），LLM 调用云端 API
- 关键帧提取在本地完成，只把筛选后的关键帧（预计 8-20 帧/视频）传给 LLM
- 可视化视频在本地合成，使用 OpenCV 或 supervision 的标注工具

---

## 3. 组件设计

### 3.1 video_preprocessor — 视频预处理

**职责：** 将输入视频拆解为帧序列，进行质量过滤和标准化。

- **输入：** `Path`（视频文件路径）
- **输出：** `List[np.ndarray]`（过滤后的帧列表）+ `fps: float`
- **操作：**
  1. 用 OpenCV / supervision 逐帧读取
  2. 过滤模糊帧：拉普拉斯方差 < 阈值时丢弃
  3. 统一缩放到固定高度（720p），保持宽高比
  4. 输出帧列表和原始 fps

### 3.2 pose_segmentor — 姿态与分割推理

**职责：** 对每帧运行 YOLO-pose 和 YOLO-seg，输出关键点 + 分割 mask。

- **输入：** `List[np.ndarray]`（帧列表）
- **输出：** `List[FrameResult]`
  - `FrameResult.keypoints: np.ndarray` (N_persons, 17, 3) — x, y, confidence
  - `FrameResult.masks: List[np.ndarray]` — 每人的分割 mask
  - `FrameResult.bboxes: np.ndarray` — 检测框
- **依赖：** Ultralytics YOLO
- **注意：** 婴幼儿体型小，需调整置信度阈值；只保留最大 bbox 的人形检测

### 3.3 gait_analyzer — 步态周期与关键帧提取

**职责：** 从连续姿态序列中提取步态周期，筛选关键相位帧。

- **输入：** `List[FrameResult]` + `fps`
- **输出：** `GaitCycle`
  - `key_frames: List[KeyFrame]` — 关键帧（脚跟着地、站立中期、脚尖离地、摆动中期）
  - `cycle_periods: List[Tuple[int, int]]` — 每个完整周期的起止帧索引
  - `metrics: Dict` — 步频、步宽、步长估计等基础指标
- **核心算法：**
  1. 追踪脚踝/脚跟关键点 Y 坐标变化，检测波峰波谷
  2. 一个完整周期 = 两次同侧脚跟着地之间
  3. 从每个周期中提取 4 个关键相位帧
  4. 若检测到多个周期，每个周期各取一套；若不足一个周期，退化为均匀采样

### 3.4 llm_assessor — LLM 评估

**职责：** 将关键帧和姿态数据提交给全模态 LLM，获取异常判断。

- **输入：**
  - `key_frames: List[KeyFrame]`（含原始帧图像 + 关键点坐标）
  - `metrics: Dict`（步态基础指标）
  - `prompt_template: str`（系统提示词模板）
- **输出：** `AssessmentResult`
  - `risk_level: str` — "正常" / "轻微关注" / "建议就医"
  - `findings: List[str]` — 具体发现
  - `recommendations: List[str]` — 建议措施
  - `raw_response: str` — LLM 原始返回（用于调试）
- **API：** 调用 Qwen 多模态 API，关键帧作为图片列表上传，姿态数据以 JSON 附在 prompt 中

### 3.5 visualizer — 可视化合成

**职责：** 在原始视频上叠加骨架和分割 mask，生成评估视频。

- **输入：** 原始视频 + `List[FrameResult]` + `GaitCycle.key_frames` 标记
- **输出：** 输出视频文件（`output_annotated.mp4`）
- **叠加内容：**
  - COCO 骨架连线（不同颜色表示不同肢体）
  - 关键点圆点
  - 分割 mask（半透明覆盖）
  - 关键帧标记（在进度条上高亮）

### 3.6 report_generator — 报告生成

**职责：** 将 LLM 评估结果整理为结构化报告。

- **输入：** `AssessmentResult` + `GaitCycle.metrics` + 关键帧缩略图
- **输出：** Markdown 文件（含表格、关键帧图片嵌入、风险提示）

### 3.7 cli — 命令行入口

**职责：** 解析参数、协调 pipeline 执行、输出结果。

```bash
python gait_assess.py \
  --video ./baby_walking.mp4 \
  --output ./results/ \
  --llm-api-key $QWEN_API_KEY \
  --llm-model qwen-vl-max \
  --yolo-pose-model yolov8n-pose.pt \
  --yolo-seg-model yolov8n-seg.pt
```

---

## 4. 数据流与详细处理流程

### 4.1 主流程

```
main()
 │
 ├── 1. 解析 CLI 参数
 │
 ├── 2. video_preprocessor.process(video_path)
 │      └── 返回 frames[], fps
 │
 ├── 3. pose_segmentor.infer(frames[])
 │      └── 返回 frame_results[]
 │
 ├── 4. gait_analyzer.extract_cycles(frame_results[], fps)
 │      └── 返回 GaitCycle (key_frames[], metrics)
 │
 ├── 5. llm_assessor.assess(key_frames[], metrics)
 │      └── 返回 AssessmentResult
 │
 ├── 6. visualizer.render(video_path, frame_results[], key_frames[])
 │      └── 输出 annotated_video.mp4
 │
 ├── 7. report_generator.generate(AssessmentResult, metrics, key_frames[])
 │      └── 输出 report.md
 │
 └── 8. 汇总输出路径，打印摘要
```

### 4.2 步态周期检测详细逻辑

婴幼儿步态与成人不同（步宽较大、步长较短、缺乏 heel-strike），算法需调整：

| 检测目标 | 方法 | 关键帧 |
|---------|------|--------|
| 周期分割 | 追踪单侧脚踝 Y 坐标（垂直方向）的局部极值 | — |
| 脚跟着地 | 脚踝达到周期内最低 Y 坐标 | ✓ 关键帧 1 |
| 站立中期 | 脚踝处于周期中点，身体重心最高 | ✓ 关键帧 2 |
| 脚尖离地 | 脚踝开始上升，脚部离地瞬间 | ✓ 关键帧 3 |
| 摆动中期 | 脚踝达到周期内最高 Y 坐标 | ✓ 关键帧 4 |

**退化策略：** 若视频过短（< 1.5 个周期）或婴幼儿步态不规律导致周期检测失败，则均匀采样 8 帧替代。

### 4.3 LLM Prompt 设计

```markdown
你是一位儿童发育评估专家。请根据以下婴幼儿走路视频的关键帧和姿态数据，
评估其走路姿态是否存在异常，并给出建议。

【步态基础指标】
步频: {steps_per_minute} 步/分钟
步宽估计: {step_width_cm} cm
...

【评估要求】
1. 观察膝、踝、髋关节的对位关系
2. 注意是否存在膝内翻/外翻、足内翻/外翻、踮脚走路等
3. 结合婴幼儿月龄（如已知），考虑发育阶段正常范围
4. 风险分级：正常 / 轻微关注 / 建议就医

请用中文输出结构化的评估结果。
```

---

## 5. 错误处理与边界情况

| 场景 | 处理策略 |
|-----|---------|
| 视频中没有检测到人体 | 返回错误，提示"未检测到人物，请确保宝宝全身在画面中" |
| 检测到多个人 | 只保留最大 bbox 的那个人，在报告中备注 |
| 帧质量过低（大部分模糊） | 跳过模糊帧，若有效帧 < 30% 则报错 |
| 步态周期检测失败 | 退化到均匀采样 8 帧，在报告中标注 |
| LLM API 调用失败/超时 | 重试 2 次（指数退避），仍失败则报错并保留中间结果 |
| LLM 返回格式异常 | 尝试 regex 提取风险等级和发现，失败则标记"解析失败" |
| 婴幼儿背对镜头/不在画面 | YOLO-pose 置信度低时跳过该帧，关键帧不足则报错 |
| 视频过短（< 3 秒） | 报错提示"视频过短，无法评估步态" |

---

## 6. 技术栈

| 层级 | 技术/库 | 版本要求 |
|-----|--------|---------|
| 语言 | Python | >= 3.13 |
| 包管理 | uv | 依赖管理和虚拟环境 |
| 静态分析 | basedpyright | 类型检查 |
| CV 推理 | ultralytics (YOLOv8/v11) | >= 8.0 |
| CV 工具 | supervision | >= 0.22 |
| 视频处理 | opencv-python, numpy | 最新稳定版 |
| LLM 调用 | openai SDK / dashscope SDK | 最新稳定版 |
| 可视化 | supervision.annotators, opencv | — |
| CLI | click 或 argparse | — |
| 配置 | pydantic-settings | — |

**硬件需求：**
- 本地运行 YOLO 推荐 GPU（CUDA），CPU 亦可但较慢
- LLM 推理在云端，需网络连接

---

## 7. 测试策略

| 测试类型 | 内容 | 工具 |
|---------|------|------|
| 单元测试 | 各组件独立测试 | pytest |
| 集成测试 | 端到端 pipeline，短测试视频验证全流程 | pytest |
| Mock 测试 | LLM 调用使用 mock 响应 | unittest.mock |
| 视觉回归测试 | 关键帧提取结果与预期帧索引对比 | 数值断言 |
| 静态分析 | basedpyright 类型检查 | basedpyright |

**测试数据：** 准备 2-3 段公开儿童走路视频用于自动化测试。

---

## 8. 项目结构（预期）

```
gait-assess/
├── pyproject.toml           # uv 项目配置 + basedpyright 配置
├── uv.lock                  # 锁定依赖版本
├── README.md
├── src/
│   └── gait_assess/
│       ├── __init__.py
│       ├── cli.py            # 命令行入口
│       ├── preprocessor.py   # 视频预处理
│       ├── pose_segmentor.py # YOLO 推理
│       ├── gait_analyzer.py  # 步态周期检测
│       ├── llm_assessor.py   # LLM 评估
│       ├── visualizer.py     # 可视化合成
│       ├── report_generator.py
│       └── models.py         # 共享数据模型（Pydantic）
├── tests/
│   ├── test_preprocessor.py
│   ├── test_gait_analyzer.py
│   ├── test_llm_assessor.py
│   └── fixtures/             # 测试视频
└── docs/
    └── specs/                # 设计文档
```

---

## 9. 风险与后续考虑

| 风险 | 缓解措施 |
|-----|---------|
| 婴幼儿步态个体差异大，LLM 判断可能不准确 | 明确标注"仅供参考，不作为医学诊断"；后续可引入医学专家标注数据微调 |
| YOLO 对婴幼儿小体型检测效果可能不佳 | 尝试不同模型尺寸（n/s/m/l），必要时用婴幼儿专用数据集微调 |
| 关键帧提取算法对不规则步态失效 | 退化策略（均匀采样）；后续可探索基于学习的相位检测 |
| 视频拍摄角度/光线影响检测质量 | 在报告中提示用户拍摄建议（侧面、全身、光线充足） |
