"""程序化 API 测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from gait_assess.api import (
    AssessmentError,
    assess,
    assess_developmental,
    assess_gait,
    assess_posture,
)
from gait_assess.llm_assessor import LLMError
from gait_assess.models import AppConfig, AssessmentResult, FrameResult, GaitCycle, KeyFrame
from gait_assess.preprocessor import VideoNotFoundError, VideoQualityError, VideoTooShortError


def _make_mock_preprocessor() -> MagicMock:
    instance = MagicMock()
    instance.process.return_value = (
        [np.zeros((10, 10, 3), dtype=np.uint8)],
        30.0,
        1.0,
        [150.0],
    )
    mock = MagicMock(return_value=instance)
    return mock


def _make_mock_segmentor() -> MagicMock:
    instance = MagicMock()
    instance.infer.return_value = [
        FrameResult(
            keypoints=np.zeros((1, 17, 3)),
            masks=[],
            bboxes=np.zeros((1, 4)),
        )
    ]
    mock = MagicMock(return_value=instance)
    return mock


def _make_mock_analyzer(metrics: dict | None = None) -> MagicMock:
    instance = MagicMock()
    instance.extract_cycles.return_value = GaitCycle(
        key_frames=[
            KeyFrame(
                frame_index=0,
                phase_name="test",
                image=np.zeros((10, 10, 3), dtype=np.uint8),
            )
        ],
        cycle_periods=[(0, 1)],
        metrics=metrics or {},
    )
    mock = MagicMock(return_value=instance)
    return mock


def _make_mock_assessor() -> MagicMock:
    instance = MagicMock()
    instance.assess.return_value = AssessmentResult(
        risk_level="正常",
        findings=["finding"],
        recommendations=["rec"],
        raw_response="ok",
    )
    mock = MagicMock(return_value=instance)
    return mock


def _make_mock_visualizer() -> MagicMock:
    instance = MagicMock()
    instance.render.return_value = Path("annotated_video.mp4")
    instance.generate_viewer_data.return_value = Path("per-frame.json")
    mock = MagicMock(return_value=instance)
    return mock


def _make_mock_report_gen() -> MagicMock:
    instance = MagicMock()
    instance.generate.return_value = Path("report.md")
    mock = MagicMock(return_value=instance)
    return mock


class TestAssess:
    """assess() 核心功能测试。"""

    @pytest.fixture
    def dummy_video(self, tmp_path: Path) -> Path:
        video = tmp_path / "test.mp4"
        video.write_text("dummy")
        return video

    @pytest.fixture
    def base_config(self, tmp_path: Path) -> AppConfig:
        return AppConfig(
            video=tmp_path / "test.mp4",
            output=tmp_path / "output",
            llm_api_key="test-key",
        )

    def test_success_flow(self, dummy_video: Path, base_config: AppConfig) -> None:
        """使用 mock 替代所有流水线组件，验证成功流程返回完整结果。"""
        with (
            patch("gait_assess.api.VideoPreprocessor", _make_mock_preprocessor()),
            patch("gait_assess.api.PoseSegmentor", _make_mock_segmentor()),
            patch("gait_assess.api.GaitAnalyzer", _make_mock_analyzer({"步频": 60})),
            patch("gait_assess.api.LLMAssessor", _make_mock_assessor()),
            patch("gait_assess.api.Visualizer", _make_mock_visualizer()),
            patch("gait_assess.api.ReportGenerator", _make_mock_report_gen()),
            patch("gait_assess.api.subprocess.run") as mock_subprocess,
            patch("gait_assess.api.shutil.copy2"),
        ):
            mock_subprocess.return_value = MagicMock(returncode=0)

            result = assess(dummy_video, base_config)

            assert result["report_path"] == Path("report.md")
            assert result["video_path"] == Path("annotated_video.mp4")
            assert result["viewer_video_path"] == base_config.output / "viewer_video.mp4"
            assert result["viewer_data_path"] == Path("per-frame.json")
            assert result["viewer_html_path"] is not None
            assert isinstance(result["assessment"], AssessmentResult)
            assert result["assessment"].risk_level == "正常"
            assert isinstance(result["gait_cycle"], GaitCycle)
            assert result["config"] == base_config
            assert len(result["frames"]) == 1
            assert result["fps"] == 30.0
            assert len(result["frame_results"]) == 1

    def test_skip_llm(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证 skip_llm=True 时返回跳过标记的评估结果。"""
        with (
            patch("gait_assess.api.VideoPreprocessor", _make_mock_preprocessor()),
            patch("gait_assess.api.PoseSegmentor", _make_mock_segmentor()),
            patch("gait_assess.api.GaitAnalyzer", _make_mock_analyzer()),
            patch("gait_assess.api.Visualizer", _make_mock_visualizer()),
            patch("gait_assess.api.ReportGenerator", _make_mock_report_gen()),
            patch("gait_assess.api.subprocess.run") as mock_subprocess,
            patch("gait_assess.api.shutil.copy2"),
        ):
            mock_subprocess.return_value = MagicMock(returncode=0)

            result = assess(dummy_video, base_config, skip_llm=True)

            assert result["assessment"].risk_level == "未知"
            assert result["assessment"].raw_response == "skip_llm"
            assert "LLM 评估已跳过" in result["assessment"].findings

    def test_preprocess_video_not_found(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证预处理阶段 VideoNotFoundError 被包装为 AssessmentError。"""
        with patch("gait_assess.api.VideoPreprocessor") as mock_preprocessor:
            instance = MagicMock()
            instance.process.side_effect = VideoNotFoundError("视频不存在")
            mock_preprocessor.return_value = instance

            with pytest.raises(AssessmentError) as exc_info:
                assess(dummy_video, base_config)

            assert exc_info.value.stage == "preprocess"
            assert "视频不存在" in str(exc_info.value)
            assert isinstance(exc_info.value.original, VideoNotFoundError)

    def test_preprocess_video_too_short(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证预处理阶段 VideoTooShortError 被包装为 AssessmentError。"""
        with patch("gait_assess.api.VideoPreprocessor") as mock_preprocessor:
            instance = MagicMock()
            instance.process.side_effect = VideoTooShortError("视频太短")
            mock_preprocessor.return_value = instance

            with pytest.raises(AssessmentError) as exc_info:
                assess(dummy_video, base_config)

            assert exc_info.value.stage == "preprocess"
            assert isinstance(exc_info.value.original, VideoTooShortError)

    def test_preprocess_video_quality_error(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证预处理阶段 VideoQualityError 被包装为 AssessmentError。"""
        with patch("gait_assess.api.VideoPreprocessor") as mock_preprocessor:
            instance = MagicMock()
            instance.process.side_effect = VideoQualityError("视频质量差")
            mock_preprocessor.return_value = instance

            with pytest.raises(AssessmentError) as exc_info:
                assess(dummy_video, base_config)

            assert exc_info.value.stage == "preprocess"
            assert isinstance(exc_info.value.original, VideoQualityError)

    def test_llm_error(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证 LLM 阶段错误被包装为 AssessmentError。"""
        with (
            patch("gait_assess.api.VideoPreprocessor", _make_mock_preprocessor()),
            patch("gait_assess.api.PoseSegmentor", _make_mock_segmentor()),
            patch("gait_assess.api.GaitAnalyzer", _make_mock_analyzer()),
            patch("gait_assess.api.LLMAssessor") as mock_assessor,
        ):
            instance = MagicMock()
            instance.assess.side_effect = LLMError("API 调用失败")
            mock_assessor.return_value = instance

            with pytest.raises(AssessmentError) as exc_info:
                assess(dummy_video, base_config)

            assert exc_info.value.stage == "llm"
            assert "API 调用失败" in str(exc_info.value)
            assert isinstance(exc_info.value.original, LLMError)

    def test_developmental_mode_auto_age(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证 developmental 模式下自动推断月龄。"""
        base_config.assessment_mode = "developmental"
        base_config.child_age_months = None

        with (
            patch("gait_assess.api.VideoPreprocessor", _make_mock_preprocessor()),
            patch("gait_assess.api.PoseSegmentor", _make_mock_segmentor()),
            patch("gait_assess.api.GaitAnalyzer", _make_mock_analyzer()),
            patch("gait_assess.api.estimate_age_from_pose", return_value=18),
            patch("gait_assess.api.LLMAssessor", _make_mock_assessor()),
            patch("gait_assess.api.Visualizer", _make_mock_visualizer()),
            patch("gait_assess.api.ReportGenerator", _make_mock_report_gen()),
            patch("gait_assess.api.subprocess.run") as mock_subprocess,
            patch("gait_assess.api.shutil.copy2"),
        ):
            mock_subprocess.return_value = MagicMock(returncode=0)

            assess(dummy_video, base_config)

            assert base_config.child_age_months == 18

    def test_developmental_mode_no_age_inference(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证 developmental 模式下推断失败时不修改月龄。"""
        base_config.assessment_mode = "developmental"
        base_config.child_age_months = None

        with (
            patch("gait_assess.api.VideoPreprocessor", _make_mock_preprocessor()),
            patch("gait_assess.api.PoseSegmentor", _make_mock_segmentor()),
            patch("gait_assess.api.GaitAnalyzer", _make_mock_analyzer()),
            patch("gait_assess.api.estimate_age_from_pose", return_value=None),
            patch("gait_assess.api.LLMAssessor", _make_mock_assessor()),
            patch("gait_assess.api.Visualizer", _make_mock_visualizer()),
            patch("gait_assess.api.ReportGenerator", _make_mock_report_gen()),
            patch("gait_assess.api.subprocess.run") as mock_subprocess,
            patch("gait_assess.api.shutil.copy2"),
        ):
            mock_subprocess.return_value = MagicMock(returncode=0)

            assess(dummy_video, base_config)

            assert base_config.child_age_months is None

    def test_ffmpeg_fallback_to_copy(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证 ffmpeg 失败时回退到 shutil.copy2。"""
        with (
            patch("gait_assess.api.VideoPreprocessor", _make_mock_preprocessor()),
            patch("gait_assess.api.PoseSegmentor", _make_mock_segmentor()),
            patch("gait_assess.api.GaitAnalyzer", _make_mock_analyzer()),
            patch("gait_assess.api.LLMAssessor", _make_mock_assessor()),
            patch("gait_assess.api.Visualizer", _make_mock_visualizer()),
            patch("gait_assess.api.ReportGenerator", _make_mock_report_gen()),
            patch("gait_assess.api.subprocess.run", side_effect=FileNotFoundError("ffmpeg not found")),
            patch("gait_assess.api.shutil.copy2") as mock_copy,
        ):
            assess(dummy_video, base_config)

            # copy2 被调用两次：一次复制视频（ffmpeg 回退），一次复制 viewer.html
            assert mock_copy.call_count == 2
            # 第一次调用是复制视频文件
            assert mock_copy.call_args_list[0][0][0] == dummy_video


class TestModeFunctions:
    """模式专用函数测试。"""

    @pytest.fixture
    def dummy_video(self, tmp_path: Path) -> Path:
        video = tmp_path / "test.mp4"
        video.write_text("dummy")
        return video

    @pytest.fixture
    def base_config(self, tmp_path: Path) -> AppConfig:
        return AppConfig(
            video=tmp_path / "test.mp4",
            output=tmp_path / "output",
            llm_api_key="test-key",
        )

    def test_assess_gait(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证 assess_gait 设置 mode=gait 并调用 assess。"""
        with patch("gait_assess.api.assess") as mock_assess:
            mock_assess.return_value = {"report_path": Path("report.md")}

            result = assess_gait(dummy_video, base_config)

            assert base_config.assessment_mode == "gait"
            mock_assess.assert_called_once_with(dummy_video, base_config)
            assert result["report_path"] == Path("report.md")

    def test_assess_developmental(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证 assess_developmental 设置 mode=developmental 并调用 assess。"""
        with patch("gait_assess.api.assess") as mock_assess:
            mock_assess.return_value = {"report_path": Path("report.md")}

            result = assess_developmental(dummy_video, base_config)

            assert base_config.assessment_mode == "developmental"
            mock_assess.assert_called_once_with(dummy_video, base_config)
            assert result["report_path"] == Path("report.md")

    def test_assess_posture(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证 assess_posture 设置 mode=posture 并调用 assess。"""
        with patch("gait_assess.api.assess") as mock_assess:
            mock_assess.return_value = {"report_path": Path("report.md")}

            result = assess_posture(dummy_video, base_config)

            assert base_config.assessment_mode == "posture"
            mock_assess.assert_called_once_with(dummy_video, base_config)
            assert result["report_path"] == Path("report.md")

    def test_mode_functions_pass_kwargs(self, dummy_video: Path, base_config: AppConfig) -> None:
        """验证模式函数正确传递 **kwargs。"""
        with patch("gait_assess.api.assess") as mock_assess:
            mock_assess.return_value = {}

            assess_gait(dummy_video, base_config, skip_llm=True)
            mock_assess.assert_called_with(dummy_video, base_config, skip_llm=True)

            assess_developmental(dummy_video, base_config, skip_llm=False)
            mock_assess.assert_called_with(dummy_video, base_config, skip_llm=False)
