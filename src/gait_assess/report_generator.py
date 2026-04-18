"""报告生成：结构化 Markdown 评估报告。"""

from pathlib import Path

import cv2
import numpy as np

from gait_assess.models import AppConfig, AssessmentResult, GaitCycle


# 内联 CSS 样式
REPORT_CSS = """
<style>
.badge-risk-normal { display: inline-block; padding: 4px 12px; border-radius: 12px; background: #d4edda; color: #155724; font-weight: bold; }
.badge-risk-mild { display: inline-block; padding: 4px 12px; border-radius: 12px; background: #fff3cd; color: #856404; font-weight: bold; }
.badge-risk-moderate { display: inline-block; padding: 4px 12px; border-radius: 12px; background: #f8d7da; color: #721c24; font-weight: bold; }
.badge-risk-significant { display: inline-block; padding: 4px 12px; border-radius: 12px; background: #f5c6cb; color: #721c24; font-weight: bold; }
.card-finding { background: #f8f9fa; border-left: 4px solid #17a2b8; padding: 10px 14px; margin: 8px 0; border-radius: 0 6px 6px 0; }
.card-recommendation { background: #f8f9fa; padding: 10px 14px; margin: 8px 0; border-radius: 6px; }
@media print {
  .badge-risk-normal, .badge-risk-mild, .badge-risk-moderate, .badge-risk-significant { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .card-finding, .card-recommendation { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
"""

_RISK_BADGE_MAP = {
    "正常": ("badge-risk-normal", "✅"),
    "轻微关注": ("badge-risk-mild", "⚠️"),
    "建议就医": ("badge-risk-significant", "🚨"),
    "轻度": ("badge-risk-mild", "⚠️"),
    "中度": ("badge-risk-moderate", "📋"),
    "显著": ("badge-risk-significant", "🚨"),
}

_MODE_TITLES = {
    "gait": "婴幼儿走路姿态评估报告",
    "developmental": "婴幼儿运动发育筛查报告",
    "posture": "婴幼儿姿势矫正评估报告",
}


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

        mode = self.config.assessment_mode
        title = _MODE_TITLES.get(mode, _MODE_TITLES["gait"])

        # 风险徽章
        badge_class, badge_icon = _RISK_BADGE_MAP.get(
            assessment.risk_level, ("", "❓")
        )
        risk_badge = f'<span class="{badge_class}">{badge_icon} {assessment.risk_level}</span>'

        lines: list[str] = [
            REPORT_CSS,
            f"# {title}",
            "",
            "---",
            "",
            "## 评估摘要",
            "",
            f"**风险等级**：{risk_badge}",
        ]

        if assessment.confidence_score > 0:
            lines.append(f"**置信度**：{assessment.confidence_score:.0%}")

        if self.config.child_age_months is not None:
            lines.append(f"**月龄**：{self.config.child_age_months} 个月")

        lines.extend(["", "---", ""])

        # 步态/姿态基础指标
        if mode == "gait":
            lines.extend(["## 步态基础指标", "", "| 指标 | 数值 |", "|------|------|"])
        elif mode == "developmental":
            lines.extend(["## 发育指标", "", "| 指标 | 数值 |", "|------|------|"])
        else:
            lines.extend(["## 姿态指标", "", "| 指标 | 数值 |", "|------|------|"])

        for k, v in gait_cycle.metrics.items():
            lines.append(f"| {k} | {v} |")

        # 详细指标
        if assessment.metrics_detail:
            lines.extend(["", "### 详细姿态指标", ""])
            for k, v in assessment.metrics_detail.items():
                if isinstance(v, dict):
                    lines.append(f"**{k}**：")
                    for sk, sv in v.items():
                        lines.append(f"- {sk}: {sv}")
                else:
                    lines.append(f"- **{k}**：{v}")

        lines.extend(["", "---", "", "## 关键帧", ""])

        # 关键帧图片保存为独立文件，Markdown 使用相对路径引用
        key_frames_dir = output_dir / "key_frames"
        key_frames_dir.mkdir(parents=True, exist_ok=True)

        for i, kf in enumerate(gait_cycle.key_frames):
            img_filename = f"frame_{i:02d}.jpg"
            img_path = key_frames_dir / img_filename
            cv2.imwrite(str(img_path), kf.image)
            lines.extend([
                f"### 帧 {kf.frame_index} - {kf.phase_name}",
                "",
                f'<img src="key_frames/{img_filename}" width="400" />',
                "",
            ])

        lines.extend(["---", "", "## 评估发现", ""])

        for finding in assessment.findings:
            icon = "✅" if "正常" in finding or "良好" in finding else "⚠️"
            lines.append(
                f'<div class="card-finding">{icon} {finding}</div>'
            )

        lines.extend(["", "---", "", "## 建议措施", ""])

        for i, rec in enumerate(assessment.recommendations, 1):
            lines.append(
                f'<div class="card-recommendation">{i}. {rec}</div>'
            )

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
