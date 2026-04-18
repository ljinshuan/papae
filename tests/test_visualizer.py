"""Visualizer 测试。"""

from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from gait_assess.models import AppConfig, FrameResult, GaitCycle, KeyFrame
from gait_assess.visualizer import Visualizer, COCO_SKELETON, COLORS


class TestVisualizer:
    """视频可视化测试。"""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(video=Path("dummy.mp4"))

    @pytest.fixture
    def frame_results(self) -> list[FrameResult]:
        """生成合成的帧结果。"""
        kpts = np.zeros((1, 17, 3))
        for i in range(17):
            kpts[0, i] = [50 + i * 10, 100 + (i % 3) * 20, 0.8]
        return [
            FrameResult(keypoints=kpts, masks=[], bboxes=np.array([[40, 80, 220, 160]]))
        ]

    @pytest.fixture
    def gait_cycle(self) -> GaitCycle:
        """生成合成的步态周期。"""
        return GaitCycle(
            key_frames=[
                KeyFrame(
                    frame_index=0,
                    phase_name="脚跟着地",
                    image=np.zeros((240, 320, 3), dtype=np.uint8),
                )
            ],
            cycle_periods=[(0, 1)],
            metrics={},
        )

    def _create_dummy_video(self, path: Path, frames: int = 5) -> None:
        """创建合成视频文件。"""
        width, height = 320, 240
        fourcc = cv2.VideoWriter_fourcc(*"avc1")  # type: ignore[reportAttributeAccessIssue]
        writer = cv2.VideoWriter(str(path), fourcc, 30.0, (width, height))
        for _ in range(frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            writer.write(frame)
        writer.release()

    def test_output_file_exists(
        self,
        config: AppConfig,
        frame_results: list[FrameResult],
        gait_cycle: GaitCycle,
        tmp_path: Path,
    ) -> None:
        """验证输出视频文件被创建。"""
        video_path = tmp_path / "input.mp4"
        self._create_dummy_video(video_path)
        output_dir = tmp_path / "output"

        visualizer = Visualizer(config)
        result_path = visualizer.render(video_path, frame_results, gait_cycle, output_dir)

        assert result_path.exists()
        assert result_path.name == "annotated_video.mp4"

    def test_skeleton_drawing(self, config: AppConfig) -> None:
        """验证骨架连线逻辑和颜色。"""
        visualizer = Visualizer(config)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)

        kpts = np.zeros((1, 17, 3))
        for i in range(17):
            kpts[0, i] = [50 + i * 10, 100, 0.8]

        fr = FrameResult(keypoints=kpts, masks=[], bboxes=np.array([[40, 80, 220, 100]]))
        phase_map: dict[int, str] = {}

        with patch("gait_assess.visualizer.cv2.line") as mock_line:
            visualizer._annotate_frame(frame, fr, 0, phase_map)

            assert mock_line.call_count == len(COCO_SKELETON)
            for i, call in enumerate(mock_line.call_args_list):
                args = call[0]
                assert args[3] == COLORS[i % len(COLORS)]
                assert args[4] == 2

    def test_keypoint_confidence(self, config: AppConfig) -> None:
        """验证低置信度关键点用浅色，高置信度用绿色。"""
        visualizer = Visualizer(config)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)

        kpts = np.zeros((1, 17, 3))
        # 高置信度
        kpts[0, 0] = [50, 100, 0.6]
        # 低置信度（但 > 0.1）
        kpts[0, 1] = [70, 100, 0.3]
        # 极低置信度（不绘制）
        kpts[0, 2] = [90, 100, 0.05]

        fr = FrameResult(keypoints=kpts, masks=[], bboxes=np.array([[40, 80, 100, 120]]))
        phase_map: dict[int, str] = {}

        with patch("gait_assess.visualizer.cv2.circle") as mock_circle:
            visualizer._annotate_frame(frame, fr, 0, phase_map)

            # 只应绘制 2 个关键点（置信度 > 0.1 的）
            assert mock_circle.call_count == 2

            # 高置信度 = 绿色
            high_conf_call = mock_circle.call_args_list[0]
            assert high_conf_call[0][3] == (0, 255, 0)

            # 低置信度 = 浅青色
            low_conf_call = mock_circle.call_args_list[1]
            assert low_conf_call[0][3] == (0, 255, 255)

    def test_keyframe_marking(self, config: AppConfig) -> None:
        """验证关键帧标记文本正确显示。"""
        visualizer = Visualizer(config)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)

        kpts = np.zeros((1, 17, 3))
        kpts[0, 0] = [50, 100, 0.9]
        fr = FrameResult(keypoints=kpts, masks=[], bboxes=np.array([[40, 80, 60, 120]]))

        phase_map = {5: "站立中期"}

        with patch("gait_assess.visualizer.cv2.putText") as mock_putText:
            # 非关键帧不应调用 putText
            visualizer._annotate_frame(frame, fr, 0, phase_map)
            assert mock_putText.call_count == 0

            # 关键帧应调用 putText
            visualizer._annotate_frame(frame, fr, 5, phase_map)
            assert mock_putText.call_count == 1
            args = mock_putText.call_args_list[0][0]
            assert args[1] == "★ 站立中期"
            assert args[3] == cv2.FONT_HERSHEY_SIMPLEX


class TestGenerateViewerData:
    """generate_viewer_data() 测试。"""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(video=Path("dummy.mp4"))

    def _create_dummy_video(self, path: Path, frames: int = 5) -> None:
        """创建合成视频文件。"""
        width, height = 320, 240
        fourcc = cv2.VideoWriter_fourcc(*"avc1")  # type: ignore[reportAttributeAccessIssue]
        writer = cv2.VideoWriter(str(path), fourcc, 30.0, (width, height))
        for _ in range(frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            writer.write(frame)
        writer.release()

    def test_json_structure(self, config: AppConfig, tmp_path: Path) -> None:
        """验证 JSON 输出包含顶层字段和 frames 数组。"""
        video_path = tmp_path / "input.mp4"
        self._create_dummy_video(video_path)
        output_dir = tmp_path / "output"

        kpts = np.zeros((1, 17, 3))
        for i in range(17):
            kpts[0, i] = [50 + i * 10, 100 + (i % 3) * 20, 0.8]
        frame_results = [
            FrameResult(keypoints=kpts, masks=[], bboxes=np.array([[40, 80, 220, 160]]))
        ]

        visualizer = Visualizer(config)
        result_path = visualizer.generate_viewer_data(video_path, frame_results, output_dir)

        assert result_path.exists()
        assert result_path.name == "per-frame.json"

        import json
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "fps" in data
        assert "frame_count" in data
        assert "width" in data
        assert "height" in data
        assert "video_filename" in data
        assert "viewer_video_filename" in data
        assert "frames" in data
        assert isinstance(data["frames"], list)
        assert data["frame_count"] == len(frame_results)

    def test_frame_fields(self, config: AppConfig, tmp_path: Path) -> None:
        """验证每帧包含必需字段。"""
        video_path = tmp_path / "input.mp4"
        self._create_dummy_video(video_path)
        output_dir = tmp_path / "output"

        kpts = np.zeros((1, 17, 3))
        for i in range(17):
            kpts[0, i] = [50 + i * 10, 100, 0.8]
        frame_results = [
            FrameResult(keypoints=kpts, masks=[], bboxes=np.array([[40, 80, 220, 160]]))
        ]

        visualizer = Visualizer(config)
        result_path = visualizer.generate_viewer_data(video_path, frame_results, output_dir)

        import json
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        frame = data["frames"][0]
        assert "frame_index" in frame
        assert "bbox" in frame
        assert "bbox_label" in frame
        assert "keypoints" in frame
        assert "mask" in frame

    def test_empty_detection(self, config: AppConfig, tmp_path: Path) -> None:
        """验证空检测帧输出空 bbox 和 null keypoints/mask。"""
        video_path = tmp_path / "input.mp4"
        self._create_dummy_video(video_path)
        output_dir = tmp_path / "output"

        frame_results = [
            FrameResult(keypoints=np.zeros((0, 17, 3)), masks=[], bboxes=np.zeros((0, 4)))
        ]

        visualizer = Visualizer(config)
        result_path = visualizer.generate_viewer_data(video_path, frame_results, output_dir)

        import json
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        frame = data["frames"][0]
        assert frame["bbox"] == []
        assert frame["bbox_label"] == ""
        assert frame["keypoints"] is None
        assert frame["mask"] is None

    def test_non_empty_detection(self, config: AppConfig, tmp_path: Path) -> None:
        """验证非空检测帧输出 4 值 bbox 和 17x3 keypoints。"""
        video_path = tmp_path / "input.mp4"
        self._create_dummy_video(video_path)
        output_dir = tmp_path / "output"

        kpts = np.zeros((1, 17, 3))
        for i in range(17):
            kpts[0, i] = [50 + i * 10, 100, 0.8]
        frame_results = [
            FrameResult(keypoints=kpts, masks=[], bboxes=np.array([[40, 80, 220, 160]]))
        ]

        visualizer = Visualizer(config)
        result_path = visualizer.generate_viewer_data(video_path, frame_results, output_dir)

        import json
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        frame = data["frames"][0]
        assert len(frame["bbox"]) == 4
        assert frame["keypoints"] is not None
        assert len(frame["keypoints"]) == 17
        assert all(len(kp) == 3 for kp in frame["keypoints"])

    def test_mask_encoding(self, config: AppConfig, tmp_path: Path) -> None:
        """验证 mask 存在时为非空 base64 字符串。"""
        video_path = tmp_path / "input.mp4"
        self._create_dummy_video(video_path)
        output_dir = tmp_path / "output"

        kpts = np.zeros((1, 17, 3))
        kpts[0, 0] = [50, 100, 0.9]
        mask = np.ones((240, 320), dtype=np.float32) * 0.5
        frame_results = [
            FrameResult(
                keypoints=kpts,
                masks=[mask],
                bboxes=np.array([[40, 80, 100, 120]]),
            )
        ]

        visualizer = Visualizer(config)
        result_path = visualizer.generate_viewer_data(video_path, frame_results, output_dir)

        import json
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        frame = data["frames"][0]
        assert frame["mask"] is not None
        assert isinstance(frame["mask"], str)
        assert len(frame["mask"]) > 0
