"""可视化：骨架/mask 叠加、关键帧标记、视频编码。"""

import base64
import json
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import supervision as sv

from gait_assess.models import AppConfig, FrameResult, GaitCycle

# COCO 骨架连接
COCO_SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),  # 头部
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # 上肢
    (5, 11), (6, 12), (11, 12),  # 躯干
    (11, 13), (13, 15), (12, 14), (14, 16),  # 下肢
]

COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 165, 0),
]

_MASK_COLOR = sv.Color(r=128, g=0, b=128)
_MASK_ANNOTATOR = sv.MaskAnnotator(
    color=_MASK_COLOR, opacity=0.5, color_lookup=sv.ColorLookup.INDEX
)


class Visualizer:
    """视频可视化生成器。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._ankle_traces: dict[int, deque[tuple[int, int]]] = {
            15: deque(maxlen=15),
            16: deque(maxlen=15),
        }

    def render(
        self,
        video_path: Path,
        frame_results: list[FrameResult],
        gait_cycle: GaitCycle,
        output_dir: Path,
        preprocess_scale: float = 1.0,
    ) -> Path:
        """渲染带标注的视频。"""
        _video_info = sv.VideoInfo.from_video_path(str(video_path))

        output_path = output_dir / "annotated_video.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        phase_map = {
            kf.frame_index: kf.phase_name for kf in gait_cycle.key_frames
        }

        def callback(frame: np.ndarray, frame_idx: int) -> np.ndarray:
            if frame_idx < len(frame_results):
                return self._annotate_frame(
                    frame, frame_results[frame_idx], frame_idx,
                    phase_map, preprocess_scale,
                )
            return frame

        sv.process_video(str(video_path), str(output_path), callback)
        return output_path

    def generate_viewer_data(
        self,
        video_path: Path,
        frame_results: list[FrameResult],
        output_dir: Path,
        viewer_video_name: str = "viewer_video.mp4",
        preprocess_scale: float = 1.0,
    ) -> Path:
        """将 frame_results 序列化为 per-frame.json，供交互式查看器使用。"""
        info = sv.VideoInfo.from_video_path(str(video_path))
        fps = info.fps
        width = info.width
        height = info.height

        # 坐标放大倍数：将预处理后的坐标还原到原始视频尺寸
        coord_scale = 1.0 / preprocess_scale if preprocess_scale > 0 else 1.0

        frames: list[dict[str, object]] = []
        for idx, fr in enumerate(frame_results):
            frame_data: dict[str, object] = {"frame_index": idx}

            has_detection = fr.bboxes.size > 0 and fr.keypoints.size > 0

            if has_detection:
                bbox_raw = fr.bboxes[0]
                if coord_scale != 1.0:
                    bbox = (bbox_raw * coord_scale).tolist()
                    kpts = fr.keypoints[0].copy()
                    kpts[:, :2] *= coord_scale  # 只缩放 x, y，confidence 不变
                    keypoints = kpts.tolist()
                else:
                    bbox = bbox_raw.tolist()
                    keypoints = fr.keypoints[0].tolist()
                frame_data["bbox"] = bbox
                frame_data["bbox_label"] = f"({int(bbox[0])}, {int(bbox[1])})"
                frame_data["keypoints"] = keypoints
            else:
                frame_data["bbox"] = []
                frame_data["bbox_label"] = ""
                frame_data["keypoints"] = None

            if has_detection and fr.masks:
                mask = fr.masks[0]
                if coord_scale != 1.0:
                    mask_h, mask_w = mask.shape
                    target_w = int(mask_w * coord_scale)
                    target_h = int(mask_h * coord_scale)
                    mask = cv2.resize(
                        mask.astype(np.uint8),
                        (target_w, target_h),
                        interpolation=cv2.INTER_NEAREST,
                    )
                # 二值化 mask，创建 BGRA PNG（背景透明，人物区域 alpha=255）
                mask_binary = ((mask > 0.5) * 255).astype(np.uint8)
                bgra = np.zeros((mask_binary.shape[0], mask_binary.shape[1], 4), dtype=np.uint8)
                bgra[:, :, 3] = mask_binary  # alpha 通道
                _, encoded = cv2.imencode(".png", bgra)
                frame_data["mask"] = base64.b64encode(encoded).decode("utf-8")
                frame_data["mask_width"] = mask.shape[1]
                frame_data["mask_height"] = mask.shape[0]
            else:
                frame_data["mask"] = None
                frame_data["mask_width"] = 0
                frame_data["mask_height"] = 0

            frames.append(frame_data)

        output = {
            "fps": fps,
            "frame_count": len(frame_results),
            "width": width,
            "height": height,
            "video_filename": video_path.name,
            "viewer_video_filename": viewer_video_name,
            "frames": frames,
        }

        output_path = output_dir / "per-frame.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False)

        return output_path

    def _annotate_frame(
        self,
        frame: np.ndarray,
        fr: FrameResult,
        frame_idx: int,
        phase_map: dict[int, str],
        preprocess_scale: float = 1.0,
    ) -> np.ndarray:
        """标注单帧。"""
        annotated = frame.copy()

        if fr.keypoints.size == 0:
            return annotated

        # 将坐标缩放回原始视频尺寸
        coord_scale = 1.0 / preprocess_scale if preprocess_scale > 0 else 1.0

        kpts = fr.keypoints[0].copy()  # 只画最大的人
        if coord_scale != 1.0:
            kpts[:, :2] *= coord_scale  # 只缩放 x, y，confidence 不变

        h, w = annotated.shape[:2]

        # 绘制骨架连线
        for i, (start, end) in enumerate(COCO_SKELETON):
            if kpts[start, 2] > 0.1 and kpts[end, 2] > 0.1:
                pt1 = (int(kpts[start, 0]), int(kpts[start, 1]))
                pt2 = (int(kpts[end, 0]), int(kpts[end, 1]))
                color = COLORS[i % len(COLORS)]
                cv2.line(annotated, pt1, pt2, color, 2)

        # 绘制关键点（按置信度着色）
        for i in range(17):
            conf = kpts[i, 2]
            if conf > 0.1:
                x, y = int(kpts[i, 0]), int(kpts[i, 1])
                if conf >= 0.5:
                    color = (0, 255, 0)  # 绿色：高置信度
                else:
                    color = (0, 255, 255)  # 浅青色：低置信度
                cv2.circle(annotated, (x, y), 3, color, -1)

        # 绘制分割 mask（使用 supervision MaskAnnotator）
        if fr.masks:
            mask = fr.masks[0].copy()
            if coord_scale != 1.0:
                mask_h, mask_w = mask.shape
                target_w = int(mask_w * coord_scale)
                target_h = int(mask_h * coord_scale)
                mask = cv2.resize(
                    mask.astype(np.uint8),
                    (target_w, target_h),
                    interpolation=cv2.INTER_NEAREST,
                )
            if mask.shape != (h, w):
                mask = cv2.resize(
                    mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST
                )

            # 构建 sv.Detections（单个人）
            bbox = fr.bboxes[0].copy()
            if coord_scale != 1.0:
                bbox *= coord_scale
            bbox = bbox.reshape(1, 4)
            mask = mask.reshape(1, mask.shape[0], mask.shape[1])

            detections = sv.Detections(xyxy=bbox, mask=mask > 0.5)
            annotated = _MASK_ANNOTATOR.annotate(annotated, detections)

        # 运动轨迹：手动维护脚踝关键点轨迹（15=左踝, 16=右踝）
        for ankle_idx in [15, 16]:
            if kpts[ankle_idx, 2] > 0.1:
                x, y = int(kpts[ankle_idx, 0]), int(kpts[ankle_idx, 1])
                self._ankle_traces[ankle_idx].append((x, y))

        for ankle_idx, trace in self._ankle_traces.items():
            if len(trace) > 1:
                pts = np.array(list(trace), dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(annotated, [pts], False, (0, 255, 0), 2)

        # 关键帧标记
        if frame_idx in phase_map:
            phase = phase_map[frame_idx]
            cv2.putText(
                annotated,
                f"★ {phase}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )

        return annotated
