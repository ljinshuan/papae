"""生成合成测试视频，模拟人走路。"""

import cv2
import numpy as np


def generate_walking_video(
    output_path: str,
    duration: float = 5.0,
    fps: int = 30,
    width: int = 640,
    height: int = 480,
) -> None:
    """生成一段模拟人走路的合成视频。

    画面中有一个矩形在水平方向上左右移动，模拟走路的周期性运动。
    """
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[reportAttributeAccessIssue]
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = int(duration * fps)

    for frame_idx in range(total_frames):
        # 黑色背景
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # 周期运动：左右移动
        t = frame_idx / fps
        cycle_freq = 1.0  # 1 Hz，每秒一个周期
        x = int(width / 2 + 150 * np.sin(2 * np.pi * cycle_freq * t))
        y = int(height / 2)

        # 绘制模拟人体的矩形（身体）
        body_w, body_h = 40, 80
        cv2.rectangle(
            frame,
            (x - body_w // 2, y - body_h // 2),
            (x + body_w // 2, y + body_h // 2),
            (0, 255, 0),
            -1,
        )

        # 绘制头部
        head_radius = 20
        cv2.circle(frame, (x, y - body_h // 2 - head_radius), head_radius, (0, 200, 255), -1)

        # 绘制腿部（周期性摆动）
        leg_phase = np.sin(2 * np.pi * cycle_freq * t)
        left_leg_angle = leg_phase * 0.5
        right_leg_angle = -leg_phase * 0.5

        leg_length = 60
        leg_origin_y = y + body_h // 2

        # 左腿
        lx1 = int(x - 10)
        ly1 = leg_origin_y
        lx2 = int(lx1 + leg_length * np.sin(left_leg_angle))
        ly2 = int(ly1 + leg_length * np.cos(left_leg_angle))
        cv2.line(frame, (lx1, ly1), (lx2, ly2), (255, 0, 0), 4)

        # 右腿
        rx1 = int(x + 10)
        ry1 = leg_origin_y
        rx2 = int(rx1 + leg_length * np.sin(right_leg_angle))
        ry2 = int(ry1 + leg_length * np.cos(right_leg_angle))
        cv2.line(frame, (rx1, ry1), (rx2, ry2), (255, 0, 0), 4)

        writer.write(frame)

    writer.release()
    print(f"Generated: {output_path} ({total_frames} frames, {duration}s, {fps}fps)")


if __name__ == "__main__":
    generate_walking_video("test_walking.mp4")
