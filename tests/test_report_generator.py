"""报告生成器测试。"""

from pathlib import Path

import numpy as np
import pytest

from gait_assess.models import AppConfig, AssessmentResult, GaitCycle, KeyFrame
from gait_assess.report_generator import ReportGenerator


class TestReportGenerator:
    """ReportGenerator 测试类。"""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(video=Path("dummy.mp4"))

    @pytest.fixture
    def sample_gait_cycle(self) -> GaitCycle:
        key_frames = [
            KeyFrame(
                frame_index=10,
                phase_name="脚跟着地",
                image=np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8),
                keypoints=np.random.rand(17, 3).astype(np.float32),
            ),
            KeyFrame(
                frame_index=25,
                phase_name="站立中期",
                image=np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8),
                keypoints=np.random.rand(17, 3).astype(np.float32),
            ),
        ]
        return GaitCycle(
            key_frames=key_frames,
            cycle_periods=[(0, 50)],
            metrics={"步频": "120 步/分", "步长": "0.35 m"},
        )

    @pytest.fixture
    def sample_assessment(self) -> AssessmentResult:
        return AssessmentResult(
            risk_level="正常",
            findings=["步态对称性良好", "脚踝活动范围正常"],
            recommendations=["继续保持日常活动", "定期观察步态变化"],
            raw_response="test",
        )

    def test_report_structure(
        self,
        config: AppConfig,
        sample_assessment: AssessmentResult,
        sample_gait_cycle: GaitCycle,
        tmp_path: Path,
    ) -> None:
        """验证报告包含所有必需章节。"""
        generator = ReportGenerator(config)
        report_path = generator.generate(sample_assessment, sample_gait_cycle, tmp_path)

        content = report_path.read_text(encoding="utf-8")

        assert "# 婴幼儿走路姿态评估报告" in content
        assert "## 评估摘要" in content
        assert "## 步态基础指标" in content
        assert "## 关键帧" in content
        assert "## 评估发现" in content
        assert "## 建议措施" in content
        assert "免责声明" in content

    def test_risk_level_styling(
        self,
        config: AppConfig,
        sample_gait_cycle: GaitCycle,
        tmp_path: Path,
    ) -> None:
        """验证不同风险等级使用正确的 Markdown 格式。"""
        risk_levels = {
            "正常": "✅ **正常**",
            "轻微关注": "⚠️ **轻微关注**",
            "建议就医": "🚨 **建议就医**",
        }

        for level, expected_style in risk_levels.items():
            assessment = AssessmentResult(
                risk_level=level,
                findings=[],
                recommendations=[],
                raw_response="test",
            )
            generator = ReportGenerator(config)
            report_path = generator.generate(assessment, sample_gait_cycle, tmp_path / level)
            content = report_path.read_text(encoding="utf-8")
            assert expected_style in content

    def test_keyframe_embedding(
        self,
        config: AppConfig,
        sample_assessment: AssessmentResult,
        sample_gait_cycle: GaitCycle,
        tmp_path: Path,
    ) -> None:
        """验证关键帧图片被保存并在报告中被引用。"""
        generator = ReportGenerator(config)
        output_dir = tmp_path / "output"
        generator.generate(sample_assessment, sample_gait_cycle, output_dir)

        keyframe_dir = output_dir / "keyframes"
        assert keyframe_dir.exists()

        for i, kf in enumerate(sample_gait_cycle.key_frames):
            img_path = keyframe_dir / f"keyframe_{i:02d}_{kf.phase_name}.jpg"
            assert img_path.exists()

        report_path = output_dir / "report.md"
        content = report_path.read_text(encoding="utf-8")

        for kf in sample_gait_cycle.key_frames:
            assert f"![{kf.phase_name}]" in content

    def test_disclaimer_present(
        self,
        config: AppConfig,
        sample_assessment: AssessmentResult,
        sample_gait_cycle: GaitCycle,
        tmp_path: Path,
    ) -> None:
        """验证免责声明出现在报告末尾。"""
        generator = ReportGenerator(config)
        report_path = generator.generate(sample_assessment, sample_gait_cycle, tmp_path)

        content = report_path.read_text(encoding="utf-8")
        assert content.strip().endswith(
            "> ⚠️ **免责声明**：本评估仅供参考，不构成医学诊断。如有疑虑请咨询专业医生。"
        )
