"""共享数据模型，使用 Pydantic v2 定义。"""

from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrameResult(BaseModel):
    """单帧 YOLO 推理结果。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    keypoints: np.ndarray  # (N_persons, 17, 3) -> x, y, confidence
    masks: list[np.ndarray]  # 每人的分割 mask
    bboxes: np.ndarray  # (N_persons, 4) -> x1, y1, x2, y2


class KeyFrame(BaseModel):
    """步态相位关键帧。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    frame_index: int
    phase_name: str
    image: np.ndarray
    keypoints: np.ndarray | None = None


class GaitCycle(BaseModel):
    """步态周期分析结果。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    key_frames: list[KeyFrame]
    cycle_periods: list[tuple[int, int]]
    metrics: dict[str, Any]


class AssessmentResult(BaseModel):
    """LLM 评估结果。"""

    risk_level: str  # "正常" | "轻微关注" | "建议就医"
    findings: list[str]
    recommendations: list[str]
    raw_response: str


class AppConfig(BaseSettings):
    """应用配置，支持环境变量和 CLI 参数。"""

    model_config = SettingsConfigDict(
        env_prefix="GAIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    video: Path = Field(description="输入视频文件路径")
    output: Path = Field(default=Path("./results"), description="输出目录")

    llm_api_key: str = Field(default="", description="LLM API 密钥")
    llm_model: str = Field(default="qwen-vl-max", description="LLM 模型名称")
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="LLM API 基础 URL",
    )

    yolo_pose_model: str = Field(
        default="models/yolov8m-pose.pt", description="YOLO-pose 模型路径或名称"
    )
    yolo_seg_model: str = Field(
        default="models/yolov8m-seg.pt", description="YOLO-seg 模型路径或名称"
    )

    conf_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="姿态检测置信度阈值"
    )
    blur_threshold: float = Field(
        default=100.0, ge=0.0, description="模糊帧拉普拉斯方差阈值"
    )
    target_height: int = Field(
        default=720, ge=240, description="标准化目标高度（像素）"
    )
    min_valid_frame_ratio: float = Field(
        default=0.3, ge=0.0, le=1.0, description="有效帧最小比例"
    )
    min_duration: float = Field(
        default=3.0, ge=0.0, description="视频最小时长（秒）"
    )
