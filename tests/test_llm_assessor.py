"""LLM 评估测试。"""

from pathlib import Path

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
