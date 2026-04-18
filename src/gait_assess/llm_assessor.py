"""LLM 评估：多模态输入构造、API 调用、结构化解析。"""

import base64
import re
import time
from typing import Any

import cv2
import numpy as np
from openai import OpenAI

from gait_assess.models import AppConfig, AssessmentResult, GaitCycle


SYSTEM_PROMPT = """你是一位儿童发育评估专家。请根据以下婴幼儿走路视频的关键帧和姿态数据，
评估其走路姿态是否存在异常，并给出建议。

【评估要求】
1. 观察膝、踝、髋关节的对位关系
2. 注意是否存在膝内翻/外翻、足内翻/外翻、踮脚走路等
3. 结合婴幼儿月龄（如已知），考虑发育阶段正常范围
4. 风险分级：正常 / 轻微关注 / 建议就医

请用中文输出结构化的评估结果，格式如下：
风险等级：[正常/轻微关注/建议就医]
发现：
- [具体发现1]
- [具体发现2]
建议：
- [建议1]
- [建议2]
"""


class LLMError(Exception):
    """LLM 调用错误。"""


class LLMAssessor:
    """全模态 LLM 评估器。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
        )

    def assess(self, gait_cycle: GaitCycle) -> AssessmentResult:
        """对步态周期进行 LLM 评估。"""
        messages = self._build_messages(gait_cycle)

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=messages,  # type: ignore[arg-type]
                    timeout=30,
                )
                raw = response.choices[0].message.content or ""
                return self._parse_response(raw)
            except Exception as e:
                if attempt == 2:
                    raise LLMError(f"LLM API 调用失败: {e}") from e
                time.sleep(2**attempt)

        raise LLMError("LLM API 调用失败，已重试3次")

    def _build_messages(self, gait_cycle: GaitCycle) -> list[dict[str, Any]]:
        """构造多模态输入消息。"""
        content: list[dict] = []

        # 文本部分：步态指标
        metrics_text = "【步态基础指标】\n"
        for k, v in gait_cycle.metrics.items():
            metrics_text += f"{k}: {v}\n"
        content.append({"type": "text", "text": metrics_text})

        # 图片部分：关键帧
        for kf in gait_cycle.key_frames:
            img_b64 = self._encode_image(kf.image)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}"
                    },
                }
            )

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

    @staticmethod
    def _encode_image(image: np.ndarray) -> str:
        """将 numpy 图像编码为 base64 JPEG。"""
        _, buf = cv2.imencode(".jpg", image)
        return base64.b64encode(buf).decode("utf-8")

    def _parse_response(self, raw: str) -> AssessmentResult:
        """解析 LLM 响应为结构化结果。"""
        # 提取风险等级
        risk_match = re.search(
            r"风险等级[：:]\s*(正常|轻微关注|建议就医)", raw
        )
        risk_level = risk_match.group(1) if risk_match else "解析失败"

        # 提取发现
        findings: list[str] = []
        findings_match = re.search(
            r"发现[：:](.+?)(?:建议[：:]|$)", raw, re.DOTALL
        )
        if findings_match:
            findings = [
                line.strip("- ")
                for line in findings_match.group(1).strip().split("\n")
                if line.strip().startswith("-")
            ]

        # 提取建议
        recommendations: list[str] = []
        rec_match = re.search(r"建议[：:](.+)", raw, re.DOTALL)
        if rec_match:
            recommendations = [
                line.strip("- ")
                for line in rec_match.group(1).strip().split("\n")
                if line.strip().startswith("-")
            ]

        return AssessmentResult(
            risk_level=risk_level,
            findings=findings or ["无明确发现"],
            recommendations=recommendations or ["保持观察"],
            raw_response=raw,
        )
