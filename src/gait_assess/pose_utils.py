"""姿态计算工具函数：关节角度、对称性、时序轨迹。"""

from typing import Any

import numpy as np

from gait_assess.models import FrameResult

# COCO 关键点索引
NOSE = 0
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_KNEE = 13
RIGHT_KNEE = 14
LEFT_ANKLE = 15
RIGHT_ANKLE = 16

# 置信度阈值
MIN_CONFIDENCE = 0.3


def angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    """计算两个 2D 向量的夹角（度数）。"""
    if v1.size == 0 or v2.size == 0:
        return float(np.nan)
    norm1 = float(np.linalg.norm(v1))
    norm2 = float(np.linalg.norm(v2))
    if norm1 == 0 or norm2 == 0:
        return float(np.nan)
    cos_theta = float(np.dot(v1, v2)) / (norm1 * norm2)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_theta)))


def _check_confidence(kpts: np.ndarray, indices: list[int]) -> bool:
    """检查给定索引的关键点置信度是否都 >= 阈值。"""
    if kpts.shape[0] <= max(indices):
        return False
    return all(float(kpts[i, 2]) >= MIN_CONFIDENCE for i in indices)


def compute_joint_angles(kpts: np.ndarray) -> dict[str, float]:
    """计算关节角度（度数）。

    返回:
        - left_knee: 左膝角度（hip-knee-ankle）
        - right_knee: 右膝角度（hip-knee-ankle）
        - left_ankle: 左踝角度（knee-ankle 与垂直线）
        - right_ankle: 右踝角度（knee-ankle 与垂直线）
        - spine_tilt: 脊柱倾角（肩中点-髋中点 与垂直线）
    """
    angles: dict[str, float] = {
        "left_knee": float(np.nan),
        "right_knee": float(np.nan),
        "left_ankle": float(np.nan),
        "right_ankle": float(np.nan),
        "spine_tilt": float(np.nan),
    }
    if kpts.size == 0 or kpts.ndim != 2:
        return angles

    # 左膝角度
    if _check_confidence(kpts, [LEFT_HIP, LEFT_KNEE, LEFT_ANKLE]):
        v1 = kpts[LEFT_HIP, :2] - kpts[LEFT_KNEE, :2]
        v2 = kpts[LEFT_ANKLE, :2] - kpts[LEFT_KNEE, :2]
        angles["left_knee"] = angle_between(v1, v2)

    # 右膝角度
    if _check_confidence(kpts, [RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE]):
        v1 = kpts[RIGHT_HIP, :2] - kpts[RIGHT_KNEE, :2]
        v2 = kpts[RIGHT_ANKLE, :2] - kpts[RIGHT_KNEE, :2]
        angles["right_knee"] = angle_between(v1, v2)

    # 左踝角度（小腿与垂直向下夹角）
    if _check_confidence(kpts, [LEFT_KNEE, LEFT_ANKLE]):
        leg = kpts[LEFT_ANKLE, :2] - kpts[LEFT_KNEE, :2]
        vertical = np.array([0.0, 1.0])
        angles["left_ankle"] = angle_between(leg, vertical)

    # 右踝角度
    if _check_confidence(kpts, [RIGHT_KNEE, RIGHT_ANKLE]):
        leg = kpts[RIGHT_ANKLE, :2] - kpts[RIGHT_KNEE, :2]
        vertical = np.array([0.0, 1.0])
        angles["right_ankle"] = angle_between(leg, vertical)

    # 脊柱倾角（与垂直线的最小夹角，0°-90°）
    if _check_confidence(kpts, [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]):
        shoulder_mid = (kpts[LEFT_SHOULDER, :2] + kpts[RIGHT_SHOULDER, :2]) / 2
        hip_mid = (kpts[LEFT_HIP, :2] + kpts[RIGHT_HIP, :2]) / 2
        spine = shoulder_mid - hip_mid
        vertical = np.array([0.0, 1.0])
        raw_angle = angle_between(spine, vertical)
        # 取最小夹角（向上或向下偏离垂直线的程度）
        angles["spine_tilt"] = min(raw_angle, 180.0 - raw_angle)

    return angles


def compute_symmetry_metrics(kpts: np.ndarray) -> dict[str, float]:
    """计算对称性指标（像素）。

    返回:
        - shoulder_height_diff: 肩高差
        - pelvic_tilt: 骨盆倾斜
        - shoulder_hip_ratio: 肩高差 / 骨盆倾斜（骨盆倾斜为0时返回inf）
    """
    metrics: dict[str, float] = {
        "shoulder_height_diff": float(np.nan),
        "pelvic_tilt": float(np.nan),
        "shoulder_hip_ratio": float(np.nan),
    }
    if kpts.size == 0 or kpts.ndim != 2:
        return metrics

    # 肩高差
    if _check_confidence(kpts, [LEFT_SHOULDER, RIGHT_SHOULDER]):
        diff = abs(float(kpts[LEFT_SHOULDER, 1] - kpts[RIGHT_SHOULDER, 1]))
        metrics["shoulder_height_diff"] = diff

    # 骨盆倾斜
    if _check_confidence(kpts, [LEFT_HIP, RIGHT_HIP]):
        diff = abs(float(kpts[LEFT_HIP, 1] - kpts[RIGHT_HIP, 1]))
        metrics["pelvic_tilt"] = diff

    # 肩-髋水平比
    if not np.isnan(metrics["shoulder_height_diff"]) and not np.isnan(
        metrics["pelvic_tilt"]
    ):
        if metrics["pelvic_tilt"] != 0:
            metrics["shoulder_hip_ratio"] = (
                metrics["shoulder_height_diff"] / metrics["pelvic_tilt"]
            )
        else:
            metrics["shoulder_hip_ratio"] = float(np.inf)

    return metrics


def compute_temporal_trajectories(
    frame_results: list[FrameResult],
) -> dict[str, Any]:
    """计算时序轨迹。

    返回:
        - left_ankle_y: 左踝 Y 坐标列表
        - right_ankle_y: 右踝 Y 坐标列表
        - step_lengths: 相邻帧左右踝 X 坐标差列表
    """
    left_ankle_y: list[float] = []
    right_ankle_y: list[float] = []
    step_lengths: list[float] = []

    for fr in frame_results:
        if fr.keypoints.size == 0:
            left_ankle_y.append(float(np.nan))
            right_ankle_y.append(float(np.nan))
            step_lengths.append(float(np.nan))
            continue

        kpts = fr.keypoints[0]

        # 左踝 Y
        if kpts.shape[0] > LEFT_ANKLE and float(kpts[LEFT_ANKLE, 2]) >= MIN_CONFIDENCE:
            left_ankle_y.append(float(kpts[LEFT_ANKLE, 1]))
        else:
            left_ankle_y.append(float(np.nan))

        # 右踝 Y
        if kpts.shape[0] > RIGHT_ANKLE and float(kpts[RIGHT_ANKLE, 2]) >= MIN_CONFIDENCE:
            right_ankle_y.append(float(kpts[RIGHT_ANKLE, 1]))
        else:
            right_ankle_y.append(float(np.nan))

        # 步长 = 左右踝 X 坐标差
        if (
            kpts.shape[0] > max(LEFT_ANKLE, RIGHT_ANKLE)
            and float(kpts[LEFT_ANKLE, 2]) >= MIN_CONFIDENCE
            and float(kpts[RIGHT_ANKLE, 2]) >= MIN_CONFIDENCE
        ):
            step_lengths.append(abs(float(kpts[LEFT_ANKLE, 0] - kpts[RIGHT_ANKLE, 0])))
        else:
            step_lengths.append(float(np.nan))

    return {
        "left_ankle_y": left_ankle_y,
        "right_ankle_y": right_ankle_y,
        "step_lengths": step_lengths,
    }


def detect_standing_frames(
    frame_results: list[FrameResult], n_best: int = 3
) -> list[int]:
    """从视频中检测最稳定的站立帧。

    站立帧特征：
    - 左右踝 Y 坐标接近（双脚着地）
    - 脊柱倾角小（身体直立）
    - 关键点置信度高

    返回最稳定的 n_best 个帧的索引列表。
    """
    scores: list[tuple[int, float]] = []

    for i, fr in enumerate(frame_results):
        if fr.keypoints.size == 0:
            continue
        kpts = fr.keypoints[0]

        # 检查是否有足够的关键点
        required = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP, LEFT_ANKLE, RIGHT_ANKLE]
        if kpts.shape[0] <= max(required):
            continue
        if not all(float(kpts[idx, 2]) >= MIN_CONFIDENCE for idx in required):
            continue

        # 计算稳定性分数（越低越稳定）
        score = 0.0

        # 双脚着地：左右踝 Y 接近
        ankle_y_diff = abs(float(kpts[LEFT_ANKLE, 1] - kpts[RIGHT_ANKLE, 1]))
        score += ankle_y_diff

        # 脊柱直立：脊柱倾角小
        angles = compute_joint_angles(kpts)
        spine_tilt = angles.get("spine_tilt", float("nan"))
        if not np.isnan(spine_tilt):
            score += spine_tilt

        scores.append((i, score))

    # 按分数升序排列，取前 n_best
    scores.sort(key=lambda x: x[1])
    return [idx for idx, _ in scores[:n_best]]


def estimate_age_from_pose(frame_results: list[FrameResult]) -> int | None:
    """从姿态数据启发式推断大致月龄。

    基于以下启发式规则：
    - 如果检测到明显步态周期（脚踝 Y 大幅波动）：≥12 个月
    - 如果只有爬行/匍匐姿态（身体贴近地面）：6-12 个月
    - 如果能站立但无明显步态：9-15 个月
    - 如果身高（肩到踝距离）很小：0-6 个月

    返回推断的月龄或 None（无法推断时）。
    """
    if not frame_results:
        return None

    # 收集有效帧
    valid_frames: list[np.ndarray] = []
    for fr in frame_results:
        if fr.keypoints.size == 0:
            continue
        kpts = fr.keypoints[0]
        if kpts.shape[0] > LEFT_ANKLE and float(kpts[LEFT_ANKLE, 2]) >= MIN_CONFIDENCE:
            valid_frames.append(kpts)

    if not valid_frames:
        return None

    # 计算脚踝 Y 坐标波动幅度（判断是否有步态）
    ankle_y_values: list[float] = []
    for kpts in valid_frames:
        if kpts.shape[0] > LEFT_ANKLE:
            ankle_y_values.append(float(kpts[LEFT_ANKLE, 1]))

    if len(ankle_y_values) < 2:
        return None

    ankle_y_range = max(ankle_y_values) - min(ankle_y_values)

    # 计算平均肩到踝距离（判断身高）
    heights: list[float] = []
    for kpts in valid_frames:
        if kpts.shape[0] > max(LEFT_SHOULDER, LEFT_ANKLE):
            shoulder_y = float(kpts[LEFT_SHOULDER, 1])
            ankle_y = float(kpts[LEFT_ANKLE, 1])
            heights.append(abs(ankle_y - shoulder_y))

    avg_height = float(np.mean(heights)) if heights else 0.0

    # 启发式规则
    if avg_height < 80:  # 身体很小，可能还在俯卧/翻身阶段
        return 3
    elif ankle_y_range < 20:  # 脚踝几乎不动，可能是静态站立或匍匐
        if avg_height < 150:
            return 9  # 匍匐/爬行
        return 12  # 静态站立
    elif ankle_y_range < 50:  # 小幅波动，可能刚开始学步
        return 15
    else:  # 明显步态
        if avg_height > 250:
            return 30  # 较大儿童，可能已会跑跳
        return 18


def compute_symmetry_score(kpts: np.ndarray) -> float:
    """计算综合对称性评分（0-100，100 为完全对称）。

    基于肩高差、骨盆倾斜、膝角度差计算归一化分数。
    """
    if kpts.size == 0 or kpts.ndim != 2:
        return 0.0

    score = 100.0

    # 肩高差惩罚（每 1px 扣 0.5 分，最多 20 分）
    if _check_confidence(kpts, [LEFT_SHOULDER, RIGHT_SHOULDER]):
        shoulder_diff = abs(float(kpts[LEFT_SHOULDER, 1] - kpts[RIGHT_SHOULDER, 1]))
        score -= min(shoulder_diff * 0.5, 20.0)

    # 骨盆倾斜惩罚（每 1px 扣 0.5 分，最多 20 分）
    if _check_confidence(kpts, [LEFT_HIP, RIGHT_HIP]):
        hip_diff = abs(float(kpts[LEFT_HIP, 1] - kpts[RIGHT_HIP, 1]))
        score -= min(hip_diff * 0.5, 20.0)

    # 膝角度差惩罚（每 1° 扣 0.5 分，最多 20 分）
    angles = compute_joint_angles(kpts)
    left_knee = angles.get("left_knee", float(np.nan))
    right_knee = angles.get("right_knee", float(np.nan))
    if not np.isnan(left_knee) and not np.isnan(right_knee):
        knee_diff = abs(left_knee - right_knee)
        score -= min(knee_diff * 0.5, 20.0)

    # 脊柱倾角惩罚（每 1° 扣 1 分，最多 20 分）
    spine_tilt = angles.get("spine_tilt", float(np.nan))
    if not np.isnan(spine_tilt):
        score -= min(spine_tilt * 1.0, 20.0)

    return max(0.0, score)


def compute_kyphosis_angle(kpts: np.ndarray) -> float:
    """计算驼背角度（胸椎后凸角度，度数）。

    使用肩中点到鼻子的向量与垂直线的夹角。
    正值表示驼背（胸椎后凸），0° 表示直立。
    """
    if kpts.size == 0 or kpts.ndim != 2:
        return float(np.nan)

    if not _check_confidence(kpts, [LEFT_SHOULDER, RIGHT_SHOULDER, NOSE]):
        return float(np.nan)

    shoulder_mid = (kpts[LEFT_SHOULDER, :2] + kpts[RIGHT_SHOULDER, :2]) / 2
    neck_vec = kpts[NOSE, :2] - shoulder_mid
    vertical = np.array([0.0, -1.0])  # 向上

    raw_angle = angle_between(neck_vec, vertical)
    # 取最小夹角，限制在 0-90°
    return min(raw_angle, 180.0 - raw_angle)

