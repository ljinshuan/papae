## 1. 项目初始化与基础设置

- [x] 1.1 初始化 uv 项目：创建 pyproject.toml，配置 Python >= 3.13、包元数据、基于 src 的布局
- [x] 1.2 配置 basedpyright：在 pyproject.toml 中添加 [tool.basedpyright] 段，设置严格模式
- [x] 1.3 安装核心依赖：uv add ultralytics supervision opencv-python numpy click pydantic pydantic-settings
- [x] 1.4 安装开发依赖：uv add --dev pytest pytest-asyncio basedpyright
- [x] 1.5 创建目录结构：src/gait_assess/、tests/、tests/fixtures/
- [x] 1.6 创建入口文件：src/gait_assess/__init__.py、src/gait_assess/__main__.py
- [x] 1.7 配置 pytest：在 pyproject.toml 中添加 [tool.pytest.ini_options]
- [x] 1.8 运行 basedpyright 确认空项目无类型错误

## 2. 共享数据模型（models.py）

- [x] 2.1 定义 FrameResult：keypoints (np.ndarray)、masks (list)、bboxes (np.ndarray)
- [x] 2.2 定义 KeyFrame：frame_index、phase_name、image (np.ndarray)、keypoints
- [x] 2.3 定义 GaitCycle：key_frames (list)、cycle_periods (list)、metrics (dict)
- [x] 2.4 定义 AssessmentResult：risk_level、findings、recommendations、raw_response
- [x] 2.5 定义 AppConfig：视频路径、输出目录、模型路径、API 密钥、阈值等 Pydantic Settings
- [x] 2.6 基于 pyright 运行类型检查，确保模型无类型错误

## 3. 视频预处理（preprocessor.py）

- [x] 3.1 实现视频读取：使用 OpenCV 读取视频，提取 fps、总帧数
- [x] 3.2 实现拆帧：逐帧读取为 np.ndarray
- [x] 3.3 实现模糊检测：计算拉普拉斯方差，低于阈值则丢弃
- [x] 3.4 实现分辨率标准化：固定高度 720px，保持宽高比，低分辨率不放大
- [x] 3.5 实现有效帧比例检查：低于 30% 则报错
- [x] 3.6 实现视频时长检查：低于 3 秒则报错
- [x] 3.7 编写 test_preprocessor.py：测试正常视频、模糊视频、过短视频、不存在的文件
- [x] 3.8 运行测试和 basedpyright，确保通过

## 4. 姿态检测与分割（pose_segmentor.py）

- [x] 4.1 实现 YOLO-pose 推理：加载模型，对每帧输出 17 个 COCO 关键点
- [x] 4.2 实现 YOLO-seg 推理：加载模型，对每帧输出分割 mask
- [x] 4.3 实现多人物过滤：只保留 bbox 面积最大的人
- [x] 4.4 实现置信度阈值控制：默认 0.3，支持 CLI 覆盖
- [x] 4.5 实现模型权重加载：支持本地路径和自动下载
- [x] 4.6 实现姿态与分割对齐：同一人的 pose 和 seg 结果关联
- [ ] 4.7 编写 test_pose_segmentor.py：测试单人物、多人物、无人、置信度过滤
- [ ] 4.8 运行测试和 basedpyright，确保通过

## 5. 步态分析（gait_analyzer.py）

- [x] 5.1 实现脚踝轨迹追踪：从关键点序列提取左右脚踝 Y 坐标
- [x] 5.2 实现缺失插值：线性插值填补空缺，连续缺失 >5 帧则标记无效
- [x] 5.3 实现步态周期检测：基于脚踝 Y 坐标极值识别周期起止
- [x] 5.4 实现关键相位帧提取：脚跟着地、站立中期、脚尖离地、摆动中期
- [x] 5.5 实现步频计算：周期数 / 时长 * 60
- [x] 5.6 实现步宽估计：双脚支撑期脚踝 X 坐标差均值
- [x] 5.7 实现退化采样：周期检测失败时均匀采样 8 帧
- [x] 5.8 实现关键帧质量检查：姿态缺失时从相邻帧选替代
- [x] 5.9 编写 test_gait_analyzer.py：测试正常周期、不规律步态、过短视频、缺失关键点
- [x] 5.10 运行测试和 basedpyright，确保通过

## 6. LLM 评估（llm_assessor.py）

- [x] 6.1 实现多模态输入构造：将关键帧转为 base64 图片列表 + 姿态指标文本
- [x] 6.2 实现 Prompt 模板：定义系统角色、评估要求、输出格式
- [x] 6.3 实现 LLM API 调用：集成 Qwen API（openai SDK 或 dashscope SDK）
- [x] 6.4 实现超时重试：30 秒超时，最多 2 次指数退避重试
- [x] 6.5 实现结构化解析：从响应提取 risk_level、findings、recommendations
- [x] 6.6 实现非标准响应处理：正则提取失败时标记"解析失败"
- [x] 6.7 实现原始响应保留：AssessmentResult.raw_response
- [x] 6.8 编写 test_llm_assessor.py：测试标准响应、超时、格式异常、mock API
- [x] 6.9 运行测试和 basedpyright，确保通过

## 7. 可视化（visualizer.py）

- [x] 7.1 实现 COCO 骨架绘制：按 COCO 连接规则画线，不同颜色区分肢体
- [x] 7.2 实现关键点绘制：画圆点，低置信度用浅色
- [x] 7.3 实现分割 mask 叠加：半透明彩色覆盖
- [x] 7.4 实现关键帧标记：视频底部显示相位名称标记线
- [x] 7.5 实现视频编码输出：H.264 MP4，保持原始 fps
- [x] 7.6 实现输出路径处理：支持自定义输出目录
- [ ] 7.7 编写 test_visualizer.py：测试标注正确性、输出文件存在
- [ ] 7.8 运行测试和 basedpyright，确保通过

## 8. 报告生成（report_generator.py）

- [x] 8.1 实现 Markdown 报告模板：摘要、指标表、发现、建议、关键帧、免责声明
- [x] 8.2 实现风险等级可视化：不同等级使用不同 Markdown 格式突出
- [x] 8.3 实现关键帧嵌入：将关键帧图片保存并嵌入报告（相对路径引用）
- [x] 8.4 实现输出路径处理：支持自定义输出目录
- [x] 8.5 实现免责声明：固定文本附在报告末尾
- [ ] 8.6 编写 test_report_generator.py：测试报告结构、关键帧嵌入、免责声明
- [ ] 8.7 运行测试和 basedpyright，确保通过

## 9. CLI 入口（cli.py）

- [x] 9.1 实现参数解析：click 或 argparse，支持所有必需和可选参数
- [x] 9.2 实现环境变量支持：QWEN_API_KEY 等
- [x] 9.3 实现参数验证：视频路径存在、输出目录可写
- [x] 9.4 实现流水线编排：按顺序调用各组件，传递数据
- [x] 9.5 实现进度显示：各阶段名称和进度输出到终端
- [x] 9.6 实现执行摘要：处理帧数、周期数、关键帧数、输出路径、风险等级
- [x] 9.7 实现错误处理：捕获各阶段异常，保留中间结果，打印友好错误
- [x] 9.8 实现退出状态码：0=成功，1=一般错误，2=参数错误，3=视频错误，4=模型错误，5=LLM错误
- [ ] 9.9 编写 test_cli.py：测试参数解析、成功流程、各种失败场景
- [ ] 9.10 运行测试和 basedpyright，确保通过

## 10. 端到端集成与验证

- [ ] 10.1 准备测试视频：2-3 段公开儿童走路视频放入 tests/fixtures/
- [ ] 10.2 运行完整流水线：从 CLI 到报告+可视化视频的全流程
- [ ] 10.3 验证报告内容：结构正确、关键帧嵌入、免责声明存在
- [ ] 10.4 验证可视化视频：骨架连线、mask 叠加、关键帧标记正确
- [ ] 10.5 验证错误场景：过短视频、模糊视频、无人视频、无效 API 密钥
- [ ] 10.6 运行全部测试套件：pytest，确保 100% 通过
- [ ] 10.7 运行静态分析：basedpyright，确保无类型错误
- [ ] 10.8 编写 README.md：安装说明、使用方法、拍摄建议、免责声明
