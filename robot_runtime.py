import asyncio
import json
import os
import threading
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class RobotConfig:
    LOG_NAME: str
    LOG_LEVEL: str
    MIC_INDEX: int
    SPEAKER_INDEX: int
    SAMPLE_RATE: int
    CHUNK: int
    CH_EYE_L_LR: int
    CH_LID_L: int
    CH_LID_R: int
    CH_EYE_R_LR: int
    CH_EYES_UD: int
    CH_JAW: int
    CH_FACE_PITCH: int
    CH_FACE_YAW: int
    CH_HEAD_TILT: int
    CH_YAW: int
    CH_TILT: int
    TRACK_X_SIGN: float
    TRACK_Y_SIGN: float
    HEAD_TRACK_X_SIGN: float
    HEAD_TRACK_Y_SIGN: float
    HEAD_TRACK_GAIN_X: float
    HEAD_TRACK_GAIN_Y: float
    HEAD_TRACK_DEADZONE_X: float
    HEAD_TRACK_DEADZONE_Y: float
    HEAD_TRACK_SETTLE_X: float
    HEAD_TRACK_SETTLE_Y: float
    HEAD_TRACK_EDGE_SOFTEN_X: float
    HEAD_TRACK_EDGE_SOFTEN_Y: float
    TRACK_CENTER_HOLD_X: float
    TRACK_CENTER_HOLD_Y: float
    TRACK_TARGET_SMOOTHING: float
    TRACK_MOTION_SMOOTHING: float
    TRACK_TARGET_HOLD_S: float
    TRACK_FACE_PRIORITY_HOLD_S: float
    PRIMARY_FACE_LOCK_S: float
    PRIMARY_FACE_MATCH_NORM: float
    FACE_ROI_EXPAND: float
    FACE_ROI_MIN_SIZE: int
    FACE_DETECTION_CONFIDENCE: float
    PERSON_DETECTION_STRIDE: int
    PERSON_DETECTION_WEIGHT_MIN: float
    EYE_FIRST_HEAD_DELAY_S: float
    REACQUIRE_START_S: float
    REACQUIRE_SWEEP_S: float
    REACQUIRE_SWEEP_X: int
    REACQUIRE_SWEEP_Y: int
    TRACK_PREDICTION_S: float
    TRACK_PREDICTION_MAX_X: float
    TRACK_PREDICTION_MAX_Y: float
    LIGHT_LOW_MEAN: float
    LIGHT_HIGH_MEAN: float
    LIMIT_WARN_RATIO: float
    HEAD_TRACK_SPEED_MIN: int
    HEAD_TRACK_SPEED_MAX: int
    HEAD_TRACK_ACCEL_MIN: int
    HEAD_TRACK_ACCEL_MAX: int
    HEAD_TRACK_STEP_X: int
    HEAD_TRACK_STEP_Y: int
    JAW_RMS_THRESHOLD: float
    COMMAND_TRACKING_PAUSE_S: float
    TRACKING_LOST_HOLD_S: float
    CAMERA_CAPTURE_SIZE: tuple
    CAMERA_DISPLAY_SIZE: tuple
    MODEL_FRAME_MAX_SIZE: tuple
    MODEL_JPEG_QUALITY: int
    MODEL_FRAME_INTERVAL_S: float
    OCR_COMMAND: str
    OCR_LANG: str
    OCR_PSM: int
    OCR_DOCUMENT_PSM: int
    OCR_TIMEOUT_S: float
    OCR_DOCUMENT_CROP_RATIO: float


@dataclass
class RobotRuntime:
    config: RobotConfig
    logger: object
    CAMERA_AVAILABLE: bool
    MEDIAPIPE_AVAILABLE: bool
    cv2: object = None
    mp: object = None
    np: object = None
    Picamera2: object = None
    CALIBRATION_PATH: str = ""
    MEMORY_PATH: str = ""
    JAW_CLOSED: int = 1500
    JAW_OPEN_MAX: int = 1750
    LID_L_OPEN: int = 1750
    LID_L_CLOSED: int = 1500
    LID_R_OPEN: int = 1500
    LID_R_CLOSED: int = 1735
    EYE_CENTER: int = 1500
    EYE_R_TRIM: int = 0
    EYE_R_INVERT: bool = False
    EYE_LR_MIN: int = 1280
    EYE_LR_MAX: int = 1720
    EYE_UD_MIN: int = 1360
    EYE_UD_MAX: int = 1760
    HEAD_NEUTRAL: dict = field(default_factory=lambda: {"yaw": 1500, "pitch": 1500, "tilt": 1500})
    HEAD_YAW_MIN: int = 1260
    HEAD_YAW_MAX: int = 1840
    HEAD_PITCH_MIN: int = 1280
    HEAD_PITCH_MAX: int = 1700
    HEAD_TILT_MIN: int = 1320
    HEAD_TILT_MAX: int = 1680
    is_ivan_talking: bool = False
    control_mode: str = "command"
    audio_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=30))
    tracking_enabled: bool = False
    command_enabled: bool = True
    tracked_lr: int = 0
    tracked_ud: int = 0
    tracked_head_yaw: int = 0
    tracked_head_pitch: int = 0
    last_tracking_update: float = 0.0
    tracking_head_enable_at: float = 0.0
    tracking_state: str = "idle"
    tracked_target_kind: str = ""
    tracking_confidence: float = 0.0
    last_seen_x_norm: float = 0.0
    last_seen_y_norm: float = 0.0
    last_target_norm_x: float = 0.0
    last_target_norm_y: float = 0.0
    last_target_velocity_x: float = 0.0
    last_target_velocity_y: float = 0.0
    shutdown_requested: bool = False
    last_tts_audio_ts: float = 0.0
    tracking_resume_at: float = 0.0
    eye_manual_until: float = 0.0
    gaze_hold_enabled: bool = False
    gaze_hold_lr: int = 0
    gaze_hold_ud: int = 0
    head_override_until: float = 0.0
    head_override_pose: dict = field(default_factory=lambda: {"yaw": 1500, "pitch": 1500, "tilt": 1500})
    head_target_pose: dict = field(default_factory=lambda: {"yaw": 1500, "pitch": 1500, "tilt": 1500})
    head_current_pose: dict = field(default_factory=lambda: {"yaw": 1500, "pitch": 1500, "tilt": 1500})
    latest_transcription: str = ""
    latest_transcription_at: float = 0.0
    session_memory: dict = field(default_factory=lambda: {"name": None, "likes": [], "facts": []})
    memory_lock: threading.Lock = field(default_factory=threading.Lock)
    MIC_CHANNELS: int = 1
    SPEAKER_CHANNELS: int = 1
    maestro: object = None
    latest_camera_frame: object = None
    ocr_available: bool = False

    def __getattr__(self, name):
        return getattr(self.config, name)


def load_robot_config(config_path, default_config):
    config_values = asdict(default_config)
    if not os.path.exists(config_path):
        return default_config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"Config load warning: {e}")
        return default_config

    if not isinstance(payload, dict):
        print("Config load warning: expected a JSON object at the root.")
        return default_config

    for key, value in payload.items():
        if key not in config_values:
            continue
        if key in {"CAMERA_CAPTURE_SIZE", "CAMERA_DISPLAY_SIZE", "MODEL_FRAME_MAX_SIZE"} and isinstance(value, list):
            value = tuple(value)
        config_values[key] = value

    return RobotConfig(**config_values)
