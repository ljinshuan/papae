"""报告生成：Markdown 评估报告。"""

from pathlib import Path

import cv2
import numpy as np

from gait_assess.models import AppConfig, AssessmentResult, GaitCycle


class ReportGenerator:
    """Markdown 报告生成器。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(
        self,
        assessment: AssessmentResult,
        gait_cycle: GaitCycle,
        output_dir: Path,
    ) -> Path:
        """生成 Markdown 评估报告。"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存关键帧图片
        keyframe_dir = output_dir / "keyframes"
        keyframe_dir.mkdir(exist_ok=True)
        keyframe_paths: list[Path] = []

        for i, kf in enumerate(gait_cycle.key_frames):
            img_path = keyframe_dir / f"keyframe_{i:02d}_{kf.phase_name}.jpg"
            cv2.imwrite(str(img_path), kf.image)
            keyframe_paths.append(img_path.relative_to(output_dir))

        # 风险等级样式
        risk_style = {
            "正常": "✅ **正常**",
            "轻微关注": "⚠️ **轻微关注**",
            "建议就医": "🚨 **建议就医**",
        }.get(assessment.risk_level, f"❓ **{assessment.risk_level}**")

        # 构建报告
        lines: list[str] = [
            "# 婴幼儿走路姿态评估报告",
            "",
            "---",
            "",
            "## 评估摘要",
            "",
            f"**风险等级**：{risk_style}",
            "",
            "---",
            "",
            "## 步态基础指标",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
        ]

        for k, v in gait_cycle.metrics.items():
            lines.append(f"| {k} | {v} |")

        lines.extend([
            "",
            "---",
            "",
            "## 关键帧",
            "",
        ])

        for i, kf in enumerate(gait_cycle.key_frames):
            rel_path = keyframe_paths[i] if i < len(keyframe_paths) else ""
            lines.extend([
                f"### 帧 {kf.frame_index} - {kf.phase_name}",
                "",
                f"![{kf.phase_name}]({rel_path})",
                "",
            ])

        lines.extend([
            "---",
            "",
            "## 评估发现",
            "",
        ])

        for finding in assessment.findings:
            lines.append(f"- {finding}")

        lines.extend([
            "",
            "---",
            "",
            "## 建议措施",
            "",
        ])

        for rec in assessment.recommendations:
            lines.append(f"- {rec}")

        lines.extend([
            "",
            "---",
            "",
            "> ⚠️ **免责声明**：本评估仅供参考，不构成医学诊断。如有疑虑请咨询专业医生。",
            "",
        ])

        report_path = output_dir / "report.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")

        return report_path
