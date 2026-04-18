# 婴幼儿姿态评估系统

基于 YOLOv8-pose + YOLOv8-seg 和全模态大语言模型（Qwen-VL）的婴幼儿姿态评估命令行工具。

支持三种评估模式：走路步态分析、运动发育筛查、姿势矫正评估。输入家长录制的宝宝视频，输出结构化 Markdown 评估报告和带骨架/分割叠加的可视化视频。

## 功能特性

- **三种评估模式**：
  - `gait` — 走路步态分析：基于步态周期检测，评估走路姿态异常
  - `developmental` — 运动发育筛查：按月龄匹配里程碑，筛查发育延迟风险
  - `posture` — 姿势矫正评估：分析静态站立姿态的脊柱/肩膀/骨盆对称性
- **视频预处理**：自动拆帧、模糊过滤、分辨率标准化
- **姿态检测**：YOLOv8-pose 提取 17 个 COCO 关键点
- **人体分割**：YOLOv8-seg 生成分割 mask
- **步态分析**：基于脚踝轨迹检测步态周期，提取 4 个关键相位帧
- **姿态计算**：膝关节角、踝关节角、脊柱倾角、骨盆倾斜、肩高差等
- **LLM 评估**：多模态大模型端到端判断，视频 + 结构化姿态数据双通道输入
- **可视化输出**：骨架连线、mask 叠加、关键帧标记
- **报告生成**：结构化 Markdown 报告，含风险徽章、发现卡片、建议卡片、嵌入关键帧图片

## 安装

需要 Python >= 3.13。

```bash
# 克隆仓库后安装依赖
uv sync --extra dev

# 或安装到当前环境
uv pip install -e ".[dev]"
```

## 使用方法

### 基本用法

```bash
# 走路步态评估（默认模式）
uv run gait-assess --video ./baby_walking.mp4 --output ./results/

# 运动发育筛查（需指定月龄）
uv run gait-assess --video ./baby_walking.mp4 --mode developmental --age-months 12 --output ./results/

# 姿势矫正评估
uv run gait-assess --video ./baby_standing.mp4 --mode posture --output ./results/
```

### 环境变量配置

LLM 相关配置通过环境变量或 `.env` 文件读取：

```bash
# 方法 1：直接设置环境变量
export QWEN_API_KEY=your-api-key
export GAIT_LLM_MODEL=qwen-vl-max
export GAIT_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

uv run gait-assess --video ./baby.mp4
```

```bash
# 方法 2：使用 .env 文件（推荐）
cat > .env << 'EOF'
QWEN_API_KEY=your-api-key
GAIT_LLM_MODEL=qwen-vl-max
GAIT_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EOF

uv run gait-assess --video ./baby.mp4
```

### 完整 CLI 参数

```bash
uv run gait-assess \
  --video ./baby_walking.mp4 \
  --output ./results/ \
  --mode gait \
  --age-months 12 \
  --conf-threshold 0.3 \
  --blur-threshold 100.0 \
  --target-height 720 \
  --min-duration 3.0
```

## Python API

除了命令行，你也可以在 Python 代码中直接调用评估流水线。

### 基本用法

```python
from pathlib import Path
from gait_assess import assess, AppConfig

config = AppConfig(
    video=Path("./baby.mp4"),
    output=Path("./results"),
    llm_api_key="your-api-key",
)

result = assess("./baby.mp4", config)

print(result["report_path"])       # Path('.../report.md')
print(result["video_path"])        # Path('.../annotated_video.mp4')
print(result["assessment"].risk_level)  # "正常"
```

### 模式专用函数

```python
from gait_assess import assess_gait, assess_developmental, assess_posture

# 走路步态评估
gait_result = assess_gait("./baby.mp4", config)

# 运动发育筛查（可省略 age_months，自动从姿态推断）
dev_result = assess_developmental("./baby.mp4", config)

# 姿势矫正评估
posture_result = assess_posture("./baby.mp4", config)
```

### 返回结果字段

`assess()` 及各模式函数返回包含以下字段的字典：

| 字段 | 类型 | 说明 |
|------|------|------|
| `report_path` | `Path` | Markdown 评估报告文件路径 |
| `video_path` | `Path` | 带标注的可视化视频路径 |
| `viewer_video_path` | `Path` | 交互式查看器用视频路径 |
| `viewer_data_path` | `Path` | 每帧 JSON 数据路径 |
| `viewer_html_path` | `Path \| None` | viewer.html 路径 |
| `assessment` | `AssessmentResult` | LLM 评估结果（风险等级、发现、建议） |
| `gait_cycle` | `GaitCycle` | 步态周期分析结果 |
| `config` | `AppConfig` | 运行时的配置对象 |
| `frames` | `list[np.ndarray]` | 预处理后的帧列表 |
| `fps` | `float` | 视频帧率 |
| `frame_results` | `list[FrameResult]` | 每帧的姿态检测/分割结果 |

### 跳过 LLM（离线评估）

```python
result = assess("./baby.mp4", config, skip_llm=True)
# assessment.risk_level == "未知"
```

### 错误处理

```python
from gait_assess.api import AssessmentError

try:
    result = assess("./baby.mp4", config)
except AssessmentError as e:
    print(f"阶段: {e.stage}")    # "preprocess" / "llm"
    print(f"原因: {e.original}") # 原始异常
```

### 输出文件

```
results/
├── report.md              # Markdown 评估报告（含风险徽章、发现/建议卡片）
├── annotated_video.mp4    # 带标注的可视化视频
├── viewer.html            # 交互式报告查看器
└── keyframes/
    ├── keyframe_00_脚跟着地.jpg
    ├── keyframe_01_站立中期.jpg
    ├── keyframe_02_脚尖离地.jpg
    └── keyframe_03_摆动中期.jpg
```

## 拍摄建议

为获得最佳评估效果，请按以下建议录制视频：

- **光线**：选择光线充足、均匀的环境，避免逆光或强阴影
- **距离**：手机/相机距离宝宝 2-3 米，确保全身入镜
- **视角**：镜头高度与宝宝腰部平齐，正侧面拍摄效果最佳
- **背景**：选择简洁背景，避免多人同时入镜
- **时长**：录制至少 5-10 秒连续走路视频，让宝宝走 3-5 步以上
- **服装**：避免过于宽松的衣物，建议短袖/短裤以便观察肢体

## 项目结构

```
src/gait_assess/
  __init__.py          # 包入口
  cli.py               # 命令行入口与流水线编排
  models.py            # Pydantic 数据模型
  preprocessor.py      # 视频拆帧、模糊过滤、标准化
  pose_segmentor.py    # YOLO-pose + YOLO-seg 推理
  gait_analyzer.py     # 步态周期检测、关键帧提取
  pose_utils.py        # 关节角度、对称性、时序轨迹计算
  llm_assessor.py      # 多模态 LLM 调用、Jinja2 模板渲染
  visualizer.py        # 骨架/mask 叠加、视频编码
  report_generator.py  # Markdown 报告生成
  prompts/             # Jinja2 提示词模板
    gait.jinja.md
    developmental.jinja.md
    posture.jinja.md
models/                # YOLO 模型权重文件（*.pt，被 .gitignore 忽略）
tests/
  fixtures/            # 测试视频
  test_*.py            # 各模块单元测试
```

## 开发

```bash
# 使用 Makefile
make help      # 查看所有命令
make install   # 安装依赖
make test      # 运行测试
make typecheck # 运行类型检查
make lint      # 运行代码格式检查
make e2e       # 端到端验证（跳过 LLM）
make e2e-full  # 端到端验证（含 LLM，需 API 密钥）
make viewer    # 运行 e2e 并自动打开 viewer.html
make clean     # 清理结果

# 或直接运行
uv run pytest
uv run basedpyright src/
```

## 免责声明

本工具仅供参考，不构成医学诊断。评估结果基于计算机视觉和大语言模型的分析，可能存在误差。如对宝宝走路姿态有疑虑，请务必咨询专业儿科医生或康复治疗师。

## 许可证

MIT
