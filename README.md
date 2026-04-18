# 婴幼儿走路姿态评估系统

基于 YOLOv8-pose + YOLOv8-seg 和全模态大语言模型（Qwen-VL）的婴幼儿走路姿态评估命令行工具。

输入家长录制的宝宝走路视频，输出 Markdown 评估报告和带骨架/分割叠加的可视化视频。

## 功能特性

- **视频预处理**：自动拆帧、模糊过滤、分辨率标准化
- **姿态检测**：YOLOv8-pose 提取 17 个 COCO 关键点
- **人体分割**：YOLOv8-seg 生成分割 mask
- **步态分析**：基于脚踝轨迹检测步态周期，提取 4 个关键相位帧
- **LLM 评估**：多模态大模型端到端判断步态异常
- **可视化输出**：骨架连线、mask 叠加、关键帧标记
- **报告生成**：结构化 Markdown 报告，含风险等级、发现与建议

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
uv run gait-assess --video ./baby_walking.mp4 --output ./results/
```

### 完整参数

```bash
uv run gait-assess \
  --video ./baby_walking.mp4 \
  --output ./results/ \
  --llm-api-key $QWEN_API_KEY \
  --llm-model qwen-vl-max \
  --conf-threshold 0.3 \
  --blur-threshold 100.0 \
  --target-height 720 \
  --min-duration 3.0
```

也可通过环境变量设置 API 密钥：

```bash
export QWEN_API_KEY=your-api-key
uv run gait-assess --video ./baby.mp4
```

### 输出文件

```
results/
├── report.md              # Markdown 评估报告
├── annotated_video.mp4    # 带标注的可视化视频
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
  llm_assessor.py      # 多模态 LLM 调用与解析
  visualizer.py        # 骨架/mask 叠加、视频编码
  report_generator.py  # Markdown 报告生成
models/                # YOLO 模型权重文件（*.pt，被 .gitignore 忽略）
tests/
  fixtures/            # 测试视频
  test_*.py            # 各模块单元测试
```

## 开发

```bash
# 运行测试
uv run pytest

# 运行类型检查
uv run basedpyright src/

# 运行单测
uv run pytest tests/test_gait_analyzer.py -v
```

## 免责声明

本工具仅供参考，不构成医学诊断。评估结果基于计算机视觉和大语言模型的分析，可能存在误差。如对宝宝走路姿态有疑虑，请务必咨询专业儿科医生或康复治疗师。

## 许可证

MIT
