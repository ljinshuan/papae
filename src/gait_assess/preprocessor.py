"""视频预处理：读取、拆帧、模糊过滤、分辨率标准化。"""

from pathlib import Path

import cv2
import numpy as np

from gait_assess.models import AppConfig


class VideoTooShortError(Exception):
    """视频时长不足。"""


class VideoQualityError(Exception):
    """视频质量过低。"""


class VideoNotFoundError(Exception):
    """视频文件不存在。"""


class VideoPreprocessor:
    """视频预处理器。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def process(
        self, video_path: Path
    ) -> tuple[list[np.ndarray], float, float, list[float]]:
        """处理视频，返回帧列表、fps、缩放比例和每帧质量分数。"""
        if not video_path.exists():
            raise VideoNotFoundError(f"视频文件不存在: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise VideoNotFoundError(f"无法打开视频: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0

        if duration < self.config.min_duration:
            cap.release()
            raise VideoTooShortError(
                f"视频过短 ({duration:.1f}s < {self.config.min_duration}s)，无法评估步态"
            )

        # 计算实际缩放比例（低分辨率不放大）
        scale = (
            self.config.target_height / original_height
            if original_height > self.config.target_height
            else 1.0
        )

        frames: list[np.ndarray] = []
        frame_qualities: list[float] = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 模糊检测 + 分辨率标准化（全部帧都标准化）
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            frame_qualities.append(float(variance))

            standardized = self._standardize_resolution(frame)
            frames.append(standardized)

        cap.release()

        if not frames:
            raise VideoQualityError("无法从视频中读取任何帧")

        # 检查有效帧比例（用于视频质量校验）
        valid_count = sum(1 for q in frame_qualities if q >= self.config.blur_threshold)
        valid_ratio = valid_count / len(frames) if frames else 0
        if valid_ratio < self.config.min_valid_frame_ratio:
            raise VideoQualityError(
                f"视频质量过低，有效帧比例 {valid_ratio:.1%} < "
                f"{self.config.min_valid_frame_ratio:.0%}"
            )

        return frames, fps, scale, frame_qualities

    def _standardize_resolution(self, frame: np.ndarray) -> np.ndarray:
        """将帧缩放到目标高度，保持宽高比，低分辨率不放大。"""
        h, w = frame.shape[:2]
        if h <= self.config.target_height:
            return frame
        scale = self.config.target_height / h
        new_w = int(w * scale)
        return cv2.resize(frame, (new_w, self.config.target_height))
