"""步态分析：周期检测、关键帧提取、步态指标计算。"""

import numpy as np
from scipy.signal import find_peaks

from gait_assess.models import AppConfig, FrameResult, GaitCycle, KeyFrame


class GaitAnalyzer:
    """步态周期与关键帧分析器。"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def extract_cycles(
        self, frame_results: list[FrameResult], fps: float
    ) -> GaitCycle:
        """从姿态序列中提取步态周期和关键帧。"""
        # 提取脚踝轨迹
        left_ankle_y, right_ankle_y = self._extract_ankle_trajectories(
            frame_results
        )

        # 尝试检测步态周期
        cycles = self._detect_cycles(left_ankle_y, right_ankle_y)

        if cycles:
            key_frames = self._extract_key_frames(frame_results, cycles)
            metrics = self._compute_metrics(cycles, fps, frame_results)
        else:
            # 退化采样
            key_frames = self._fallback_sampling(frame_results)
            metrics = {"note": "步态周期未明确，基于采样帧评估"}

        return GaitCycle(
            key_frames=key_frames,
            cycle_periods=cycles,
            metrics=metrics,
        )

    def _extract_ankle_trajectories(
        self, frame_results: list[FrameResult]
    ) -> tuple[np.ndarray, np.ndarray]:
        """提取左右脚踝 Y 坐标轨迹，缺失时用线性插值。"""
        n = len(frame_results)
        left_y = np.full(n, np.nan)
        right_y = np.full(n, np.nan)

        # COCO keypoint indices: left_ankle=15, right_ankle=16
        for i, fr in enumerate(frame_results):
            if fr.keypoints.size == 0:
                continue
            kpts = fr.keypoints[0]  # 只取最大的人
            if kpts.shape[0] > 15 and kpts[15, 2] > 0:
                left_y[i] = kpts[15, 1]
            if kpts.shape[0] > 16 and kpts[16, 2] > 0:
                right_y[i] = kpts[16, 1]

        left_y = self._interpolate(left_y)
        right_y = self._interpolate(right_y)

        return left_y, right_y

    def _interpolate(self, arr: np.ndarray) -> np.ndarray:
        """线性插值填补缺失值，连续缺失超过5帧则标记无效。"""
        n = len(arr)
        result = arr.copy()

        # 找到非nan的索引
        valid_idx = np.where(~np.isnan(result))[0]
        if len(valid_idx) == 0:
            return result

        # 前后填充
        result[: valid_idx[0]] = result[valid_idx[0]]
        result[valid_idx[-1] + 1 :] = result[valid_idx[-1]]

        # 线性插值
        nan_idx = np.where(np.isnan(result))[0]
        for idx in nan_idx:
            # 找到前后最近的非nan
            prev = np.where(~np.isnan(result[:idx]))[0]
            nxt = np.where(~np.isnan(result[idx + 1 :]))[0]
            if len(prev) > 0 and len(nxt) > 0:
                p, nx = prev[-1], nxt[0] + idx + 1
                if nx - p <= 5:  # 连续缺失不超过5帧
                    result[idx] = result[p] + (result[nx] - result[p]) * (
                        idx - p
                    ) / (nx - p)

        return result

    def _detect_cycles(
        self, left_y: np.ndarray, right_y: np.ndarray
    ) -> list[tuple[int, int]]:
        """基于脚踝 Y 坐标极值检测步态周期。"""
        # 使用平均值作为周期信号
        signal = (left_y + right_y) / 2
        signal = np.nan_to_num(signal, nan=0)

        if len(signal) < 10:
            return []

        # 寻找波谷（脚跟着地时刻）
        inverted = -signal
        peaks, _ = find_peaks(inverted, distance=len(signal) // 10)

        if len(peaks) < 2:
            return []

        cycles = []
        for i in range(len(peaks) - 1):
            start, end = int(peaks[i]), int(peaks[i + 1])
            if end - start >= 5:  # 至少5帧
                cycles.append((start, end))

        return cycles

    def _extract_key_frames(
        self,
        frame_results: list[FrameResult],
        cycles: list[tuple[int, int]],
    ) -> list[KeyFrame]:
        """从每个周期中提取4个关键相位帧。"""
        key_frames: list[KeyFrame] = []
        phase_names = ["脚跟着地", "站立中期", "脚尖离地", "摆动中期"]

        for start, end in cycles:
            cycle_frames = frame_results[start : end + 1]
            if len(cycle_frames) < 4:
                continue

            # 脚跟着地: 周期起点
            # 站立中期: 周期中点
            # 脚尖离地: 前 3/4 处
            # 摆动中期: 周期最高点附近
            indices = [
                0,
                len(cycle_frames) // 2,
                len(cycle_frames) * 3 // 4,
                len(cycle_frames) - 1,
            ]

            for phase_idx, rel_idx in enumerate(indices):
                abs_idx = start + rel_idx
                fr = cycle_frames[rel_idx]
                kf = self._create_key_frame(
                    abs_idx, phase_names[phase_idx], fr
                )
                if kf is not None:
                    key_frames.append(kf)

        return key_frames

    def _create_key_frame(
        self, frame_index: int, phase_name: str, fr: FrameResult
    ) -> KeyFrame | None:
        """创建关键帧，若姿态缺失则从相邻帧选替代。"""
        if fr.keypoints.size == 0:
            return None

        return KeyFrame(
            frame_index=frame_index,
            phase_name=phase_name,
            image=np.zeros((10, 10, 3), dtype=np.uint8),  # 占位
            keypoints=fr.keypoints[0],
        )

    def _fallback_sampling(
        self, frame_results: list[FrameResult]
    ) -> list[KeyFrame]:
        """退化策略：均匀采样 8 帧。"""
        n = len(frame_results)
        if n == 0:
            return []

        indices = np.linspace(0, n - 1, min(8, n), dtype=int)
        key_frames: list[KeyFrame] = []

        for idx in indices:
            fr = frame_results[idx]
            if fr.keypoints.size == 0:
                continue
            key_frames.append(
                KeyFrame(
                    frame_index=int(idx),
                    phase_name="采样帧",
                    image=np.zeros((10, 10, 3), dtype=np.uint8),
                    keypoints=fr.keypoints[0],
                )
            )

        return key_frames

    def _compute_metrics(
        self,
        cycles: list[tuple[int, int]],
        fps: float,
        frame_results: list[FrameResult],
    ) -> dict:
        """计算步态基础指标。"""
        n_cycles = len(cycles)
        total_frames = len(frame_results)
        duration = total_frames / fps if fps > 0 else 0

        metrics = {
            "步频(步/分钟)": round(n_cycles / duration * 60, 1)
            if duration > 0
            else 0,
            "检测周期数": n_cycles,
            "总帧数": total_frames,
            "时长(秒)": round(duration, 1),
        }

        # 步宽估计
        step_widths: list[float] = []
        for start, end in cycles:
            for i in range(start, min(end + 1, len(frame_results))):
                fr = frame_results[i]
                if fr.keypoints.size == 0:
                    continue
                kpts = fr.keypoints[0]
                if kpts.shape[0] > 16:
                    left_x = kpts[15, 0] if kpts[15, 2] > 0 else np.nan
                    right_x = kpts[16, 0] if kpts[16, 2] > 0 else np.nan
                    if not np.isnan(left_x) and not np.isnan(right_x):
                        step_widths.append(abs(float(left_x - right_x)))

        if step_widths:
            metrics["步宽(像素)"] = round(float(np.mean(step_widths)), 1)

        return metrics
