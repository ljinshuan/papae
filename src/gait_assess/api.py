"""程序化 API：封装完整流水线，供其他项目导入使用。"""

import shutil
import subprocess
from pathlib import Path
from typing import Any

import cv2

from gait_assess.gait_analyzer import GaitAnalyzer
from gait_assess.llm_assessor import LLMAssessor, LLMError
from gait_assess.models import AppConfig, AssessmentResult, GaitCycle
from gait_assess.pose_segmentor import PoseSegmentor
from gait_assess.pose_utils import estimate_age_from_pose
from gait_assess.preprocessor import (
    VideoNotFoundError,
    VideoPreprocessor,
    VideoQualityError,
    VideoTooShortError,
)
from gait_assess.report_generator import ReportGenerator
from gait_assess.visualizer import Visualizer


class AssessmentError(Exception):
    """评估流水线错误。"""

    def __init__(self, message: str, stage: str = "", original: Exception | None = None) -> None:
        super().__init__(message)
        self.stage = stage
        self.original = original


def assess(video: Path | str, config: AppConfig, *, skip_llm: bool = False) -> dict[str, Any]:
    """执行完整的姿态评估流水线。

    Args:
        video: 输入视频文件路径
        config: 应用配置
        skip_llm: 是否跳过 LLM 评估

    Returns:
        包含所有输出路径和结构化结果的字典

    Raises:
        AssessmentError: 任何流水线阶段的错误
    """
    video_path = Path(video)
    output = config.output

    # 1. 视频预处理
    try:
        preprocessor = VideoPreprocessor(config)
        frames, fps, preprocess_scale, frame_qualities = preprocessor.process(video_path)
    except (VideoNotFoundError, VideoTooShortError, VideoQualityError) as e:
        raise AssessmentError(str(e), stage="preprocess", original=e) from e

    # 2. 姿态检测与分割
    segmentor = PoseSegmentor(config)
    frame_results = segmentor.infer(frames)

    # 3. 步态周期分析
    analyzer = GaitAnalyzer(config)
    gait_cycle = analyzer.extract_cycles(
        frame_results, fps, frame_qualities, config.blur_threshold
    )

    # 运动发育模式下，若未提供月龄则自动推断
    if config.assessment_mode == "developmental" and config.child_age_months is None:
        inferred_age = estimate_age_from_pose(frame_results)
        if inferred_age is not None:
            config.child_age_months = inferred_age

    # 保存关键帧图像（供 LLM 和报告使用）
    for kf in gait_cycle.key_frames:
        if 0 <= kf.frame_index < len(frames):
            kf.image = frames[kf.frame_index]

    # 4. LLM 评估
    if skip_llm:
        assessment = AssessmentResult(
            risk_level="未知",
            findings=["LLM 评估已跳过"],
            recommendations=["如需完整评估请提供 API 密钥"],
            raw_response="skip_llm",
        )
    else:
        try:
            assessor = LLMAssessor(config)
            assessment = assessor.assess(gait_cycle, video_path=video_path)
        except LLMError as e:
            raise AssessmentError(str(e), stage="llm", original=e) from e

    # 5. 生成可视化视频
    visualizer = Visualizer(config)
    annotated_video_path = visualizer.render(
        video_path, frame_results, gait_cycle, output, preprocess_scale
    )

    # 6. 生成交互式查看器数据
    viewer_video_name = "viewer_video.mp4"
    viewer_video_path = output / viewer_video_name
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                str(viewer_video_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.copy2(video_path, viewer_video_path)

    viewer_data_path = visualizer.generate_viewer_data(
        video_path, frame_results, output, viewer_video_name, preprocess_scale
    )

    viewer_html_src = Path(__file__).parent / "viewer.html"
    viewer_html_dst = output / "viewer.html"
    if viewer_html_src.exists():
        output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(viewer_html_src, viewer_html_dst)

    # 7. 生成评估报告
    report_gen = ReportGenerator(config)
    report_path = report_gen.generate(assessment, gait_cycle, output)

    return {
        "report_path": report_path,
        "video_path": annotated_video_path,
        "viewer_video_path": viewer_video_path,
        "viewer_data_path": viewer_data_path,
        "viewer_html_path": viewer_html_dst if viewer_html_src.exists() else None,
        "assessment": assessment,
        "gait_cycle": gait_cycle,
        "config": config,
        "frames": frames,
        "fps": fps,
        "frame_results": frame_results,
    }


def assess_gait(video: Path | str, config: AppConfig, **kwargs: Any) -> dict[str, Any]:
    """走路步态评估（设置 mode=gait）。"""
    config.assessment_mode = "gait"
    return assess(video, config, **kwargs)


def assess_developmental(video: Path | str, config: AppConfig, **kwargs: Any) -> dict[str, Any]:
    """运动发育筛查（设置 mode=developmental）。"""
    config.assessment_mode = "developmental"
    return assess(video, config, **kwargs)


def assess_posture(video: Path | str, config: AppConfig, **kwargs: Any) -> dict[str, Any]:
    """姿势矫正评估（设置 mode=posture）。"""
    config.assessment_mode = "posture"
    return assess(video, config, **kwargs)
