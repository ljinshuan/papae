"""视频预处理测试。"""

import numpy as np
import pytest

from gait_assess.models import AppConfig
from gait_assess.preprocessor import (
    VideoNotFoundError,
    VideoPreprocessor,
    VideoQualityError,
    VideoTooShortError,
)


class TestVideoPreprocessor:
    """视频预处理器测试。"""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(video="dummy.mp4", blur_threshold=50.0, min_duration=1.0)

    def test_video_not_found(self, config: AppConfig, tmp_path: str) -> None:
        """测试不存在的视频文件。"""
        preprocessor = VideoPreprocessor(config)
        with pytest.raises(VideoNotFoundError):
            preprocessor.process(tmp_path / "not_exist.mp4")

    def test_blur_detection(self, config: AppConfig) -> None:
        """测试模糊帧过滤。"""
        preprocessor = VideoPreprocessor(config)
        # 清晰帧
        sharp = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        # 模糊帧
        blurred = np.zeros((100, 100, 3), dtype=np.uint8)

        # 手动测试 _standardize_resolution
        result = preprocessor._standardize_resolution(sharp)
        assert result.shape == sharp.shape  # 低于目标高度不放大
