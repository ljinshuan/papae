# Infant Posture Assessment System

<p align="center">
  <img src="logo.png" alt="Infant Posture Assessment System Logo">
</p>

English | [中文](README.zh.md)

A command-line tool for infant posture assessment powered by YOLOv8-pose + YOLOv8-seg and a full-modal large language model (Qwen-VL).

Supports three assessment modes: gait analysis, motor development screening, and posture correction evaluation. Input a parent-recorded video of your baby, and the tool outputs a structured Markdown assessment report along with a visualized video overlaid with skeleton and segmentation masks.

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [User Guide](#user-guide)
  - [Assessment Modes](#assessment-modes)
  - [Recording Tips](#recording-tips)
  - [Understanding Your Report](#understanding-your-report)
- [Developer Guide](#developer-guide)
  - [Installation](#installation)
  - [Python API](#python-api)
  - [Output Files](#output-files)
  - [Architecture](#architecture)
  - [Project Structure](#project-structure)
  - [Development](#development)
- [Disclaimer](#disclaimer)
- [License](#license)

## Quick Start

Requires Python >= 3.13.

```bash
# Clone and install
uv sync --extra dev

# Quick assessment (default gait mode, requires LLM API key)
uv run gait-assess --video ./baby_walking.mp4 --output ./results/

# Try without API key — generates annotated video and report skeleton
uv run gait-assess --video ./baby_walking.mp4 --output ./results/ --skip-llm

# Motor development screening (requires age in months)
uv run gait-assess --video ./baby_walking.mp4 --mode developmental --age-months 12 --output ./results/

# Posture correction evaluation
uv run gait-assess --video ./baby_standing.mp4 --mode posture --output ./results/
```

### Environment Setup

LLM configurations are read from environment variables or a `.env` file:

```bash
cat > .env << 'EOF'
QWEN_API_KEY=your-api-key
GAIT_LLM_MODEL=qwen-vl-max
GAIT_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EOF
```

## Features

- **Three Assessment Modes**:
  - `gait` — Gait analysis: based on gait cycle detection, evaluates walking posture abnormalities
  - `developmental` — Motor development screening: matches motor milestones by age to screen for developmental delay risks
  - `posture` — Posture correction evaluation: analyzes spinal/shoulder/pelvic symmetry in static standing posture
- **Video Preprocessing**: automatic frame splitting, blur filtering, resolution standardization
- **Pose Detection**: YOLOv8-pose extracts 17 COCO keypoints
- **Human Segmentation**: YOLOv8-seg generates segmentation masks
- **Gait Analysis**: detects gait cycles based on ankle trajectory, extracts 4 key phase frames
- **Pose Computation**: knee angle, ankle angle, spinal tilt, pelvic tilt, shoulder height difference, etc.
- **LLM Assessment**: full-modal large model end-to-end evaluation with dual-channel input (video + structured pose data)
- **Visualized Output**: skeleton overlay, mask overlay, key frame marking
- **Interactive Viewer**: `viewer.html` with per-frame skeleton/segmentation playback and key frame gallery
- **Report Generation**: structured Markdown report with risk badges, finding cards, suggestion cards, and embedded key frame images

## User Guide

### Assessment Modes

#### `gait` — Gait Analysis (default)

Best for: babies who are already walking independently.

The tool detects gait cycles from ankle trajectories, extracts 4 key phase frames (heel strike, mid-stance, toe-off, mid-swing), computes joint angles and symmetry metrics, and feeds them to the LLM for a holistic assessment.

```bash
uv run gait-assess --video ./baby_walking.mp4 --mode gait --output ./results/
```

#### `developmental` — Motor Development Screening

Best for: screening developmental delays against age-appropriate motor milestones.

Requires `--age-months` (e.g., 12 for a 1-year-old). The LLM compares observed pose and movement patterns against standard milestones for that age group.

```bash
uv run gait-assess --video ./baby.mp4 --mode developmental --age-months 12 --output ./results/
```

#### `posture` — Posture Correction Evaluation

Best for: static standing posture analysis.

Focuses on spinal alignment, shoulder height symmetry, and pelvic tilt. The subject should stand still facing the camera for 3–5 seconds.

```bash
uv run gait-assess --video ./baby_standing.mp4 --mode posture --output ./results/
```

### Recording Tips

For the best assessment results, please follow these recording guidelines:

- **Lighting**: choose a well-lit, evenly-lit environment; avoid backlight or strong shadows
- **Distance**: place the phone/camera 2–3 meters from the baby, ensuring the whole body is in frame
- **Angle**: camera height level with the baby's waist; a frontal or side view works best
- **Background**: choose a simple background; avoid multiple people in the frame
- **Duration**: record at least 5–10 seconds of continuous walking, with the baby taking 3–5+ steps
- **Clothing**: avoid overly loose clothing; short sleeves/shorts are recommended for clear limb visibility

### Understanding Your Report

The generated `report.md` contains three main sections:

**Risk Badge** — A color-coded indicator at the top:
- 🟢 **Normal** — No significant concerns detected
- 🟡 **Mild** — Minor deviations, monitor and re-assess in 2–4 weeks
- 🟠 **Moderate** — Notable findings, consider a pediatric consultation
- 🔴 **Severe** — Significant concerns, seek professional evaluation promptly

**Findings** — Specific observations from the video and pose analysis, such as asymmetrical arm swing, knee valgus/varus, or delayed heel strike.

**Suggestions** — Actionable recommendations tailored to the findings, such as targeted exercises, activity suggestions, or follow-up timelines.

> ⚠️ This tool is for reference only and does not constitute a medical diagnosis. If you have any concerns, please consult a professional pediatrician or rehabilitation therapist.

## Developer Guide

### Installation

```bash
# Install dependencies (including dev)
uv sync --extra dev

# Or install into the current environment
uv pip install -e ".[dev]"
```

YOLO model weights (`.pt` files) are stored in the `models/` directory. They are downloaded automatically from Ultralytics Hub on first run (internet connection required). You can also download them manually and place them in `models/`.

### Python API

In addition to the CLI, you can directly invoke the assessment pipeline in Python code.

#### Basic Usage

```python
from pathlib import Path
from gait_assess import assess, AppConfig

config = AppConfig(
    video=Path("./baby.mp4"),
    output=Path("./results"),
    llm_api_key="your-api-key",
)

result = assess("./baby.mp4", config)

print(result["report_path"])       # Path('.../report.md')
print(result["video_path"])        # Path('.../annotated_video.mp4')
print(result["assessment"].risk_level)  # "正常"
```

#### Mode-Specific Functions

```python
from gait_assess import assess_gait, assess_developmental, assess_posture

# Gait assessment
gait_result = assess_gait("./baby.mp4", config)

# Motor development screening (age_months can be omitted, inferred from pose)
dev_result = assess_developmental("./baby.mp4", config)

# Posture correction evaluation
posture_result = assess_posture("./baby.mp4", config)
```

#### Return Fields

`assess()` and mode-specific functions return a dictionary containing the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `report_path` | `Path` | Markdown assessment report file path |
| `video_path` | `Path` | Annotated visualization video path |
| `viewer_video_path` | `Path` | Interactive viewer video path |
| `viewer_data_path` | `Path` | Per-frame JSON data path |
| `viewer_html_path` | `Path \| None` | viewer.html path |
| `assessment` | `AssessmentResult` | LLM assessment result (risk level, findings, suggestions) |
| `gait_cycle` | `GaitCycle` | Gait cycle analysis result |
| `config` | `AppConfig` | Runtime configuration object |
| `frames` | `list[np.ndarray]` | Preprocessed frame list |
| `fps` | `float` | Video frame rate |
| `frame_results` | `list[FrameResult]` | Per-frame pose detection/segmentation results |

#### Skip LLM (Offline Assessment)

```python
result = assess("./baby.mp4", config, skip_llm=True)
# assessment.risk_level == "未知"
```

#### Error Handling

```python
from gait_assess.api import AssessmentError

try:
    result = assess("./baby.mp4", config)
except AssessmentError as e:
    print(f"Stage: {e.stage}")    # "preprocess" / "llm"
    print(f"Reason: {e.original}") # Original exception
```

### Output Files

```
results/
├── report.md              # Markdown assessment report (with risk badges, finding/suggestion cards)
├── annotated_video.mp4    # Annotated visualization video
├── viewer.html            # Interactive report viewer (per-frame playback + key frame gallery)
└── key_frames/
    ├── frame_00.jpg       # Key phase frame images
    ├── frame_01.jpg
    ├── frame_02.jpg
    └── frame_03.jpg
```

The `viewer.html` file provides an interactive experience:
- Per-frame playback with skeleton and segmentation overlay
- Key frame gallery with phase labels
- Risk level and finding/suggestion cards rendered with styled badges

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Data Pipeline                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Input Video                                                               │
│       │                                                                     │
│       ▼                                                                     │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│   │Preprocessor  │────▶│YOLOv8-pose   │────▶│YOLOv8-seg    │               │
│   │(frames, blur)│     │(17 keypoints)│     │(segmentation)│               │
│   └──────────────┘     └──────────────┘     └──────────────┘               │
│          │                      │                    │                      │
│          └──────────────────────┼────────────────────┘                      │
│                                 ▼                                           │
│                        ┌────────────────┐                                   │
│                        │  Pose Metrics  │                                   │
│                        │(angles, symmetry│                                  │
│                        │ temporal tracks) │                                 │
│                        └────────┬───────┘                                   │
│                                 │                                           │
│                    ┌────────────┴────────────┐                              │
│                    ▼                         ▼                              │
│           ┌──────────────┐          ┌─────────────────┐                     │
│           │Gait Analyzer │          │   LLM Assessor  │                     │
│           │(cycle detect,│          │(video + pose     │                     │
│           │ key frames)  │          │  data dual input)│                     │
│           └──────┬───────┘          └────────┬────────┘                     │
│                  │                            │                             │
│                  └────────────┬───────────────┘                             │
│                               ▼                                             │
│                    ┌────────────────────┐                                   │
│                    │  Report Generator  │                                   │
│                    │  + Visualizer      │                                   │
│                    └─────────┬──────────┘                                   │
│                              │                                              │
│                    ┌─────────┴──────────┐                                   │
│                    ▼                    ▼                                   │
│              report.md        annotated_video.mp4                           │
│              viewer.html                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Key design decisions:
- **Dual-channel LLM input**: The LLM receives both the full video (base64 encoded, preserving temporal continuity) and structured pose data text (key frame coordinates, joint angles, temporal metrics). Video provides context; pose data provides precise coordinates. Video is more token-efficient than 8 separate key frame images.
- **Jinja2 prompt templates**: Prompts are externalized as `prompts/*.jinja.md` files. Each assessment mode has its own template. Adding a new mode only requires a new template file — no code changes.
- **Infant-specific tuning**: YOLO confidence threshold lowered from 0.5 to 0.3 (infants have smaller body frames). Only the largest detected person is retained per frame.

### Project Structure

```
src/gait_assess/
  __init__.py          # Package entry
  api.py               # Programmatic API layer (assess() and mode-specific functions)
  cli.py               # CLI entry and pipeline orchestration
  models.py            # Pydantic data models
  preprocessor.py      # Video frame splitting, blur filtering, standardization
  pose_segmentor.py    # YOLO-pose + YOLO-seg inference
  gait_analyzer.py     # Gait cycle detection, key frame extraction
  pose_utils.py        # Joint angles, symmetry, temporal trajectory computation
  llm_assessor.py      # Full-modal LLM call, Jinja2 template rendering
  visualizer.py        # Skeleton/mask overlay, video encoding
  report_generator.py  # Markdown report generation
  prompts/             # Jinja2 prompt templates
    gait.jinja.md
    developmental.jinja.md
    posture.jinja.md
models/                # YOLO model weight files (*.pt, ignored by .gitignore)
tests/
  fixtures/            # Test videos
  test_*.py            # Unit tests for each module
```

### Development

```bash
# Use Makefile
make help      # Show all commands
make install   # Install dependencies
make test      # Run tests
make typecheck # Run static type check
make lint      # Run code lint check (ruff)
make e2e       # End-to-end validation (skip LLM)
make e2e-full  # End-to-end validation (with LLM, requires API key)
make viewer    # Run e2e and automatically open viewer.html
make clean     # Clean results

# Or run directly
uv run pytest
uv run basedpyright src/
```

### Full CLI Arguments

```bash
uv run gait-assess \
  --video ./baby_walking.mp4 \
  --output ./results/ \
  --mode gait \
  --age-months 12 \
  --conf-threshold 0.3 \
  --blur-threshold 100.0 \
  --target-height 720 \
  --min-duration 3.0 \
  --skip-llm
```

## Disclaimer

This tool is for reference only and does not constitute a medical diagnosis. Assessment results are based on computer vision and large language model analysis and may contain errors. If you have concerns about your baby's walking posture, please consult a professional pediatrician or rehabilitation therapist.

## License

MIT
