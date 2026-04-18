"""可视化：骨架/mask 叠加、关键帧标记、视频编码。"""

import base64
import json
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


class Visualizer:
    """视频可视化生成器。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def render(
        self,
        video_path: Path,
        frame_results: list[FrameResult],
        gait_cycle: GaitCycle,
        output_dir: Path,
    ) -> Path:
        """渲染带标注的视频。"""
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        output_path = output_dir / "annotated_video.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"avc1")  # type: ignore[reportAttributeAccessIssue]
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        key_frame_indices = {kf.frame_index for kf in gait_cycle.key_frames}
        phase_map = {
            kf.frame_index: kf.phase_name for kf in gait_cycle.key_frames
        }

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx < len(frame_results):
                fr = frame_results[frame_idx]
                annotated = self._annotate_frame(frame, fr, frame_idx, phase_map)
            else:
                annotated = frame

            writer.write(annotated)
            frame_idx += 1

        cap.release()
        writer.release()

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
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

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
                mask_uint8 = (mask * 255).astype(np.uint8)
                _, encoded = cv2.imencode(".png", mask_uint8)
                frame_data["mask"] = base64.b64encode(encoded).decode("utf-8")
            else:
                frame_data["mask"] = None

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
    ) -> np.ndarray:
        """标注单帧。"""
        annotated = frame.copy()

        if fr.keypoints.size == 0:
            return annotated

        kpts = fr.keypoints[0]  # 只画最大的人
        h, w = annotated.shape[:2]

        # 绘制骨架
        for i, (start, end) in enumerate(COCO_SKELETON):
            if kpts[start, 2] > 0.1 and kpts[end, 2] > 0.1:
                pt1 = (int(kpts[start, 0]), int(kpts[start, 1]))
                pt2 = (int(kpts[end, 0]), int(kpts[end, 1]))
                color = COLORS[i % len(COLORS)]
                cv2.line(annotated, pt1, pt2, color, 2)

        # 绘制关键点
        for i in range(kpts.shape[0]):
            if kpts[i, 2] > 0.1:
                x, y = int(kpts[i, 0]), int(kpts[i, 1])
                conf = kpts[i, 2]
                color = (0, 255, 0) if conf >= 0.5 else (0, 255, 255)
                cv2.circle(annotated, (x, y), 4, color, -1)

        # 绘制分割 mask
        if fr.masks:
            mask = fr.masks[0]
            if mask.shape != (h, w):
                mask = cv2.resize(mask.astype(np.uint8), (w, h))
            overlay = annotated.copy()
            overlay[mask > 0.5] = overlay[mask > 0.5] * 0.5 + np.array([128, 0, 128]) * 0.5
            annotated = cv2.addWeighted(annotated, 0.7, overlay, 0.3, 0)

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
