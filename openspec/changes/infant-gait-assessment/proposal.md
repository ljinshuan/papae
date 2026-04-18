## Why

婴幼儿早期走路姿态异常（如膝内翻、足内翻、踮脚走路等）若未及时发现和干预，可能影响长期骨骼发育。家长缺乏专业评估工具，医院评估门槛高。本项目旨在开发一个基于计算机视觉和大语言模型的命令行工具，让家长通过录制宝宝走路视频即可获得初步姿态评估，实现早发现、早关注。

## What Changes

- 新建 Python 命令行程序 `gait-assess`，采用流水线架构处理婴幼儿走路视频
- 集成 YOLO-pose + YOLO-seg 进行人体姿态检测和实例分割
- 使用 supervision 提取步态周期关键帧（脚跟着地、站立中期、脚尖离地、摆动中期）
- 调用全模态 LLM（Qwen-VL）对关键帧进行姿态异常评估
- 输出 Markdown 评估报告 + 带骨架/分割叠加的可视化视频
- 使用 uv 进行包管理，Python >= 3.13，basedpyright 进行静态类型检查

## Capabilities

### New Capabilities

- `video-preprocessing`: 视频读取、拆帧、模糊帧过滤、分辨率标准化
- `pose-segmentation`: 基于 YOLO-pose 和 YOLO-seg 的每帧姿态关键点与分割 mask 推理
- `gait-analysis`: 从连续姿态序列中提取步态周期，识别关键相位帧，计算步态基础指标
- `llm-assessment`: 将关键帧和姿态数据提交给全模态 LLM，获取结构化异常评估结果
- `visualization`: 在原始视频上叠加 COCO 骨架连线、分割 mask、关键帧标记，生成评估视频
- `report-generation`: 将 LLM 评估结果和步态指标整理为 Markdown 结构化报告
- `cli-orchestration`: 命令行参数解析、流水线协调执行、结果汇总输出

### Modified Capabilities

无（本项目为全新开发，无现有 spec 需要修改）。

## Impact

- **新依赖**: ultralytics, supervision, opencv-python, numpy, openai/dashscope SDK, click, pydantic-settings
- **包管理**: 使用 uv 替代 pip/poetry
- **开发工具**: basedpyright 静态类型检查
- **外部服务**: 依赖 Qwen 等多模态 LLM 云端 API
- **硬件**: 本地 YOLO 推理推荐 CUDA GPU
