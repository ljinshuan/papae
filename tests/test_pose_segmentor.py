"""姿态检测与分割测试。"""
from pathlib import Path

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from gait_assess.models import AppConfig
from gait_assess.pose_segmentor import PoseSegmentor


def _mock_tensor(data: np.ndarray) -> MagicMock:
    """创建模拟 tensor，支持 .cpu().numpy() 链式调用。"""
    tensor = MagicMock()
    tensor.cpu.return_value = tensor
    tensor.numpy.return_value = data
    return tensor


class TestPoseSegmentor:
    """YOLO 姿态检测与分割推理器测试。"""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(video=Path("dummy.mp4"), conf_threshold=0.3)

    def test_single_person(self, config: AppConfig) -> None:
        """单人物场景，验证返回正确的关键点和 bbox。"""
        with patch("gait_assess.pose_segmentor.YOLO") as mock_yolo_class:
            mock_pose = MagicMock()
            mock_seg = MagicMock()
            mock_yolo_class.side_effect = [mock_pose, mock_seg]

            segmentor = PoseSegmentor(config)

            # 准备 pose 结果：1 个人
            kpts = np.ones((1, 17, 3))
            kpts[0, 0] = [100, 200, 0.9]
            bbox = np.array([[50, 50, 150, 200]])

            pose_result = MagicMock()
            pose_result.keypoints = MagicMock()
            pose_result.keypoints.__len__ = lambda _: 1
            pose_result.keypoints.data = _mock_tensor(kpts)
            pose_result.boxes = MagicMock()
            pose_result.boxes.__len__ = lambda _: 1
            pose_result.boxes.xyxy = _mock_tensor(bbox)

            # 准备 seg 结果
            mask = np.ones((1, 64, 64))
            seg_bbox = np.array([[55, 55, 145, 195]])

            seg_result = MagicMock()
            seg_result.masks = MagicMock()
            seg_result.masks.__len__ = lambda _: 1
            seg_result.masks.data = _mock_tensor(mask)
            seg_result.boxes = MagicMock()
            seg_result.boxes.xyxy = _mock_tensor(seg_bbox)
            seg_result.orig_shape = (480, 640)
            seg_result.orig_shape = (480, 640)

            mock_pose.return_value = [pose_result]
            mock_seg.return_value = [seg_result]

            frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
            results = segmentor.infer(frames)

            assert len(results) == 1
            assert results[0].bboxes.shape == (1, 4)
            assert results[0].keypoints.shape == (1, 17, 3)
            assert len(results[0].masks) == 1
            assert results[0].masks[0].shape == (480, 640)
            np.testing.assert_array_equal(results[0].bboxes, bbox)
            np.testing.assert_array_equal(results[0].keypoints, kpts)

    def test_multi_person_filter(self, config: AppConfig) -> None:
        """多人物场景，验证只保留 bbox 面积最大的人。"""
        with patch("gait_assess.pose_segmentor.YOLO") as mock_yolo_class:
            mock_pose = MagicMock()
            mock_seg = MagicMock()
            mock_yolo_class.side_effect = [mock_pose, mock_seg]

            segmentor = PoseSegmentor(config)

            # 2 个人，第 0 个 bbox 面积小，第 1 个面积大
            kpts = np.ones((2, 17, 3))
            kpts[0, :, :2] = 10
            kpts[1, :, :2] = 20
            bbox = np.array([
                [0, 0, 10, 10],      # 面积 100
                [0, 0, 100, 100],    # 面积 10000
            ])

            pose_result = MagicMock()
            pose_result.keypoints = MagicMock()
            pose_result.keypoints.__len__ = lambda _: 2
            pose_result.keypoints.data = _mock_tensor(kpts)
            pose_result.boxes = MagicMock()
            pose_result.boxes.__len__ = lambda _: 2
            pose_result.boxes.xyxy = _mock_tensor(bbox)

            # seg 结果
            mask = np.ones((1, 64, 64))
            seg_bbox = np.array([[0, 0, 100, 100]])

            seg_result = MagicMock()
            seg_result.masks = MagicMock()
            seg_result.masks.__len__ = lambda _: 1
            seg_result.masks.data = _mock_tensor(mask)
            seg_result.boxes = MagicMock()
            seg_result.boxes.xyxy = _mock_tensor(seg_bbox)
            seg_result.orig_shape = (480, 640)

            mock_pose.return_value = [pose_result]
            mock_seg.return_value = [seg_result]

            frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
            results = segmentor.infer(frames)

            assert len(results) == 1
            assert results[0].bboxes.shape == (1, 4)
            np.testing.assert_array_equal(
                results[0].bboxes, np.array([[0, 0, 100, 100]])
            )
            assert results[0].keypoints.shape == (1, 17, 3)
            np.testing.assert_array_equal(results[0].keypoints, kpts[1:2])

    def test_no_person(self, config: AppConfig) -> None:
        """无人场景，验证返回空 keypoints 和空 bboxes。"""
        with patch("gait_assess.pose_segmentor.YOLO") as mock_yolo_class:
            mock_pose = MagicMock()
            mock_seg = MagicMock()
            mock_yolo_class.side_effect = [mock_pose, mock_seg]

            segmentor = PoseSegmentor(config)

            # pose 无检测结果
            pose_result = MagicMock()
            pose_result.keypoints = None

            # seg 无检测结果
            seg_result = MagicMock()
            seg_result.masks = None

            mock_pose.return_value = [pose_result]
            mock_seg.return_value = [seg_result]

            frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
            results = segmentor.infer(frames)

            assert len(results) == 1
            assert results[0].keypoints.size == 0
            assert results[0].bboxes.size == 0
            assert results[0].masks == []

    def test_confidence_filter(self, config: AppConfig) -> None:
        """低置信度关键点被过滤为 0。"""
        with patch("gait_assess.pose_segmentor.YOLO") as mock_yolo_class:
            mock_pose = MagicMock()
            mock_seg = MagicMock()
            mock_yolo_class.side_effect = [mock_pose, mock_seg]

            segmentor = PoseSegmentor(config)

            # 1 个人，部分关键点置信度低于阈值 0.3
            kpts = np.ones((1, 17, 3))
            kpts[0, :, :2] = 50
            kpts[0, 0, 2] = 0.9   # 高置信度
            kpts[0, 1, 2] = 0.1   # 低置信度（< 0.3）
            kpts[0, 2, 2] = 0.5   # 高置信度
            bbox = np.array([[0, 0, 100, 100]])

            pose_result = MagicMock()
            pose_result.keypoints = MagicMock()
            pose_result.keypoints.__len__ = lambda _: 1
            pose_result.keypoints.data = _mock_tensor(kpts.copy())
            pose_result.boxes = MagicMock()
            pose_result.boxes.__len__ = lambda _: 1
            pose_result.boxes.xyxy = _mock_tensor(bbox)

            # seg 结果
            mask = np.ones((1, 64, 64))
            seg_bbox = np.array([[0, 0, 100, 100]])

            seg_result = MagicMock()
            seg_result.masks = MagicMock()
            seg_result.masks.__len__ = lambda _: 1
            seg_result.masks.data = _mock_tensor(mask)
            seg_result.boxes = MagicMock()
            seg_result.boxes.xyxy = _mock_tensor(seg_bbox)
            seg_result.orig_shape = (480, 640)

            mock_pose.return_value = [pose_result]
            mock_seg.return_value = [seg_result]

            frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
            results = segmentor.infer(frames)

            assert len(results) == 1
            # 置信度 0.1 的关键点应被清零
            assert results[0].keypoints[0, 1, 0] == 0
            assert results[0].keypoints[0, 1, 1] == 0
            assert results[0].keypoints[0, 1, 2] == 0
            # 高置信度关键点保持不变
            assert results[0].keypoints[0, 0, 2] == pytest.approx(0.9)
            assert results[0].keypoints[0, 2, 2] == pytest.approx(0.5)
            # 其余关键点（默认 confidence=1.0）也不变
            assert results[0].keypoints[0, 3, 2] == pytest.approx(1.0)
