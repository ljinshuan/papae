"""姿势矫正评估测试。"""

import numpy as np
import pytest

from gait_assess.models import FrameResult
from gait_assess.pose_utils import (
    compute_joint_angles,
    compute_symmetry_metrics,
    detect_standing_frames,
)


class TestPosture:
    """姿势矫正评估测试类。"""

    def test_standing_frame_detection(self) -> None:
        """测试站立帧检测选择最稳定的帧。"""
        frame_results = []

        # 帧 0: 直立站立
        kpts0 = np.zeros((1, 17, 3))
        kpts0[0, 5] = [100.0, 100.0, 0.95]   # left_shoulder
        kpts0[0, 6] = [200.0, 100.0, 0.95]   # right_shoulder
        kpts0[0, 11] = [100.0, 200.0, 0.95]  # left_hip
        kpts0[0, 12] = [200.0, 200.0, 0.95]  # right_hip
        kpts0[0, 15] = [100.0, 400.0, 0.95]  # left_ankle
        kpts0[0, 16] = [200.0, 400.0, 0.95]  # right_ankle
        frame_results.append(
            FrameResult(keypoints=kpts0, masks=[], bboxes=np.zeros((1, 4)))
        )

        # 帧 1: 倾斜（高低肩）
        kpts1 = np.zeros((1, 17, 3))
        kpts1[0, 5] = [100.0, 100.0, 0.95]
        kpts1[0, 6] = [200.0, 140.0, 0.95]   # 右肩低 40px
        kpts1[0, 11] = [100.0, 200.0, 0.95]
        kpts1[0, 12] = [200.0, 200.0, 0.95]
        kpts1[0, 15] = [100.0, 400.0, 0.95]
        kpts1[0, 16] = [200.0, 400.0, 0.95]
        frame_results.append(
            FrameResult(keypoints=kpts1, masks=[], bboxes=np.zeros((1, 4)))
        )

        frames = detect_standing_frames(frame_results, n_best=2)
        assert 0 in frames  # 直立帧应该被选中最先
        assert len(frames) <= 2

    def test_symmetry_scoring(self) -> None:
        """测试对称性评分。"""
        # 完全对称
        kpts_sym = np.zeros((17, 3))
        kpts_sym[5] = [100.0, 100.0, 0.95]
        kpts_sym[6] = [200.0, 100.0, 0.95]
        kpts_sym[11] = [100.0, 200.0, 0.95]
        kpts_sym[12] = [200.0, 200.0, 0.95]

        sym = compute_symmetry_metrics(kpts_sym)
        # 对称姿态的肩高差和骨盆倾斜应接近 0
        assert sym["shoulder_height_diff"] == pytest.approx(0.0, abs=0.1)
        assert sym["pelvic_tilt"] == pytest.approx(0.0, abs=0.1)

    def test_spine_tilt_detection(self) -> None:
        """测试脊柱倾角检测。"""
        # 直立
        kpts_upright = np.zeros((17, 3))
        kpts_upright[5] = [100.0, 100.0, 0.95]
        kpts_upright[6] = [200.0, 100.0, 0.95]
        kpts_upright[11] = [100.0, 200.0, 0.95]
        kpts_upright[12] = [200.0, 200.0, 0.95]

        angles = compute_joint_angles(kpts_upright)
        assert angles["spine_tilt"] == pytest.approx(0.0, abs=5.0)

        # 倾斜（肩中点偏右）
        kpts_tilt = np.zeros((17, 3))
        kpts_tilt[5] = [120.0, 100.0, 0.95]
        kpts_tilt[6] = [220.0, 100.0, 0.95]
        kpts_tilt[11] = [100.0, 200.0, 0.95]
        kpts_tilt[12] = [200.0, 200.0, 0.95]

        angles = compute_joint_angles(kpts_tilt)
        # 脊柱应向右倾斜
        assert angles["spine_tilt"] > 5.0

    def test_risk_classification_thresholds(self) -> None:
        """测试风险分类阈值。"""
        # 根据 posture.jinja.md 中的阈值：
        # 脊柱倾角 > 5°：需关注
        # 肩高差 > 15px：需关注
        # 骨盆倾斜 > 10px：需关注

        # 正常姿态
        kpts_normal = np.zeros((17, 3))
        kpts_normal[5] = [100.0, 100.0, 0.95]
        kpts_normal[6] = [200.0, 100.0, 0.95]
        kpts_normal[11] = [100.0, 200.0, 0.95]
        kpts_normal[12] = [200.0, 200.0, 0.95]
        sym_normal = compute_symmetry_metrics(kpts_normal)
        assert sym_normal["shoulder_height_diff"] < 15
        assert sym_normal["pelvic_tilt"] < 10

        # 异常姿态（高低肩）
        kpts_abnormal = np.zeros((17, 3))
        kpts_abnormal[5] = [100.0, 100.0, 0.95]
        kpts_abnormal[6] = [200.0, 130.0, 0.95]  # 肩高差 30px
        kpts_abnormal[11] = [100.0, 200.0, 0.95]
        kpts_abnormal[12] = [200.0, 200.0, 0.95]
        sym_abnormal = compute_symmetry_metrics(kpts_abnormal)
        assert sym_abnormal["shoulder_height_diff"] > 15
