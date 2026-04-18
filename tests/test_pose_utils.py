"""姿态计算工具测试。"""

import numpy as np
import pytest

from gait_assess.models import FrameResult
from gait_assess.pose_utils import (
    angle_between,
    compute_joint_angles,
    compute_symmetry_metrics,
    compute_temporal_trajectories,
    detect_standing_frames,
    estimate_age_from_pose,
)


class TestPoseUtils:
    """姿态计算工具测试。"""

    def test_angle_between_perpendicular(self) -> None:
        """测试垂直向量夹角为 90°。"""
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        assert angle_between(v1, v2) == pytest.approx(90.0, abs=0.1)

    def test_angle_between_parallel(self) -> None:
        """测试平行向量夹角为 0°。"""
        v1 = np.array([1.0, 0.0])
        v2 = np.array([2.0, 0.0])
        assert angle_between(v1, v2) == pytest.approx(0.0, abs=0.1)

    def test_angle_between_empty(self) -> None:
        """测试空向量返回 NaN。"""
        assert np.isnan(angle_between(np.array([]), np.array([1.0, 0.0])))

    def test_compute_joint_angles_empty(self) -> None:
        """测试空输入返回全 NaN。"""
        kpts = np.array([])
        angles = compute_joint_angles(kpts)
        assert all(np.isnan(v) for v in angles.values())

    def test_compute_joint_angles_straight_knee(self) -> None:
        """测试直立姿态的关节角度。"""
        # 构造直立姿态：髋(100,200), 膝(100,300), 踝(100,400)
        kpts = np.zeros((17, 3))
        kpts[11] = [100.0, 200.0, 0.95]  # left_hip
        kpts[13] = [100.0, 300.0, 0.95]  # left_knee
        kpts[15] = [100.0, 400.0, 0.95]  # left_ankle
        kpts[12] = [120.0, 200.0, 0.95]  # right_hip
        kpts[14] = [120.0, 300.0, 0.95]  # right_knee
        kpts[16] = [120.0, 400.0, 0.95]  # right_ankle
        kpts[5] = [90.0, 100.0, 0.95]   # left_shoulder
        kpts[6] = [130.0, 100.0, 0.95]  # right_shoulder

        angles = compute_joint_angles(kpts)

        # 膝角度：髋-膝-踝几乎直线，约 180°
        assert angles["left_knee"] == pytest.approx(180.0, abs=5.0)
        assert angles["right_knee"] == pytest.approx(180.0, abs=5.0)

        # 踝角度：小腿垂直向下，与垂直线夹角约 0°
        assert angles["left_ankle"] == pytest.approx(0.0, abs=5.0)
        assert angles["right_ankle"] == pytest.approx(0.0, abs=5.0)

        # 脊柱倾角：肩膀水平，约 0°
        assert angles["spine_tilt"] == pytest.approx(0.0, abs=5.0)

    def test_compute_symmetry_metrics_symmetric(self) -> None:
        """测试对称姿态的对称性指标接近 0。"""
        kpts = np.zeros((17, 3))
        kpts[5] = [100.0, 100.0, 0.95]  # left_shoulder
        kpts[6] = [200.0, 100.0, 0.95]  # right_shoulder (同高度)
        kpts[11] = [100.0, 200.0, 0.95]  # left_hip
        kpts[12] = [200.0, 200.0, 0.95]  # right_hip (同高度)

        metrics = compute_symmetry_metrics(kpts)
        assert metrics["shoulder_height_diff"] == pytest.approx(0.0, abs=0.1)
        assert metrics["pelvic_tilt"] == pytest.approx(0.0, abs=0.1)

    def test_compute_symmetry_metrics_asymmetric(self) -> None:
        """测试不对称姿态的指标。"""
        kpts = np.zeros((17, 3))
        kpts[5] = [100.0, 100.0, 0.95]
        kpts[6] = [200.0, 130.0, 0.95]  # 右肩低 30px
        kpts[11] = [100.0, 200.0, 0.95]
        kpts[12] = [200.0, 210.0, 0.95]  # 右髋低 10px

        metrics = compute_symmetry_metrics(kpts)
        assert metrics["shoulder_height_diff"] == pytest.approx(30.0, abs=0.1)
        assert metrics["pelvic_tilt"] == pytest.approx(10.0, abs=0.1)
        assert metrics["shoulder_hip_ratio"] == pytest.approx(3.0, abs=0.1)

    def test_compute_temporal_trajectories(self) -> None:
        """测试时序轨迹计算。"""
        # 构造 3 帧
        frame_results = []
        for i in range(3):
            kpts = np.zeros((1, 17, 3))
            kpts[0, 15] = [100.0 + i * 10, 400.0, 0.95]  # left_ankle
            kpts[0, 16] = [150.0 + i * 5, 410.0, 0.95]  # right_ankle
            frame_results.append(
                FrameResult(keypoints=kpts, masks=[], bboxes=np.zeros((1, 4)))
            )

        traj = compute_temporal_trajectories(frame_results)
        assert len(traj["left_ankle_y"]) == 3
        assert len(traj["right_ankle_y"]) == 3
        assert len(traj["step_lengths"]) == 3
        assert traj["left_ankle_y"] == [400.0, 400.0, 400.0]
        assert traj["step_lengths"] == [50.0, 45.0, 40.0]

    def test_detect_standing_frames(self) -> None:
        """测试站立帧检测。"""
        # 构造 3 帧：第1帧直立，第2帧倾斜，第3帧缺失
        frame_results = []

        # 帧 0: 直立
        kpts0 = np.zeros((1, 17, 3))
        kpts0[0, 5] = [100.0, 100.0, 0.95]
        kpts0[0, 6] = [200.0, 100.0, 0.95]
        kpts0[0, 11] = [100.0, 200.0, 0.95]
        kpts0[0, 12] = [200.0, 200.0, 0.95]
        kpts0[0, 15] = [100.0, 400.0, 0.95]
        kpts0[0, 16] = [200.0, 400.0, 0.95]
        frame_results.append(
            FrameResult(keypoints=kpts0, masks=[], bboxes=np.zeros((1, 4)))
        )

        # 帧 1: 倾斜（脊柱不直，脚踝不等高）
        kpts1 = np.zeros((1, 17, 3))
        kpts1[0, 5] = [100.0, 100.0, 0.95]
        kpts1[0, 6] = [200.0, 120.0, 0.95]
        kpts1[0, 11] = [100.0, 200.0, 0.95]
        kpts1[0, 12] = [200.0, 200.0, 0.95]
        kpts1[0, 15] = [100.0, 400.0, 0.95]
        kpts1[0, 16] = [200.0, 380.0, 0.95]  # 脚踝不等高
        frame_results.append(
            FrameResult(keypoints=kpts1, masks=[], bboxes=np.zeros((1, 4)))
        )

        # 帧 2: 空帧
        frame_results.append(
            FrameResult(
                keypoints=np.zeros((0, 17, 3)), masks=[], bboxes=np.zeros((0, 4))
            )
        )

        standing = detect_standing_frames(frame_results, n_best=2)
        # 最稳定的应该是帧 0
        assert standing[0] == 0
        assert len(standing) <= 2

    def test_estimate_age_from_pose_walking(self) -> None:
        """测试步态视频的月龄推断。"""
        frame_results = []
        for i in range(10):
            kpts = np.zeros((1, 17, 3))
            # 模拟走路时脚踝上下波动
            ankle_y = 400.0 + 30.0 * np.sin(i * 0.5)
            kpts[0, 15] = [100.0, ankle_y, 0.95]
            kpts[0, 16] = [150.0, ankle_y + 5, 0.95]
            kpts[0, 5] = [100.0, 100.0, 0.95]
            frame_results.append(
                FrameResult(keypoints=kpts, masks=[], bboxes=np.zeros((1, 4)))
            )

        age = estimate_age_from_pose(frame_results)
        assert age is not None
        assert age >= 12  # 有步态，应该是学步期以上

    def test_estimate_age_from_pose_empty(self) -> None:
        """测试空输入返回 None。"""
        assert estimate_age_from_pose([]) is None

    def test_compute_symmetry_score_perfect(self) -> None:
        """测试完全对称评分 100。"""
        kpts = np.zeros((17, 3))
        kpts[5] = [100.0, 100.0, 0.95]  # left_shoulder
        kpts[6] = [200.0, 100.0, 0.95]  # right_shoulder
        kpts[11] = [100.0, 200.0, 0.95]  # left_hip
        kpts[12] = [200.0, 200.0, 0.95]  # right_hip
        kpts[13] = [100.0, 300.0, 0.95]  # left_knee
        kpts[14] = [200.0, 300.0, 0.95]  # right_knee
        kpts[15] = [100.0, 400.0, 0.95]  # left_ankle
        kpts[16] = [200.0, 400.0, 0.95]  # right_ankle

        from gait_assess.pose_utils import compute_symmetry_score
        score = compute_symmetry_score(kpts)
        assert score == pytest.approx(100.0, abs=5.0)

    def test_compute_symmetry_score_asymmetric(self) -> None:
        """测试不对称姿态评分降低。"""
        kpts = np.zeros((17, 3))
        kpts[5] = [100.0, 100.0, 0.95]
        kpts[6] = [200.0, 130.0, 0.95]  # 肩高差 30px
        kpts[11] = [100.0, 200.0, 0.95]
        kpts[12] = [200.0, 210.0, 0.95]  # 骨盆倾斜 10px
        kpts[13] = [100.0, 300.0, 0.95]
        kpts[14] = [200.0, 320.0, 0.95]  # 膝角度差异
        kpts[15] = [100.0, 400.0, 0.95]
        kpts[16] = [200.0, 400.0, 0.95]

        from gait_assess.pose_utils import compute_symmetry_score
        score = compute_symmetry_score(kpts)
        assert score < 100.0
        assert score >= 0.0

    def test_compute_kyphosis_angle(self) -> None:
        """测试驼背角度计算。"""
        # 直立
        kpts_upright = np.zeros((17, 3))
        kpts_upright[5] = [100.0, 100.0, 0.95]
        kpts_upright[6] = [200.0, 100.0, 0.95]
        kpts_upright[0] = [150.0, 50.0, 0.95]  # nose

        from gait_assess.pose_utils import compute_kyphosis_angle
        angle = compute_kyphosis_angle(kpts_upright)
        assert angle == pytest.approx(0.0, abs=5.0)

        # 驼背（鼻子更靠前，肩膀靠后）
        kpts_hunch = np.zeros((17, 3))
        kpts_hunch[5] = [100.0, 100.0, 0.95]
        kpts_hunch[6] = [200.0, 100.0, 0.95]
        kpts_hunch[0] = [250.0, 120.0, 0.95]  # nose 明显靠前

        angle = compute_kyphosis_angle(kpts_hunch)
        assert angle > 5.0
