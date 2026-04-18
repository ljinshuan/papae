## ADDED Requirements

### Requirement: Per-frame JSON data generation
The system SHALL generate a `per-frame.json` file containing per-frame detection data for all processed frames.

#### Scenario: Successful data generation
- **WHEN** the pipeline completes video processing
- **THEN** the output directory SHALL contain a `per-frame.json` with fields: `fps`, `frame_count`, `width`, `height`, and a `frames` array where each element contains `frame_index`, `bbox`, `bbox_label`, `keypoints`, and `mask`

#### Scenario: Empty detection frame
- **WHEN** a frame has no detected person
- **THEN** that frame's entry SHALL have an empty `bbox` array and `null` for `keypoints` and `mask`

### Requirement: Interactive viewer HTML generation
The system SHALL generate a `viewer.html` file that provides an interactive 2×2 panel viewer.

#### Scenario: Viewer loads successfully
- **WHEN** a user opens `viewer.html` in a supported browser
- **THEN** the page SHALL display four panels arranged in a 2×2 grid

#### Scenario: Raw video panel
- **WHEN** the viewer is playing
- **THEN** the top-left panel SHALL display the original video frame without any overlays

#### Scenario: BBOX detection panel
- **WHEN** the viewer is playing and detection data exists for the current frame
- **THEN** the top-right panel SHALL display the original frame with a bounding box rectangle around the detected person and a coordinate label at the top-left corner of the box

#### Scenario: BBOX follows person movement
- **WHEN** the bounding box coordinates change between frames
- **THEN** the rectangle and label SHALL update position to match the new coordinates

#### Scenario: Segment highlighter panel
- **WHEN** the viewer is playing and segment mask data exists for the current frame
- **THEN** the bottom-left panel SHALL display the original frame with the person's segment mask overlaid with a semi-transparent purple highlight

#### Scenario: Pose crop panel
- **WHEN** the viewer is playing and detection data exists for the current frame
- **THEN** the bottom-right panel SHALL display the video cropped to the bounding box area with pose skeleton keypoints and connections drawn at 1:1 scale relative to the original person

#### Scenario: Missing detection fallback
- **WHEN** the current frame has no detection data
- **THEN** panels 2, 3, and 4 SHALL display "未检测到人物" text, and panel 1 SHALL continue playing normally

#### Scenario: Missing mask fallback
- **WHEN** the current frame has detection data but no segment mask
- **THEN** the segment panel SHALL display only the bounding box (same as panel 2)

### Requirement: Playback controls
The viewer SHALL provide playback control UI.

#### Scenario: Play and pause
- **WHEN** the user clicks the play/pause button
- **THEN** the video SHALL toggle between playing and paused states, and all four panels SHALL update synchronously

#### Scenario: Frame stepping
- **WHEN** the user clicks the forward or backward frame button
- **THEN** the video SHALL advance or retreat by exactly one frame, and all panels SHALL update

#### Scenario: Speed selection
- **WHEN** the user selects a playback speed (0.5x, 1x, or 2x)
- **THEN** the video playback rate SHALL update to the selected speed

#### Scenario: Progress scrubbing
- **WHEN** the user drags the progress bar
- **THEN** the video SHALL seek to the corresponding time, and all panels SHALL update to the new frame

### Requirement: Synchronized panel rendering
All four panels SHALL render frames synchronously from a single video time source.

#### Scenario: Frame sync on playback
- **WHEN** the video is playing
- **THEN** all four panels SHALL display the same frame index, calculated from the shared video element's `currentTime`

### Requirement: Output coexistence
The system SHALL retain existing outputs alongside the new viewer artifacts.

#### Scenario: Full pipeline output
- **WHEN** the pipeline completes
- **THEN** the output directory SHALL contain both the existing `annotated_video.mp4` and `report.md`, AND the new `viewer.html` and `per-frame.json`
