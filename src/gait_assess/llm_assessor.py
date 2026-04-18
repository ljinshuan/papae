"""LLM 评估：多模态输入构造、API 调用、结构化解析。"""

import base64
import re
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import OpenAI

from gait_assess.models import AppConfig, AssessmentResult, GaitCycle
from gait_assess.pose_utils import (
    compute_joint_angles,
    compute_symmetry_metrics,
    compute_temporal_trajectories,
)


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
        # 初始化 Jinja2 模板环境
        prompts_dir = Path(__file__).parent / "prompts"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            autoescape=select_autoescape(),
        )

    def assess(self, gait_cycle: GaitCycle, video_path: Path | None = None) -> AssessmentResult:
        """对步态周期进行 LLM 评估。"""
        messages = self._build_messages(gait_cycle, video_path)

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

    def _build_messages(
        self, gait_cycle: GaitCycle, video_path: Path | None = None
    ) -> list[dict[str, Any]]:
        """构造多模态输入消息。"""
        # 1. 计算并序列化姿态数据
        pose_data = self._serialize_pose_data(gait_cycle)

        # 2. 渲染系统提示词模板
        mode = self.config.assessment_mode
        template_name = f"{mode}.jinja.md"
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception:
            # 回退到 gait 模板
            template = self.jinja_env.get_template("gait.jinja.md")

        system_prompt = template.render(
            child_age_months=self.config.child_age_months,
            pose_data=pose_data,
        )

        # 3. 构造用户消息内容
        content: list[dict] = []

        # 文本部分：结构化姿态数据
        content.append({"type": "text", "text": pose_data})

        # 视频部分：传完整视频替代关键帧图片
        if video_path is not None and video_path.exists():
            video_b64 = self._encode_video(video_path)
            content.append(
                {
                    "type": "video_url",
                    "video_url": {
                        "url": f"data:video/mp4;base64,{video_b64}"
                    },
                }
            )
        else:
            # 回退到关键帧图片（向后兼容）
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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

    @staticmethod
    def _serialize_pose_data(gait_cycle: GaitCycle) -> str:
        """将姿态数据序列化为紧凑文本格式。"""
        lines: list[str] = ["【关键帧姿态数据】"]

        for i, kf in enumerate(gait_cycle.key_frames):
            lines.append(f"\n帧 {i} [{kf.phase_name}]:")

            if kf.keypoints is not None and kf.keypoints.size > 0:
                kpts = kf.keypoints
                # 关键点坐标
                kp_lines: list[str] = []
                keypoint_names = {
                    0: "nose", 5: "left_shoulder", 6: "right_shoulder",
                    11: "left_hip", 12: "right_hip",
                    13: "left_knee", 14: "right_knee",
                    15: "left_ankle", 16: "right_ankle",
                }
                for idx, name in keypoint_names.items():
                    if kpts.shape[0] > idx:
                        x, y, conf = kpts[idx]
                        kp_lines.append(f"{name}=[{x:.1f},{y:.1f},{conf:.2f}]")
                lines.append(f"  关键点: {', '.join(kp_lines)}")

                # 关节角度
                angles = compute_joint_angles(kpts)
                angle_strs: list[str] = []
                for name, val in angles.items():
                    if not np.isnan(val):
                        angle_strs.append(f"{name}={val:.1f}°")
                if angle_strs:
                    lines.append(f"  关节角: {', '.join(angle_strs)}")

                # 对称性指标
                symmetry = compute_symmetry_metrics(kpts)
                sym_strs: list[str] = []
                for name, val in symmetry.items():
                    if not np.isnan(val) and val != float("inf"):
                        sym_strs.append(f"{name}={val:.1f}px")
                if sym_strs:
                    lines.append(f"  对称性: {', '.join(sym_strs)}")

        # 时序指标
        lines.append("\n【时序指标】")
        for k, v in gait_cycle.metrics.items():
            lines.append(f"{k}: {v}")

        return "\n".join(lines)

    @staticmethod
    def _encode_image(image: np.ndarray) -> str:
        """将 numpy 图像编码为 base64 JPEG。"""
        _, buf = cv2.imencode(".jpg", image)
        return base64.b64encode(buf).decode("utf-8")

    @staticmethod
    def _encode_video(video_path: Path) -> str:
        """将视频文件编码为 base64。"""
        with open(video_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _parse_response(self, raw: str) -> AssessmentResult:
        """解析 LLM 响应为结构化结果。"""
        # 提取风险等级
        risk_match = re.search(
            r"风险等级[：:]\s*(正常|轻微关注|建议就医|轻度|中度|显著)", raw
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
