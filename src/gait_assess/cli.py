"""命令行入口与流水线编排。"""

import sys
import time
from pathlib import Path

import click

from gait_assess.api import AssessmentError, assess
from gait_assess.models import AppConfig
from gait_assess.preprocessor import (
    VideoNotFoundError,
    VideoQualityError,
    VideoTooShortError,
)


@click.command()
@click.option("--video", "-v", required=True, type=click.Path(exists=True, path_type=Path), help="输入视频文件路径")
@click.option("--output", "-o", default="./results", type=click.Path(path_type=Path), help="输出目录")
@click.option("--yolo-pose-model", default="models/yolov8n-pose.pt", help="YOLO-pose 模型")
@click.option("--yolo-seg-model", default="models/yolov8n-seg.pt", help="YOLO-seg 模型")
@click.option("--conf-threshold", default=0.3, type=float, help="姿态检测置信度阈值")
@click.option("--blur-threshold", default=100.0, type=float, help="模糊帧阈值")
@click.option("--target-height", default=720, type=int, help="标准化目标高度")
@click.option("--min-duration", default=3.0, type=float, help="视频最小时长（秒）")
@click.option("--mode", default="gait", type=click.Choice(["gait", "developmental", "posture"]), help="评估模式")
@click.option("--age-months", default=None, type=int, help="儿童月龄（月），用于 developmental 模式")
@click.option("--skip-llm", is_flag=True, help="跳过 LLM 评估（仅生成可视化视频和报告）")
def main(
    video: Path,
    output: Path,
    yolo_pose_model: str,
    yolo_seg_model: str,
    conf_threshold: float,
    blur_threshold: float,
    target_height: int,
    min_duration: float,
    mode: str,
    age_months: int | None,
    skip_llm: bool,
) -> None:
    """婴幼儿走路姿态评估工具。"""
    start_time = time.time()
    exit_code = 0

    config = AppConfig(
        video=video,
        output=output,
        yolo_pose_model=yolo_pose_model,
        yolo_seg_model=yolo_seg_model,
        conf_threshold=conf_threshold,
        blur_threshold=blur_threshold,
        target_height=target_height,
        min_duration=min_duration,
        assessment_mode=mode,
        child_age_months=age_months,
    )

    try:
        result = assess(video, config, skip_llm=skip_llm)

        gait_cycle = result["gait_cycle"]
        assessment = result["assessment"]
        frames = result["frames"]

        click.echo("🎬 步骤 1/6: 视频预处理...")
        click.echo(f"   ✓ 读取 {len(frames)} 帧，fps={result['fps']:.1f}")
        click.echo("🤖 步骤 2/6: 姿态检测与分割...")
        valid_frames = sum(1 for fr in result["frame_results"] if fr.keypoints.size > 0)
        click.echo(f"   ✓ 检测到姿态的帧: {valid_frames}/{len(result['frame_results'])}")
        click.echo("📊 步骤 3/6: 步态周期分析...")
        click.echo(f"   ✓ 检测周期数: {len(gait_cycle.cycle_periods)}")
        click.echo(f"   ✓ 关键帧数: {len(gait_cycle.key_frames)}")
        if config.assessment_mode == "developmental" and config.child_age_months is not None:
            click.echo(f"   ✓ 推断月龄: {config.child_age_months} 个月")
        click.echo("🧠 步骤 4/6: LLM 评估 (已跳过)" if skip_llm else "🧠 步骤 4/6: LLM 评估...")
        click.echo(f"   ✓ 风险等级: {assessment.risk_level}")
        click.echo("🎨 步骤 5/6: 生成可视化视频...")
        click.echo(f"   ✓ 输出: {result['video_path']}")
        click.echo("📦 生成交互式查看器数据...")
        click.echo(f"   ✓ 转码视频: {result['viewer_video_path']}")
        click.echo(f"   ✓ 输出: {result['viewer_data_path']}")
        if result["viewer_html_path"]:
            click.echo(f"   ✓ 输出: {result['viewer_html_path']}")
        click.echo("📝 步骤 6/6: 生成评估报告...")
        click.echo(f"   ✓ 输出: {result['report_path']}")

        elapsed = time.time() - start_time
        click.echo("")
        click.echo("=" * 50)
        click.echo("✅ 评估完成")
        click.echo(f"   处理帧数: {len(frames)}")
        click.echo(f"   周期数: {len(gait_cycle.cycle_periods)}")
        click.echo(f"   关键帧数: {len(gait_cycle.key_frames)}")
        click.echo(f"   风险等级: {assessment.risk_level}")
        click.echo(f"   报告: {result['report_path']}")
        click.echo(f"   可视化视频: {result['video_path']}")
        click.echo(f"   查看器数据: {result['viewer_data_path']}")
        click.echo(f"   查看器页面: {result['viewer_html_path']}")
        click.echo(f"   耗时: {elapsed:.1f}秒")
        click.echo("=" * 50)

    except (VideoNotFoundError, VideoTooShortError, VideoQualityError) as e:
        click.echo(f"❌ 视频错误: {e}", err=True)
        exit_code = 3
    except AssessmentError as e:
        if e.stage == "llm":
            click.echo(f"❌ LLM 错误: {e}", err=True)
            exit_code = 5
        else:
            click.echo(f"❌ 视频错误: {e}", err=True)
            exit_code = 3
    except Exception as e:
        click.echo(f"❌ 错误: {e}", err=True)
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
