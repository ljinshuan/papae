"""CLI 测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from click.testing import CliRunner

from gait_assess.cli import main
from gait_assess.llm_assessor import LLMError
from gait_assess.models import AppConfig, AssessmentResult, FrameResult, GaitCycle, KeyFrame
from gait_assess.preprocessor import VideoNotFoundError


class TestCLI:
    """CLI 测试。"""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    @pytest.fixture
    def dummy_video(self, tmp_path: Path) -> Path:
        video = tmp_path / "test.mp4"
        video.write_text("dummy")
        return video

    def test_argument_parsing(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证所有 CLI 参数正确解析。"""
        with (
            patch("gait_assess.cli.VideoPreprocessor") as mock_preprocessor,
            patch("gait_assess.cli.PoseSegmentor") as mock_segmentor,
            patch("gait_assess.cli.GaitAnalyzer") as mock_analyzer,
            patch("gait_assess.cli.LLMAssessor") as mock_assessor,
            patch("gait_assess.cli.Visualizer") as mock_visualizer,
            patch("gait_assess.cli.ReportGenerator") as mock_report_gen,
        ):
            mock_preprocessor_instance = MagicMock()
            mock_preprocessor_instance.process.return_value = (
                [np.zeros((10, 10, 3), dtype=np.uint8)],
                30.0,
            )
            mock_preprocessor.return_value = mock_preprocessor_instance

            mock_segmentor_instance = MagicMock()
            mock_segmentor_instance.infer.return_value = [
                FrameResult(
                    keypoints=np.zeros((1, 17, 3)),
                    masks=[],
                    bboxes=np.zeros((1, 4)),
                )
            ]
            mock_segmentor.return_value = mock_segmentor_instance

            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.extract_cycles.return_value = GaitCycle(
                key_frames=[
                    KeyFrame(
                        frame_index=0,
                        phase_name="test",
                        image=np.zeros((10, 10, 3), dtype=np.uint8),
                    )
                ],
                cycle_periods=[(0, 1)],
                metrics={},
            )
            mock_analyzer.return_value = mock_analyzer_instance

            mock_assessor_instance = MagicMock()
            mock_assessor_instance.assess.return_value = AssessmentResult(
                risk_level="正常",
                findings=[],
                recommendations=[],
                raw_response="",
            )
            mock_assessor.return_value = mock_assessor_instance

            mock_visualizer_instance = MagicMock()
            mock_visualizer_instance.render.return_value = Path("video.mp4")
            mock_visualizer_instance.generate_viewer_data.return_value = Path("per-frame.json")
            mock_visualizer.return_value = mock_visualizer_instance

            mock_report_gen_instance = MagicMock()
            mock_report_gen_instance.generate.return_value = Path("report.md")
            mock_report_gen.return_value = mock_report_gen_instance

            result = runner.invoke(
                main,
                [
                    "--video",
                    str(dummy_video),
                    "--output",
                    "./custom_output",
                    "--llm-api-key",
                    "test-key",
                    "--llm-model",
                    "custom-model",
                    "--yolo-pose-model",
                    "custom-pose.pt",
                    "--yolo-seg-model",
                    "custom-seg.pt",
                    "--conf-threshold",
                    "0.5",
                    "--blur-threshold",
                    "50.0",
                    "--target-height",
                    "480",
                    "--min-duration",
                    "2.0",
                ],
            )

            assert result.exit_code == 0

            config_call = mock_preprocessor.call_args[0][0]
            assert isinstance(config_call, AppConfig)
            assert config_call.video == dummy_video
            assert config_call.output == Path("./custom_output")
            assert config_call.llm_api_key == "test-key"
            assert config_call.llm_model == "custom-model"
            assert config_call.yolo_pose_model == "custom-pose.pt"
            assert config_call.yolo_seg_model == "custom-seg.pt"
            assert config_call.conf_threshold == 0.5
            assert config_call.blur_threshold == 50.0
            assert config_call.target_height == 480
            assert config_call.min_duration == 2.0

    def test_missing_video(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证不存在的视频返回退出码 3。"""
        with patch("gait_assess.cli.VideoPreprocessor") as mock_preprocessor:
            mock_preprocessor_instance = MagicMock()
            mock_preprocessor_instance.process.side_effect = VideoNotFoundError(
                "视频不存在"
            )
            mock_preprocessor.return_value = mock_preprocessor_instance

            result = runner.invoke(main, ["--video", str(dummy_video)])
            assert result.exit_code == 3
            assert "视频错误" in result.output

    def test_invalid_api_key(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证无效 API 密钥返回退出码 5。"""
        with (
            patch("gait_assess.cli.VideoPreprocessor") as mock_preprocessor,
            patch("gait_assess.cli.PoseSegmentor") as mock_segmentor,
            patch("gait_assess.cli.GaitAnalyzer") as mock_analyzer,
            patch("gait_assess.cli.LLMAssessor") as mock_assessor,
        ):
            mock_preprocessor_instance = MagicMock()
            mock_preprocessor_instance.process.return_value = (
                [np.zeros((10, 10, 3), dtype=np.uint8)],
                30.0,
            )
            mock_preprocessor.return_value = mock_preprocessor_instance

            mock_segmentor_instance = MagicMock()
            mock_segmentor_instance.infer.return_value = [
                FrameResult(
                    keypoints=np.zeros((1, 17, 3)),
                    masks=[],
                    bboxes=np.zeros((1, 4)),
                )
            ]
            mock_segmentor.return_value = mock_segmentor_instance

            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.extract_cycles.return_value = GaitCycle(
                key_frames=[
                    KeyFrame(
                        frame_index=0,
                        phase_name="test",
                        image=np.zeros((10, 10, 3), dtype=np.uint8),
                    )
                ],
                cycle_periods=[(0, 1)],
                metrics={},
            )
            mock_analyzer.return_value = mock_analyzer_instance

            mock_assessor_instance = MagicMock()
            mock_assessor_instance.assess.side_effect = LLMError("无效的 API 密钥")
            mock_assessor.return_value = mock_assessor_instance

            result = runner.invoke(main, ["--video", str(dummy_video)])
            assert result.exit_code == 5
            assert "错误" in result.output

    def test_success_flow(self, runner: CliRunner, dummy_video: Path) -> None:
        """使用 mock 替代所有流水线组件，验证成功流程输出。"""
        with (
            patch("gait_assess.cli.VideoPreprocessor") as mock_preprocessor,
            patch("gait_assess.cli.PoseSegmentor") as mock_segmentor,
            patch("gait_assess.cli.GaitAnalyzer") as mock_analyzer,
            patch("gait_assess.cli.LLMAssessor") as mock_assessor,
            patch("gait_assess.cli.Visualizer") as mock_visualizer,
            patch("gait_assess.cli.ReportGenerator") as mock_report_gen,
        ):
            mock_preprocessor_instance = MagicMock()
            mock_preprocessor_instance.process.return_value = (
                [np.zeros((10, 10, 3), dtype=np.uint8)],
                30.0,
            )
            mock_preprocessor.return_value = mock_preprocessor_instance

            mock_segmentor_instance = MagicMock()
            mock_segmentor_instance.infer.return_value = [
                FrameResult(
                    keypoints=np.zeros((1, 17, 3)),
                    masks=[],
                    bboxes=np.zeros((1, 4)),
                )
            ]
            mock_segmentor.return_value = mock_segmentor_instance

            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.extract_cycles.return_value = GaitCycle(
                key_frames=[
                    KeyFrame(
                        frame_index=0,
                        phase_name="test",
                        image=np.zeros((10, 10, 3), dtype=np.uint8),
                    )
                ],
                cycle_periods=[(0, 1)],
                metrics={"步频": 60},
            )
            mock_analyzer.return_value = mock_analyzer_instance

            mock_assessor_instance = MagicMock()
            mock_assessor_instance.assess.return_value = AssessmentResult(
                risk_level="正常",
                findings=["发现1"],
                recommendations=["建议1"],
                raw_response="raw",
            )
            mock_assessor.return_value = mock_assessor_instance

            mock_visualizer_instance = MagicMock()
            mock_visualizer_instance.render.return_value = Path("output/video.mp4")
            mock_visualizer_instance.generate_viewer_data.return_value = Path("output/per-frame.json")
            mock_visualizer.return_value = mock_visualizer_instance

            mock_report_gen_instance = MagicMock()
            mock_report_gen_instance.generate.return_value = Path("output/report.md")
            mock_report_gen.return_value = mock_report_gen_instance

            result = runner.invoke(main, ["--video", str(dummy_video)])

            assert result.exit_code == 0
            assert "评估完成" in result.output
            assert "正常" in result.output
            assert "output/report.md" in result.output
            assert "output/video.mp4" in result.output
