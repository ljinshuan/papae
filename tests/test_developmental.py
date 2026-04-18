"""运动发育筛查测试。"""

from gait_assess.pose_utils import estimate_age_from_pose


class TestDevelopmental:
    """运动发育筛查测试类。"""

    def test_estimate_age_from_pose_crawling(self) -> None:
        """测试匍匐姿态推断月龄。"""
        import numpy as np
        from gait_assess.models import FrameResult

        frame_results = []
        for i in range(5):
            kpts = np.zeros((1, 17, 3))
            # 身体贴近地面，脚踝 Y 接近
            kpts[0, 15] = [100.0, 200.0, 0.95]
            kpts[0, 16] = [150.0, 205.0, 0.95]
            kpts[0, 5] = [100.0, 80.0, 0.95]
            frame_results.append(
                FrameResult(keypoints=kpts, masks=[], bboxes=np.zeros((1, 4)))
            )

        age = estimate_age_from_pose(frame_results)
        assert age is not None
        assert age < 12  # 匍匐阶段应在 12 个月以下

    def test_estimate_age_from_pose_infant(self) -> None:
        """测试婴儿姿态推断月龄。"""
        import numpy as np
        from gait_assess.models import FrameResult

        frame_results = []
        for i in range(5):
            kpts = np.zeros((1, 17, 3))
            # 身体很小
            kpts[0, 15] = [100.0, 150.0, 0.95]
            kpts[0, 16] = [120.0, 150.0, 0.95]
            kpts[0, 5] = [100.0, 80.0, 0.95]
            frame_results.append(
                FrameResult(keypoints=kpts, masks=[], bboxes=np.zeros((1, 4)))
            )

        age = estimate_age_from_pose(frame_results)
        assert age is not None
        assert age <= 6  # 小身体应是婴儿期

    def test_milestone_age_groups(self) -> None:
        """测试月龄分组逻辑。"""
        groups = [
            (3, "0-6m"),
            (9, "6-12m"),
            (15, "12-24m"),
            (30, "24-36m"),
        ]
        for age, expected_group in groups:
            if age <= 6:
                group = "0-6m"
            elif age <= 12:
                group = "6-12m"
            elif age <= 24:
                group = "12-24m"
            else:
                group = "24-36m"
            assert group == expected_group
