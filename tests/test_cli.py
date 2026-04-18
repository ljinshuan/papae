"""CLI 测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from click.testing import CliRunner

from gait_assess.api import AssessmentError
from gait_assess.cli import main
from gait_assess.llm_assessor import LLMError
from gait_assess.models import AppConfig, AssessmentResult, GaitCycle, KeyFrame
from gait_assess.preprocessor import VideoNotFoundError


def _make_assess_result(config: AppConfig) -> dict:
    """构造 api.assess() 的成功返回值。"""
    return {
        "report_path": config.output / "report.md",
        "video_path": config.output / "annotated_video.mp4",
        "viewer_video_path": config.output / "viewer_video.mp4",
        "viewer_data_path": config.output / "per-frame.json",
        "viewer_html_path": config.output / "viewer.html",
        "assessment": AssessmentResult(
            risk_level="正常",
            findings=["finding"],
            recommendations=["rec"],
            raw_response="ok",
        ),
        "gait_cycle": GaitCycle(
            key_frames=[
                KeyFrame(
                    frame_index=0,
                    phase_name="test",
                    image=np.zeros((10, 10, 3), dtype=np.uint8),
                )
            ],
            cycle_periods=[(0, 1)],
            metrics={"步频": 60},
        ),
        "config": config,
        "frames": [np.zeros((10, 10, 3), dtype=np.uint8)],
        "fps": 30.0,
        "frame_results": [],
    }


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
        """验证所有 CLI 参数正确解析并传给 api.assess()。"""
        with patch("gait_assess.cli.assess") as mock_assess:
            mock_assess.return_value = _make_assess_result(
                AppConfig(video=dummy_video, output=Path("./custom_output"))
            )

            result = runner.invoke(
                main,
                [
                    "--video",
                    str(dummy_video),
                    "--output",
                    "./custom_output",
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
                    "--mode",
                    "developmental",
                    "--age-months",
                    "18",
                ],
            )

            assert result.exit_code == 0
            assert mock_assess.called

            config_call = mock_assess.call_args[0][1]
            assert isinstance(config_call, AppConfig)
            assert config_call.video == dummy_video
            assert config_call.output == Path("./custom_output")
            assert config_call.yolo_pose_model == "custom-pose.pt"
            assert config_call.yolo_seg_model == "custom-seg.pt"
            assert config_call.conf_threshold == 0.5
            assert config_call.blur_threshold == 50.0
            assert config_call.target_height == 480
            assert config_call.min_duration == 2.0
            assert config_call.assessment_mode == "developmental"
            assert config_call.child_age_months == 18

    def test_missing_video(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证不存在的视频返回退出码 3。"""
        with patch("gait_assess.cli.assess") as mock_assess:
            mock_assess.side_effect = VideoNotFoundError("视频不存在")

            result = runner.invoke(main, ["--video", str(dummy_video)])
            assert result.exit_code == 3
            assert "视频错误" in result.output

    def test_invalid_api_key(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证无效 API 密钥返回退出码 5。"""
        with patch("gait_assess.cli.assess") as mock_assess:
            mock_assess.side_effect = AssessmentError(
                "API 调用失败", stage="llm", original=LLMError("无效的 API 密钥")
            )

            result = runner.invoke(main, ["--video", str(dummy_video)])
            assert result.exit_code == 5
            assert "错误" in result.output

    def test_success_flow(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证成功流程输出。"""
        with patch("gait_assess.cli.assess") as mock_assess:
            mock_assess.return_value = _make_assess_result(
                AppConfig(video=dummy_video, output=Path("./results"))
            )

            result = runner.invoke(main, ["--video", str(dummy_video)])

            assert result.exit_code == 0
            assert "评估完成" in result.output
            assert "正常" in result.output
            assert "report.md" in result.output

    def test_mode_argument(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证 --mode 参数正确解析并影响配置。"""
        with patch("gait_assess.cli.assess") as mock_assess:
            mock_assess.return_value = _make_assess_result(
                AppConfig(video=dummy_video, output=Path("./results"))
            )

            for mode in ["gait", "developmental", "posture"]:
                result = runner.invoke(
                    main, ["--video", str(dummy_video), "--mode", mode]
                )
                assert result.exit_code == 0, f"mode={mode} failed"
                config_call = mock_assess.call_args[0][1]
                assert config_call.assessment_mode == mode

    def test_age_months_argument(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证 --age-months 参数正确解析。"""
        with patch("gait_assess.cli.assess") as mock_assess:
            mock_assess.return_value = _make_assess_result(
                AppConfig(video=dummy_video, output=Path("./results"))
            )

            result = runner.invoke(
                main,
                [
                    "--video",
                    str(dummy_video),
                    "--mode",
                    "developmental",
                    "--age-months",
                    "24",
                ],
            )
            assert result.exit_code == 0
            config_call = mock_assess.call_args[0][1]
            assert config_call.child_age_months == 24
            assert config_call.assessment_mode == "developmental"

    def test_default_mode_is_gait(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证不传 --mode 时默认使用 gait 模式。"""
        with patch("gait_assess.cli.assess") as mock_assess:
            mock_assess.return_value = _make_assess_result(
                AppConfig(video=dummy_video, output=Path("./results"))
            )

            result = runner.invoke(main, ["--video", str(dummy_video)])
            assert result.exit_code == 0
            config_call = mock_assess.call_args[0][1]
            assert config_call.assessment_mode == "gait"

    def test_skip_llm(self, runner: CliRunner, dummy_video: Path) -> None:
        """验证 --skip-llm 正确传给 api.assess()。"""
        with patch("gait_assess.cli.assess") as mock_assess:
            mock_assess.return_value = _make_assess_result(
                AppConfig(video=dummy_video, output=Path("./results"))
            )

            result = runner.invoke(
                main, ["--video", str(dummy_video), "--skip-llm"]
            )
            assert result.exit_code == 0
            assert mock_assess.call_args[1]["skip_llm"] is True
