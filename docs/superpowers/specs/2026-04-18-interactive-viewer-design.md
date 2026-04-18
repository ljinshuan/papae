# 交互式结果查看器 — 设计文档

## 背景

当前 `visualizer.py` 输出单一叠加视频（骨架 + mask + 关键帧标记），所有信息混在一帧中，不够直观。家长/医生需要更清晰的分层呈现方式，且希望能交互控制播放。

## 目标

将评估结果输出为交互式网页查看器，在 2×2 面板中分层展示原始视频、人物检测、分割高亮和姿态骨架，支持播放/暂停、逐帧查看、速度调节。

## 布局（已确认：2×2 网格）

```
┌─────────────────┬─────────────────┐
│  原始视频        │  BBOX + 坐标    │
│  (Raw)          │  (Detection)    │
├─────────────────┼─────────────────┤
│  Segment 高亮    │  姿态 1:1 裁剪   │
│  (Segmentation) │  (Pose Crop)    │
└─────────────────┴─────────────────┘
```

- **左上（Raw）**：原始视频帧，无任何叠加
- **右上（Detection）**：原始帧 + bbox 矩形框 + 左上角坐标标签（跟随人物移动）
- **左下（Segmentation）**：原始帧 + segment mask 紫色半透明高亮叠加
- **右下（Pose Crop）**：按 bbox 裁剪出的人物区域 + 骨架连线，与原始人物大小 1:1

## 技术方案（已确认：前端 Canvas 实时渲染 + Vue 3 CDN）

### 后端改动

在 `visualizer.py` 中新增 `generate_viewer_data()` 方法，将 `frame_results` 序列化为 `per-frame.json`。

现有的 `annotated_video.mp4` 继续保留，不删除。

### 前端架构

```
viewer.html（Vue 3 via CDN importmap）
├── 隐藏 <video> 元素（共享时间源）
├── 顶部控制栏组件（PlayerControls）
│   ├── 播放/暂停按钮
│   ├── 逐帧前进 / 后退
│   ├── 速度选择：0.5x / 1x / 2x
│   └── 进度条 + 当前帧号/总帧数
└── 2×2 VideoPanel 组件（×4）
    └── 每个面板包含 <canvas>，共用 video.currentTime
```

### 同步策略

`requestAnimationFrame` 轮询 `video.currentTime`，计算 `currentFrame = Math.floor(time * fps)`。仅当帧索引变化时触发重绘，避免无效渲染。

## 数据格式：`per-frame.json`

```json
{
  "fps": 30,
  "frame_count": 300,
  "width": 1280,
  "height": 720,
  "frames": [
    {
      "frame_index": 0,
      "bbox": [340, 120, 560, 680],
      "bbox_label": "(340, 120)",
      "keypoints": [
        [345, 125, 0.92],
        [350, 130, 0.85],
        ...
      ],
      "mask": "base64_encoded_png_or_null"
    }
  ]
}
```

- `bbox`: `[x1, y1, x2, y2]`，对应 pose 检测的最大人物
- `bbox_label`: 框旁边跟随显示的坐标文本
- `keypoints`: 17 个 COCO 关键点 `[x, y, confidence]`
- `mask`: segment mask 的 base64 PNG 编码；无检测结果时为 `null`

## Canvas 绘制细节

| 面板 | 绘制逻辑 |
|------|----------|
| **Raw** | `ctx.drawImage(video, 0, 0, w, h)` |
| **Detection** | Raw + `strokeRect(bbox)` + `fillText(label, x1, y1 - 5)` |
| **Segmentation** | Raw + `putImageData(mask)` 叠加紫色半透明层（沿用现有配色） |
| **Pose Crop** | `drawImage(video, bx, by, bw, bh, 0, 0, bw, bh)` + 骨架按 `(x - bx, y - by)` 偏移重绘 |

骨架连线使用 `COCO_SKELETON` 定义（与现有 `visualizer.py` 一致），线宽 2px，关节点半径 4px。

## 输出文件结构

```
results/
├── report.md              # 评估报告（已有）
├── annotated_video.mp4    # 现有叠加视频（保留）
├── viewer.html            # 新增：交互式查看器
├── per-frame.json         # 新增：每帧标注数据
└── baby.mp4               # 原始视频（供 viewer.html 引用）
```

`viewer.html` 通过相对路径引用 `per-frame.json` 和原始视频文件。

## 错误处理

| 场景 | 行为 |
|------|------|
| 某帧无检测结果（bbox 为空数组） | 面板 2/3/4 显示 "未检测到人物"，面板 1 正常播放 |
| mask 为 null | 面板 3 退化为与面板 2 相同（只显示 bbox） |
| 视频加载失败 | 显示错误提示，不影响 report.md 生成 |
| JSON 加载失败 | 显示错误提示，提供下载链接 |
| 浏览器不支持 Canvas | 降级为静态关键帧图片预览 |

## 测试策略

1. **后端单元测试**：验证 `generate_viewer_data()` 输出 JSON 结构与预期一致
2. **前端手动测试**：Chrome/Safari/Firefox 打开 `viewer.html`，验证播放/暂停/逐帧/变速功能
3. **端到端测试**：完整 pipeline 运行后，确认输出目录包含 `viewer.html` + `per-frame.json`，且 viewer 能正常播放

## 非目标（明确排除）

- 不替换现有 `annotated_video.mp4`，两者共存
- 不引入 Vite/Webpack 等构建工具，Vue 3 通过 CDN importmap 引入
- 不实现视频上传、分享、云端存储等功能
- 不实现姿态数据的实时 3D 可视化
