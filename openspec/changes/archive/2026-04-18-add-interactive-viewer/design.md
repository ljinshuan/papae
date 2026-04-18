## Context

当前 `visualizer.py` 使用 OpenCV 将骨架、mask 和关键帧标记叠加到单一视频中。用户（家长和医生）需要更清晰的分层呈现方式，以便独立观察原始视频、人物检测、分割结果和姿态分析。

## Goals / Non-Goals

**Goals:**

- 输出交互式网页查看器，2×2 面板分层展示原始视频、BBOX+坐标、Segment 高亮、姿态 1:1 裁剪
- 支持播放/暂停、逐帧前进/后退、速度调节 (0.5x/1x/2x)
- 每帧数据通过 `per-frame.json` 提供给前端
- 保留现有 `annotated_video.mp4`，与新查看器共存

**Non-Goals:**

- 不替换现有 `annotated_video.mp4`
- 不引入 Vite/Webpack 等构建工具
- 不实现视频上传、分享、云端存储
- 不实现姿态数据的实时 3D 可视化

## Decisions

### 前端框架：Vue 3 via CDN importmap

- **选择**：Vue 3 通过 CDN 直接引入，不构建
- **理由**：响应式绑定播放状态和进度非常简洁；4 个面板拆成组件结构清晰；无需构建工具
- **替代方案**：纯原生 JS（代码冗长）、React CDN（模板语法对 Canvas 操作不如 Vue 直观）

### 渲染方式：前端 Canvas 实时绘制

- **选择**：后端只输出 JSON 数据 + 原始视频，前端 4 个 Canvas 共用隐藏 video 元素取帧绘制
- **理由**：数据量最小、4 面板播放同步精确（同一 video 源）、交互完全可控
- **替代方案**：后端预渲染 4 路视频（同步差、体积大）；后端预渲染 PNG 帧序列（文件数量巨大）

### 同步策略：requestAnimationFrame 轮询

- **选择**：通过 `requestAnimationFrame` 轮询 `video.currentTime`，计算当前帧索引，帧变化时触发重绘
- **理由**：比 `timeupdate` 事件更频繁、更精确；仅当帧索引变化时重绘，避免无效渲染
- **替代方案**：`timeupdate` 事件（触发频率低，约 4-250ms，不够精确）

### 数据格式：JSON + base64 PNG mask

- **选择**：`per-frame.json` 包含每帧 bbox、keypoints、base64 编码的 mask
- **理由**：JSON 易于解析；base64 PNG 在浏览器中可直接转为 ImageData 绘制到 Canvas
- **替代方案**：二进制 mask 数组（体积更小但需额外处理）；WebP base64（体积更小但兼容性差）

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| `per-frame.json` 体积过大（mask 数据多） | 仅婴幼儿视频通常较短（几秒到十几秒），gzip 后通常 <5MB |
| 前端浏览器兼容性 | 目标浏览器 Chrome/Safari/Firefox 最新 2 个版本，均支持 Canvas 2D 和 importmap |
| 逐帧数据生成增加运行时间 | 序列化在现有 pipeline 最后一步执行，不阻塞视频分析；mask base64 编码是主要开销 |
| Vue 3 CDN 加载依赖网络 | importmap 指向稳定 CDN（esm.sh / unpkg），国内可配置阿里云 CDN 镜像 |

## Open Questions

- 是否需要 gzip 压缩 `per-frame.json`？（当前不需要，数据量可控）
- 是否需要支持移动端浏览器？（当前以桌面端为主，但响应式布局预留扩展）
