"""婴幼儿走路姿态评估系统."""

from gait_assess.api import (
    AssessmentError,
    assess,
    assess_developmental,
    assess_gait,
    assess_posture,
)
from gait_assess.gait_analyzer import GaitAnalyzer
from gait_assess.llm_assessor import LLMAssessor
from gait_assess.models import (
    AppConfig,
    AssessmentResult,
    FrameResult,
    GaitCycle,
    KeyFrame,
    PoseMetrics,
)
from gait_assess.pose_segmentor import PoseSegmentor
from gait_assess.preprocessor import VideoPreprocessor
from gait_assess.report_generator import ReportGenerator
from gait_assess.visualizer import Visualizer

__version__ = "0.1.0"

__all__ = [
    # 高级 API
    "assess",
    "assess_gait",
    "assess_developmental",
    "assess_posture",
    "AssessmentError",
    # 核心组件类
    "VideoPreprocessor",
    "PoseSegmentor",
    "GaitAnalyzer",
    "LLMAssessor",
    "Visualizer",
    "ReportGenerator",
    # 数据模型
    "AppConfig",
    "AssessmentResult",
    "GaitCycle",
    "KeyFrame",
    "FrameResult",
    "PoseMetrics",
    # 版本号
    "__version__",
]
