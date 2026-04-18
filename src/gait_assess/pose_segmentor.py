"""姿态检测与分割：YOLO-pose + YOLO-seg 推理。"""

from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO  # type: ignore[reportPrivateImportUsage]

from gait_assess.models import AppConfig, FrameResult


class PoseSegmentor:
    """YOLO 姿态检测与分割推理器。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.pose_model = self._load_model(config.yolo_pose_model)
        self.seg_model = self._load_model(config.yolo_seg_model)

    def _load_model(self, model_path: str) -> YOLO:
        """加载 YOLO 模型，支持本地路径或自动下载。"""
        path = Path(model_path)
        if path.exists():
            return YOLO(str(path))
        return YOLO(model_path)

    def infer(self, frames: list[np.ndarray]) -> list[FrameResult]:
        """对帧列表进行推理，返回每帧的结果。"""
        results: list[FrameResult] = []

        # YOLO-pose 推理
        pose_results = self.pose_model(frames, verbose=False)

        # YOLO-seg 推理
        seg_results = self.seg_model(frames, verbose=False)

        for pose_r, seg_r in zip(pose_results, seg_results, strict=True):
            keypoints, bboxes = self._extract_pose(pose_r)
            masks = self._extract_masks(seg_r, bboxes)
            results.append(
                FrameResult(keypoints=keypoints, masks=masks, bboxes=bboxes)
            )

        return results

    def _extract_pose(
        self, result
    ) -> tuple[np.ndarray, np.ndarray]:
        """从 YOLO-pose 结果提取关键点和 bbox，只保留最大的人。"""
        if result.keypoints is None or len(result.keypoints) == 0:
            return np.array([]), np.array([])

        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return np.array([]), np.array([])

        # 只保留置信度高于阈值的关键点
        kpts = result.keypoints.data.cpu().numpy()  # (N, 17, 3)
        conf_mask = kpts[..., 2] >= self.config.conf_threshold
        kpts[~conf_mask] = 0

        # 只保留 bbox 面积最大的人
        if len(boxes) > 1:
            xyxy = boxes.xyxy.cpu().numpy()  # (N, 4)
            areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
            largest_idx = int(np.argmax(areas))
            kpts = kpts[largest_idx : largest_idx + 1]
            xyxy = xyxy[largest_idx : largest_idx + 1]
        else:
            xyxy = boxes.xyxy.cpu().numpy()

        return kpts, xyxy

    def _extract_masks(
        self, result, pose_bboxes: np.ndarray
    ) -> list[np.ndarray]:
        """从 YOLO-seg 结果提取 mask，只保留与 pose 对应的人。"""
        if result.masks is None or len(result.masks) == 0:
            return []

        seg_boxes = result.boxes.xyxy.cpu().numpy()
        masks = result.masks.data.cpu().numpy()

        if len(pose_bboxes) == 0:
            return []

        # 找到与 pose bbox IOU 最大的 seg mask
        pose_box = pose_bboxes[0]
        best_iou = 0.0
        best_idx = 0

        for i, seg_box in enumerate(seg_boxes):
            iou = self._compute_iou(pose_box, seg_box)
            if iou > best_iou:
                best_iou = iou
                best_idx = i

        # 将 mask 缩放到原始输入帧尺寸（与 pose 输入一致）
        mask = masks[best_idx]
        orig_h, orig_w = result.orig_shape
        if mask.shape != (orig_h, orig_w):
            mask = cv2.resize(
                mask.astype(np.float32),
                (orig_w, orig_h),
                interpolation=cv2.INTER_LINEAR,
            )
        return [mask]

    @staticmethod
    def _compute_iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
        """计算两个 bbox 的 IOU。"""
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])

        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0
