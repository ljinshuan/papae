"""命令行入口与流水线编排。"""

import sys
import time
from pathlib import Path

import click

from gait_assess.gait_analyzer import GaitAnalyzer
from gait_assess.llm_assessor import LLMAssessor, LLMError
from gait_assess.models import AppConfig
from gait_assess.pose_segmentor import PoseSegmentor
from gait_assess.preprocessor import (
    VideoNotFoundError,
    VideoPreprocessor,
    VideoQualityError,
    VideoTooShortError,
)
from gait_assess.report_generator import ReportGenerator
from gait_assess.visualizer import Visualizer


@click.command()
@click.option("--video", "-v", required=True, type=click.Path(exists=True, path_type=Path), help="输入视频文件路径")
@click.option("--output", "-o", default="./results", type=click.Path(path_type=Path), help="输出目录")
@click.option("--llm-api-key", envvar="QWEN_API_KEY", help="LLM API 密钥")
@click.option("--llm-model", default="qwen-vl-max", help="LLM 模型名称")
@click.option("--yolo-pose-model", default="yolov8n-pose.pt", help="YOLO-pose 模型")
@click.option("--yolo-seg-model", default="yolov8n-seg.pt", help="YOLO-seg 模型")
@click.option("--conf-threshold", default=0.3, type=float, help="姿态检测置信度阈值")
@click.option("--blur-threshold", default=100.0, type=float, help="模糊帧阈值")
@click.option("--target-height", default=720, type=int, help="标准化目标高度")
@click.option("--min-duration", default=3.0, type=float, help="视频最小时长（秒）")
def main(
    video: Path,
    output: Path,
    llm_api_key: str,
    llm_model: str,
    yolo_pose_model: str,
    yolo_seg_model: str,
    conf_threshold: float,
    blur_threshold: float,
    target_height: int,
    min_duration: float,
) -> None:
    """婴幼儿走路姿态评估工具。"""
    start_time = time.time()
    exit_code = 0

    config = AppConfig(
        video=video,
        output=output,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        yolo_pose_model=yolo_pose_model,
        yolo_seg_model=yolo_seg_model,
        conf_threshold=conf_threshold,
        blur_threshold=blur_threshold,
        target_height=target_height,
        min_duration=min_duration,
    )

    try:
        click.echo("🎬 步骤 1/6: 视频预处理...")
        preprocessor = VideoPreprocessor(config)
        frames, fps = preprocessor.process(video)
        click.echo(f"   ✓ 读取 {len(frames)} 帧，fps={fps:.1f}")

        click.echo("🤖 步骤 2/6: 姿态检测与分割...")
        segmentor = PoseSegmentor(config)
        frame_results = segmentor.infer(frames)
        valid_frames = sum(1 for fr in frame_results if fr.keypoints.size > 0)
        click.echo(f"   ✓ 检测到姿态的帧: {valid_frames}/{len(frame_results)}")

        click.echo("📊 步骤 3/6: 步态周期分析...")
        analyzer = GaitAnalyzer(config)
        gait_cycle = analyzer.extract_cycles(frame_results, fps)
        click.echo(f"   ✓ 检测周期数: {len(gait_cycle.cycle_periods)}")
        click.echo(f"   ✓ 关键帧数: {len(gait_cycle.key_frames)}")

        # 保存关键帧图像（供 LLM 和报告使用）
        for i, kf in enumerate(gait_cycle.key_frames):
            if i < len(frames):
                kf.image = frames[i]

        click.echo("🧠 步骤 4/6: LLM 评估...")
        assessor = LLMAssessor(config)
        assessment = assessor.assess(gait_cycle)
        click.echo(f"   ✓ 风险等级: {assessment.risk_level}")

        click.echo("🎨 步骤 5/6: 生成可视化视频...")
        visualizer = Visualizer(config)
        video_path = visualizer.render(video, frame_results, gait_cycle, output)
        click.echo(f"   ✓ 输出: {video_path}")

        click.echo("📝 步骤 6/6: 生成评估报告...")
        report_gen = ReportGenerator(config)
        report_path = report_gen.generate(assessment, gait_cycle, output)
        click.echo(f"   ✓ 输出: {report_path}")

        elapsed = time.time() - start_time
        click.echo("")
        click.echo("=" * 50)
        click.echo("✅ 评估完成")
        click.echo(f"   处理帧数: {len(frames)}")
        click.echo(f"   周期数: {len(gait_cycle.cycle_periods)}")
        click.echo(f"   关键帧数: {len(gait_cycle.key_frames)}")
        click.echo(f"   风险等级: {assessment.risk_level}")
        click.echo(f"   报告: {report_path}")
        click.echo(f"   可视化视频: {video_path}")
        click.echo(f"   耗时: {elapsed:.1f}秒")
        click.echo("=" * 50)

    except (VideoNotFoundError, VideoTooShortError, VideoQualityError) as e:
        click.echo(f"❌ 视频错误: {e}", err=True)
        exit_code = 3
    except Exception as e:
        click.echo(f"❌ 错误: {e}", err=True)
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
