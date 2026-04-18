## 1. Backend: Per-frame JSON generation

- [ ] 1.1 Add `generate_viewer_data()` to `visualizer.py` that serializes `frame_results` to `per-frame.json`
- [ ] 1.2 Define the JSON schema: `fps`, `frame_count`, `width`, `height`, `frames[]` with `frame_index`, `bbox`, `bbox_label`, `keypoints`, `mask` (base64 PNG)
- [ ] 1.3 Handle edge cases: empty detection → empty bbox + null keypoints/mask; null mask → panel 3 falls back to bbox only
- [ ] 1.4 Write unit tests for `generate_viewer_data()` verifying JSON structure and edge cases

## 2. Frontend: viewer.html

- [ ] 2.1 Create `viewer.html` with Vue 3 CDN via importmap
- [ ] 2.2 Implement hidden `<video>` element as shared time source
- [ ] 2.3 Implement `PlayerControls` component: play/pause, frame step forward/backward, speed selector (0.5x/1x/2x), progress bar
- [ ] 2.4 Implement `VideoPanel` component with 4 mode variants: raw, bbox, segment, pose_crop
- [ ] 2.5 Panel 1 (raw): draw original frame to Canvas
- [ ] 2.6 Panel 2 (bbox): draw frame + strokeRect + fillText label at top-left of bbox
- [ ] 2.7 Panel 3 (segment): draw frame + overlay base64 mask as semi-transparent purple
- [ ] 2.8 Panel 4 (pose_crop): drawImage cropped to bbox + skeleton keypoints and COCO connections offset by bbox origin
- [ ] 2.9 Implement `requestAnimationFrame` sync loop: calculate `currentFrame` from `video.currentTime`, redraw all panels only on frame change
- [ ] 2.10 Handle missing detection: panels 2/3/4 display "未检测到人物"
- [ ] 2.11 Handle missing mask: panel 3 falls back to bbox-only display
- [ ] 2.12 Load `per-frame.json` via fetch and render error state on failure

## 3. Pipeline integration

- [ ] 3.1 Update `cli.py` orchestration to call `generate_viewer_data()` after existing visualization
- [ ] 3.2 Ensure `viewer.html` is copied/available in output directory alongside `per-frame.json`
- [ ] 3.3 Verify output directory contains: `report.md`, `annotated_video.mp4`, `viewer.html`, `per-frame.json`

## 4. Testing and verification

- [ ] 4.1 Run backend unit tests for `generate_viewer_data()` — all pass
- [ ] 4.2 Manually test `viewer.html` in Chrome: verify play/pause, frame stepping, speed change, progress scrubbing
- [ ] 4.3 Verify 4 panels render correctly and stay synchronized during playback
- [ ] 4.4 Run full pipeline end-to-end and confirm all output files are generated
- [ ] 4.5 Run `uv run basedpyright src/` — no new type errors
- [ ] 4.6 Run `uv run pytest` — all tests pass
