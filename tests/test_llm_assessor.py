"""LLM 评估测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gait_assess.llm_assessor import LLMAssessor
from gait_assess.models import AppConfig, AssessmentResult, GaitCycle, KeyFrame


class TestLLMAssessor:
    """LLM 评估器测试。"""

    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(video=Path("dummy.mp4"), llm_api_key="test-key")

    def test_parse_response_standard(self, config: AppConfig) -> None:
        """测试标准格式响应解析。"""
        assessor = LLMAssessor(config)
        raw = """风险等级：轻微关注
发现：
- 检测到膝外翻倾向
- 步宽略大
建议：
- 建议观察2周
- 如持续请咨询医生
"""
        result = assessor._parse_response(raw)
        assert result.risk_level == "轻微关注"
        assert len(result.findings) == 2
        assert len(result.recommendations) == 2

    def test_parse_response_malformed(self, config: AppConfig) -> None:
        """测试异常格式响应解析。"""
        assessor = LLMAssessor(config)
        raw = "这是一些非结构化文本"
        result = assessor._parse_response(raw)
        assert result.risk_level == "解析失败"
        assert result.raw_response == raw

    def test_jinja_template_rendering(self, config: AppConfig) -> None:
        """测试 Jinja 模板正确加载和渲染。"""
        assessor = LLMAssessor(config)
        template = assessor.jinja_env.get_template("gait.jinja.md")
        rendered = template.render(
            child_age_months=18,
            pose_data="测试姿态数据",
        )
        assert "儿童发育评估专家" in rendered
        assert "18 个月" in rendered
        assert "测试姿态数据" in rendered

    def test_jinja_template_developmental(self, config: AppConfig) -> None:
        """测试 developmental 模板加载。"""
        config.assessment_mode = "developmental"
        assessor = LLMAssessor(config)
        template = assessor.jinja_env.get_template("developmental.jinja.md")
        rendered = template.render(
            child_age_months=12,
            pose_data="",
        )
        assert "大运动发育筛查" in rendered
        assert "0-6 个月" in rendered

    def test_jinja_template_posture(self, config: AppConfig) -> None:
        """测试 posture 模板加载。"""
        config.assessment_mode = "posture"
        assessor = LLMAssessor(config)
        template = assessor.jinja_env.get_template("posture.jinja.md")
        rendered = template.render(
            child_age_months=None,
            pose_data="",
        )
        assert "姿势矫正评估" in rendered
        assert "脊柱倾角" in rendered

    def test_mode_switching_in_build_messages(self, config: AppConfig) -> None:
        """测试 _build_messages 根据 assessment_mode 选择模板。"""
        import numpy as np

        kpts = np.zeros((17, 3))
        kpts[15] = [100.0, 400.0, 0.95]
        kpts[16] = [150.0, 400.0, 0.95]

        gait_cycle = GaitCycle(
            key_frames=[
                KeyFrame(
                    frame_index=0,
                    phase_name="test",
                    image=np.zeros((10, 10, 3), dtype=np.uint8),
                    keypoints=kpts,
                )
            ],
            cycle_periods=[],
            metrics={},
        )

        for mode in ["gait", "developmental", "posture"]:
            config.assessment_mode = mode
            assessor = LLMAssessor(config)
            messages = assessor._build_messages(gait_cycle)

            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"

    def test_video_message_construction(self, config: AppConfig, tmp_path: Path) -> None:
        """测试视频消息构造。"""
        import numpy as np

        config.assessment_mode = "gait"
        assessor = LLMAssessor(config)

        # 创建一个小测试视频文件
        video_path = tmp_path / "test.mp4"
        video_path.write_bytes(b"fake video data")

        kpts = np.zeros((17, 3))
        kpts[15] = [100.0, 400.0, 0.95]
        gait_cycle = GaitCycle(
            key_frames=[
                KeyFrame(
                    frame_index=0,
                    phase_name="test",
                    image=np.zeros((10, 10, 3), dtype=np.uint8),
                    keypoints=kpts,
                )
            ],
            cycle_periods=[],
            metrics={},
        )

        messages = assessor._build_messages(gait_cycle, video_path=video_path)
        user_content = messages[1]["content"]

        # 验证包含姿态数据文本
        text_parts = [c for c in user_content if c.get("type") == "text"]
        assert len(text_parts) > 0
        assert "关键帧姿态数据" in text_parts[0]["text"]

        # 验证包含视频
        video_parts = [c for c in user_content if c.get("type") == "video_url"]
        assert len(video_parts) > 0
        assert "video/mp4" in video_parts[0]["video_url"]["url"]

    def test_fallback_to_keyframes_when_no_video(self, config: AppConfig) -> None:
        """测试无视频时回退到关键帧图片。"""
        import numpy as np

        assessor = LLMAssessor(config)

        kpts = np.zeros((17, 3))
        kpts[15] = [100.0, 400.0, 0.95]
        gait_cycle = GaitCycle(
            key_frames=[
                KeyFrame(
                    frame_index=0,
                    phase_name="test",
                    image=np.zeros((10, 10, 3), dtype=np.uint8),
                    keypoints=kpts,
                ),
                KeyFrame(
                    frame_index=1,
                    phase_name="test2",
                    image=np.zeros((10, 10, 3), dtype=np.uint8),
                    keypoints=kpts,
                ),
            ],
            cycle_periods=[],
            metrics={},
        )

        messages = assessor._build_messages(gait_cycle, video_path=None)
        user_content = messages[1]["content"]

        # 验证包含关键帧图片
        image_parts = [c for c in user_content if c.get("type") == "image_url"]
        assert len(image_parts) == 2  # 2 个关键帧
        assert "image/jpeg" in image_parts[0]["image_url"]["url"]
