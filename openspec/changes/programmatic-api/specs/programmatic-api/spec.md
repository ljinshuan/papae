## ADDED Requirements

### Requirement: Public API module
The system SHALL provide a public `api.py` module that exposes a high-level `assess()` function to run the complete assessment pipeline programmatically.

#### Scenario: Import and call assess()
- **WHEN** a user executes `from gait_assess import assess`
- **AND** calls `assess(video_path, config)`
- **THEN** the system SHALL execute the full pipeline (preprocess → detect → analyze → assess → visualize → report)
- **AND** return a `dict` containing all output paths and structured results

#### Scenario: Mode-specific assessment
- **WHEN** a user calls `assess_gait(video_path, config)`
- **THEN** the system SHALL set `config.assessment_mode = "gait"` and run the pipeline
- **AND** return gait-specific results

#### Scenario: Developmental assessment
- **WHEN** a user calls `assess_developmental(video_path, config)`
- **THEN** the system SHALL set `config.assessment_mode = "developmental"` and run the pipeline
- **AND** auto-infer age from pose if `config.child_age_months` is not set

#### Scenario: Posture assessment
- **WHEN** a user calls `assess_posture(video_path, config)`
- **THEN** the system SHALL set `config.assessment_mode = "posture"` and run the pipeline

### Requirement: Public component classes
The system SHALL expose all core component classes through `gait_assess` package imports.

#### Scenario: Direct component usage
- **WHEN** a user executes `from gait_assess import VideoPreprocessor, PoseSegmentor, GaitAnalyzer, LLMAssessor`
- **THEN** all classes SHALL be importable and instantiable with an `AppConfig`

### Requirement: Package-level exports
The system SHALL update `__init__.py` to export all public symbols.

#### Scenario: Convenient imports
- **WHEN** a user executes `from gait_assess import assess, AppConfig, AssessmentResult`
- **THEN** all symbols SHALL be available without importing submodules

### Requirement: CLI delegates to API
The system SHALL refactor `cli.py` to delegate pipeline execution to `api.py`.

#### Scenario: CLI behavior unchanged
- **WHEN** a user runs `gait-assess --video ./baby.mp4`
- **THEN** the CLI SHALL parse arguments, construct `AppConfig`, and call `api.assess()`
- **AND** the output SHALL be identical to the previous implementation
