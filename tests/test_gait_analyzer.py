"""步态分析测试。"""

import numpy as np
import pytest

from gait_assess.gait_analyzer import GaitAnalyzer
from gait_assess.models import AppConfig, FrameResult


class TestGaitAnalyzer:
    """步态分析器测试。"""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(video="dummy.mp4")

    @pytest.fixture
    def frame_results(self) -> list[FrameResult]:
        """生成模拟的帧结果。"""
        results: list[FrameResult] = []
        for _ in range(60):
            kpts = np.zeros((1, 17, 3))
            # 设置脚踝关键点
            kpts[0, 15] = [50, 80, 0.8]  # left ankle
            kpts[0, 16] = [60, 80, 0.8]  # right ankle
            results.append(
                FrameResult(keypoints=kpts, masks=[], bboxes=np.array([[40, 60, 70, 90]]))
            )
        return results

    def test_extract_ankle_trajectories(self, config: AppConfig, frame_results: list[FrameResult]) -> None:
        """测试脚踝轨迹提取。"""
        analyzer = GaitAnalyzer(config)
        left_y, right_y = analyzer._extract_ankle_trajectories(frame_results)
        assert len(left_y) == len(frame_results)
        assert len(right_y) == len(frame_results)
        assert not np.isnan(left_y).all()

    def test_interpolate(self, config: AppConfig) -> None:
        """测试缺失值插值。"""
        analyzer = GaitAnalyzer(config)
        arr = np.array([1.0, np.nan, np.nan, 4.0, 5.0])
        result = analyzer._interpolate(arr)
        assert not np.isnan(result[1])
        assert not np.isnan(result[2])

    def test_fallback_sampling(self, config: AppConfig, frame_results: list[FrameResult]) -> None:
        """测试退化采样。"""
        analyzer = GaitAnalyzer(config)
        key_frames = analyzer._fallback_sampling(frame_results)
        assert len(key_frames) <= 8
        assert len(key_frames) > 0
