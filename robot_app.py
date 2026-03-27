import asyncio
import atexit
import os
import signal
import sys
import threading
import time
from ctypes import *

import numpy as np
import pyaudio
from google import genai

import robot_audio
import robot_camera
import robot_commands
from robot_logging import configure_logger, log_event
import robot_motion
import robot_ocr
from robot_session import handle_session_response
from robot_memory import (
    apply_memory_from_text as update_session_memory_from_text,
    load_session_memory as load_session_memory_file,
    save_session_memory as save_session_memory_file,
)
from robot_prompt import build_system_instruction as compose_system_instruction
from robot_runtime import RobotConfig, RobotRuntime, load_robot_config
from robot_tools import get_tool_declarations
# Allow venv to import Raspberry Pi system camera package
sys.path.append('/usr/lib/python3/dist-packages')

try:
    import cv2
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
except Exception:
    CAMERA_AVAILABLE = False

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except Exception:
    mp = None
    MEDIAPIPE_AVAILABLE = False

# --- HARDWARE CONFIG ---
os.environ["ALSA_CARD"] = "2"
os.environ.setdefault("JACK_NO_START_SERVER", "1")

MIC_INDEX = 1
SPEAKER_INDEX = 2
SAMPLE_RATE = 48000
CHUNK = 512

JAW_CLOSED = 1500
JAW_OPEN_MAX = 1750

# Eye channels
CH_EYE_L_LR = 1
CH_LID_L = 2
CH_LID_R = 3
CH_EYE_R_LR = 4
CH_EYES_UD = 5
CH_JAW = 6
CH_FACE_PITCH = 7
CH_FACE_YAW = 8
CH_HEAD_TILT = 9
SWAP_YAW_TILT = False

CH_YAW = CH_FACE_YAW
CH_TILT = CH_HEAD_TILT
if SWAP_YAW_TILT:
    CH_YAW, CH_TILT = CH_HEAD_TILT, CH_FACE_YAW

# Eyelid calibration (from your table)
LID_L_OPEN = 1750
LID_L_CLOSED = 1500
LID_R_OPEN = 1500
LID_R_CLOSED = 1735

# Eye center and trims
EYE_CENTER = 1500
EYE_R_TRIM = 0
EYE_R_INVERT = False
EYE_LR_MIN = 1280
EYE_LR_MAX = 1720
EYE_UD_MIN = 1360
EYE_UD_MAX = 1760

# Head calibration / motion
HEAD_NEUTRAL = {"yaw": 1500, "pitch": 1500, "tilt": 1500}
HEAD_YAW_MIN = 1260
HEAD_YAW_MAX = 1840
HEAD_PITCH_MIN = 1280
HEAD_PITCH_MAX = 1700
HEAD_TILT_MIN = 1320
HEAD_TILT_MAX = 1680
CALIBRATION_PATH = os.path.join(os.path.dirname(__file__), "ivan_servo_calibration.json")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "robot_config.json")
MEMORY_PATH = os.path.join(os.path.dirname(__file__), "ivan_session_memory.json")
# Camera mounted on head: positive screen X means target is right, so eyes should move right.
TRACK_X_SIGN = 1.0
TRACK_Y_SIGN = -1.0
# Head yaw: right turn is lower pulse (see servo_controller.py minright/maxleft).
HEAD_TRACK_X_SIGN = -1.0
HEAD_TRACK_Y_SIGN = -1.0
HEAD_TRACK_GAIN_X = 1.20
HEAD_TRACK_GAIN_Y = 1.46
HEAD_TRACK_DEADZONE_X = 0.08
HEAD_TRACK_DEADZONE_Y = 0.04
HEAD_TRACK_SETTLE_X = 0.10
HEAD_TRACK_SETTLE_Y = 0.08
HEAD_TRACK_EDGE_SOFTEN_X = 0.75
HEAD_TRACK_EDGE_SOFTEN_Y = 0.80
TRACK_CENTER_HOLD_X = 0.12
TRACK_CENTER_HOLD_Y = 0.07
TRACK_TARGET_SMOOTHING = 0.42
TRACK_MOTION_SMOOTHING = 0.28
TRACK_TARGET_HOLD_S = 0.8
TRACK_FACE_PRIORITY_HOLD_S = 1.0
PRIMARY_FACE_LOCK_S = 1.4
PRIMARY_FACE_MATCH_NORM = 0.18
FACE_ROI_EXPAND = 1.9
FACE_ROI_MIN_SIZE = 84
FACE_DETECTION_CONFIDENCE = 0.58
PERSON_DETECTION_STRIDE = 1
PERSON_DETECTION_WEIGHT_MIN = 0.15
EYE_FIRST_HEAD_DELAY_S = 0.18
REACQUIRE_START_S = 0.30
REACQUIRE_SWEEP_S = 3.4
REACQUIRE_SWEEP_X = 220
REACQUIRE_SWEEP_Y = 95
TRACK_PREDICTION_S = 0.10
TRACK_PREDICTION_MAX_X = 0.06
TRACK_PREDICTION_MAX_Y = 0.10
LIGHT_LOW_MEAN = 72.0
LIGHT_HIGH_MEAN = 182.0
LIMIT_WARN_RATIO = 0.90
HEAD_TRACK_SPEED_MIN = 18
HEAD_TRACK_SPEED_MAX = 75
HEAD_TRACK_ACCEL_MIN = 4
HEAD_TRACK_ACCEL_MAX = 12
HEAD_TRACK_STEP_X = 26
HEAD_TRACK_STEP_Y = 22
JAW_RMS_THRESHOLD = 120.0
COMMAND_TRACKING_PAUSE_S = 2.8
TRACKING_LOST_HOLD_S = 3.2
CAMERA_CAPTURE_SIZE = (800, 600)
CAMERA_DISPLAY_SIZE = (640, 480)
MODEL_FRAME_MAX_SIZE = (800, 600)
MODEL_JPEG_QUALITY = 72
MODEL_FRAME_INTERVAL_S = 0.45
OCR_COMMAND = os.environ.get("IVAN_OCR_COMMAND", "tesseract")
OCR_LANG = os.environ.get("IVAN_OCR_LANG", "eng")
OCR_PSM = 6
OCR_DOCUMENT_PSM = 6
OCR_TIMEOUT_S = 5.0
OCR_DOCUMENT_CROP_RATIO = 0.7
SPEECH_SELF_CAPTURE_GUARD_S = 1.8
FOLLOW_UP_WAIT_S = 5.0

DEFAULT_CONFIG = RobotConfig(
    LOG_NAME="ivan.robot",
    LOG_LEVEL=os.environ.get("IVAN_LOG_LEVEL", "INFO"),
    MIC_INDEX=MIC_INDEX,
    SPEAKER_INDEX=SPEAKER_INDEX,
    SAMPLE_RATE=SAMPLE_RATE,
    CHUNK=CHUNK,
    CH_EYE_L_LR=CH_EYE_L_LR,
    CH_LID_L=CH_LID_L,
    CH_LID_R=CH_LID_R,
    CH_EYE_R_LR=CH_EYE_R_LR,
    CH_EYES_UD=CH_EYES_UD,
    CH_JAW=CH_JAW,
    CH_FACE_PITCH=CH_FACE_PITCH,
    CH_FACE_YAW=CH_FACE_YAW,
    CH_HEAD_TILT=CH_HEAD_TILT,
    CH_YAW=CH_YAW,
    CH_TILT=CH_TILT,
    TRACK_X_SIGN=TRACK_X_SIGN,
    TRACK_Y_SIGN=TRACK_Y_SIGN,
    HEAD_TRACK_X_SIGN=HEAD_TRACK_X_SIGN,
    HEAD_TRACK_Y_SIGN=HEAD_TRACK_Y_SIGN,
    HEAD_TRACK_GAIN_X=HEAD_TRACK_GAIN_X,
    HEAD_TRACK_GAIN_Y=HEAD_TRACK_GAIN_Y,
    HEAD_TRACK_DEADZONE_X=HEAD_TRACK_DEADZONE_X,
    HEAD_TRACK_DEADZONE_Y=HEAD_TRACK_DEADZONE_Y,
    HEAD_TRACK_SETTLE_X=HEAD_TRACK_SETTLE_X,
    HEAD_TRACK_SETTLE_Y=HEAD_TRACK_SETTLE_Y,
    HEAD_TRACK_EDGE_SOFTEN_X=HEAD_TRACK_EDGE_SOFTEN_X,
    HEAD_TRACK_EDGE_SOFTEN_Y=HEAD_TRACK_EDGE_SOFTEN_Y,
    TRACK_CENTER_HOLD_X=TRACK_CENTER_HOLD_X,
    TRACK_CENTER_HOLD_Y=TRACK_CENTER_HOLD_Y,
    TRACK_TARGET_SMOOTHING=TRACK_TARGET_SMOOTHING,
    TRACK_MOTION_SMOOTHING=TRACK_MOTION_SMOOTHING,
    TRACK_TARGET_HOLD_S=TRACK_TARGET_HOLD_S,
    TRACK_FACE_PRIORITY_HOLD_S=TRACK_FACE_PRIORITY_HOLD_S,
    PRIMARY_FACE_LOCK_S=PRIMARY_FACE_LOCK_S,
    PRIMARY_FACE_MATCH_NORM=PRIMARY_FACE_MATCH_NORM,
    FACE_ROI_EXPAND=FACE_ROI_EXPAND,
    FACE_ROI_MIN_SIZE=FACE_ROI_MIN_SIZE,
    FACE_DETECTION_CONFIDENCE=FACE_DETECTION_CONFIDENCE,
    PERSON_DETECTION_STRIDE=PERSON_DETECTION_STRIDE,
    PERSON_DETECTION_WEIGHT_MIN=PERSON_DETECTION_WEIGHT_MIN,
    EYE_FIRST_HEAD_DELAY_S=EYE_FIRST_HEAD_DELAY_S,
    REACQUIRE_START_S=REACQUIRE_START_S,
    REACQUIRE_SWEEP_S=REACQUIRE_SWEEP_S,
    REACQUIRE_SWEEP_X=REACQUIRE_SWEEP_X,
    REACQUIRE_SWEEP_Y=REACQUIRE_SWEEP_Y,
    TRACK_PREDICTION_S=TRACK_PREDICTION_S,
    TRACK_PREDICTION_MAX_X=TRACK_PREDICTION_MAX_X,
    TRACK_PREDICTION_MAX_Y=TRACK_PREDICTION_MAX_Y,
    LIGHT_LOW_MEAN=LIGHT_LOW_MEAN,
    LIGHT_HIGH_MEAN=LIGHT_HIGH_MEAN,
    LIMIT_WARN_RATIO=LIMIT_WARN_RATIO,
    HEAD_TRACK_SPEED_MIN=HEAD_TRACK_SPEED_MIN,
    HEAD_TRACK_SPEED_MAX=HEAD_TRACK_SPEED_MAX,
    HEAD_TRACK_ACCEL_MIN=HEAD_TRACK_ACCEL_MIN,
    HEAD_TRACK_ACCEL_MAX=HEAD_TRACK_ACCEL_MAX,
    HEAD_TRACK_STEP_X=HEAD_TRACK_STEP_X,
    HEAD_TRACK_STEP_Y=HEAD_TRACK_STEP_Y,
    JAW_RMS_THRESHOLD=JAW_RMS_THRESHOLD,
    COMMAND_TRACKING_PAUSE_S=COMMAND_TRACKING_PAUSE_S,
    TRACKING_LOST_HOLD_S=TRACKING_LOST_HOLD_S,
    CAMERA_CAPTURE_SIZE=CAMERA_CAPTURE_SIZE,
    CAMERA_DISPLAY_SIZE=CAMERA_DISPLAY_SIZE,
    MODEL_FRAME_MAX_SIZE=MODEL_FRAME_MAX_SIZE,
    MODEL_JPEG_QUALITY=MODEL_JPEG_QUALITY,
    MODEL_FRAME_INTERVAL_S=MODEL_FRAME_INTERVAL_S,
    OCR_COMMAND=OCR_COMMAND,
    OCR_LANG=OCR_LANG,
    OCR_PSM=OCR_PSM,
    OCR_DOCUMENT_PSM=OCR_DOCUMENT_PSM,
    OCR_TIMEOUT_S=OCR_TIMEOUT_S,
    OCR_DOCUMENT_CROP_RATIO=OCR_DOCUMENT_CROP_RATIO,
    SPEECH_SELF_CAPTURE_GUARD_S=SPEECH_SELF_CAPTURE_GUARD_S,
    FOLLOW_UP_WAIT_S=FOLLOW_UP_WAIT_S,
)
CONFIG = load_robot_config(CONFIG_PATH, DEFAULT_CONFIG)

runtime = RobotRuntime(
    config=CONFIG,
    logger=configure_logger(CONFIG.LOG_NAME, CONFIG.LOG_LEVEL),
    CAMERA_AVAILABLE=CAMERA_AVAILABLE,
    MEDIAPIPE_AVAILABLE=MEDIAPIPE_AVAILABLE,
    cv2=cv2 if CAMERA_AVAILABLE else None,
    mp=mp,
    np=np,
    Picamera2=Picamera2 if CAMERA_AVAILABLE else None,
    CALIBRATION_PATH=CALIBRATION_PATH,
    MEMORY_PATH=MEMORY_PATH,
    JAW_CLOSED=JAW_CLOSED,
    JAW_OPEN_MAX=JAW_OPEN_MAX,
    LID_L_OPEN=LID_L_OPEN,
    LID_L_CLOSED=LID_L_CLOSED,
    LID_R_OPEN=LID_R_OPEN,
    LID_R_CLOSED=LID_R_CLOSED,
    EYE_CENTER=EYE_CENTER,
    EYE_R_TRIM=EYE_R_TRIM,
    EYE_R_INVERT=EYE_R_INVERT,
    EYE_LR_MIN=EYE_LR_MIN,
    EYE_LR_MAX=EYE_LR_MAX,
    EYE_UD_MIN=EYE_UD_MIN,
    EYE_UD_MAX=EYE_UD_MAX,
    HEAD_NEUTRAL=dict(HEAD_NEUTRAL),
    HEAD_YAW_MIN=HEAD_YAW_MIN,
    HEAD_YAW_MAX=HEAD_YAW_MAX,
    HEAD_PITCH_MIN=HEAD_PITCH_MIN,
    HEAD_PITCH_MAX=HEAD_PITCH_MAX,
    HEAD_TILT_MIN=HEAD_TILT_MIN,
    HEAD_TILT_MAX=HEAD_TILT_MAX,
    head_override_pose=dict(HEAD_NEUTRAL),
    head_target_pose=dict(HEAD_NEUTRAL),
    head_current_pose=dict(HEAD_NEUTRAL),
)
log_event(runtime.logger, "info", "config_loaded", path=CONFIG_PATH, log_level=CONFIG.LOG_LEVEL)


# --- Error suppression (ALSA/JACK) ---
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)


def py_error_handler(filename, line, function, err, fmt):
    pass


c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
except Exception:
    pass


def save_session_memory():
    save_session_memory_file(runtime.session_memory, runtime.memory_lock, runtime.MEMORY_PATH)


def load_session_memory():
    load_session_memory_file(runtime.session_memory, runtime.memory_lock, runtime.MEMORY_PATH)


def apply_memory_from_text(text):
    update_session_memory_from_text(text, runtime.session_memory, save_session_memory)


def build_system_instruction():
    return compose_system_instruction(
        runtime.session_memory,
        runtime.memory_lock,
        runtime.control_mode,
        runtime.FOLLOW_UP_WAIT_S,
    )


async def main():
    init_maestro()
    if runtime.maestro:
        threading.Thread(target=eye_movement_worker, args=(runtime.maestro,), daemon=True).start()
        threading.Thread(target=head_hold_worker, args=(runtime.maestro,), daemon=True).start()

    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
    voice_name = os.environ.get("IVAN_VOICE_NAME", "Kore").strip() or "Kore"

    p = pyaudio.PyAudio()
    mic, spk = open_audio_streams(p)

    playback_task = asyncio.create_task(playback_worker(spk))
    camera_mgr = CameraManager()
    camera_task = asyncio.create_task(camera_mgr.capture_loop())

    tool_declarations = get_tool_declarations()

    try:
        while not runtime.shutdown_requested:
            mic_task = None
            cam_send_task = None
            idle_prompt_task = None
            try:
                config = {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": voice_name}}},
                    "input_audio_transcription": {},
                    "output_audio_transcription": {},
                    "tools": [{"function_declarations": tool_declarations}],
                    "system_instruction": build_system_instruction(),
                }

                async with client.aio.live.connect(
                    model="gemini-2.5-flash-native-audio-latest",
                    config=config,
                ) as session:
                    log_event(runtime.logger, "info", "session_connected", model="gemini-2.5-flash-native-audio-latest", voice=voice_name)
                    print("\n--- IVAN main4 LIVE (audio + camera) ---")

                    mic_task = asyncio.create_task(send_mic(session, mic))
                    cam_send_task = asyncio.create_task(send_camera(session, camera_mgr))
                    idle_prompt_task = asyncio.create_task(command_idle_prompt_worker(session))

                    while not runtime.shutdown_requested:
                        got_message = False
                        async for response in session.receive():
                            got_message = True
                            await handle_session_response(
                                response,
                                session,
                                runtime,
                                apply_memory_from_text,
                                execute_local_voice_command,
                                execute_robot_function,
                            )

                        if not got_message:
                            await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                log_event(runtime.logger, "warning", "session_reconnect", error=str(e))
                print(f"Reconnect: {e}")
                while not runtime.audio_queue.empty():
                    try:
                        runtime.audio_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                center_all_servos_now()
                await asyncio.sleep(1.0)
            finally:
                for task in (mic_task, cam_send_task, idle_prompt_task):
                    if task:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        except Exception:
                            pass
    finally:
        for task in (playback_task, camera_task):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        await camera_mgr.stop()
        try:
            mic.stop_stream()
            mic.close()
        except Exception:
            pass
        try:
            spk.stop_stream()
            spk.close()
        except Exception:
            pass
        p.terminate()
        save_session_memory()
        center_all_servos_now()
        log_event(runtime.logger, "info", "runtime_shutdown")


async def command_idle_prompt_worker(session):
    while not runtime.shutdown_requested:
        try:
            now = time.time()
            due_at = getattr(runtime, "command_idle_prompt_due_at", 0.0)
            if (
                due_at
                and now >= due_at
                and runtime.control_mode == "command"
                and runtime.command_enabled
                and not runtime.tracking_enabled
                and not runtime.is_ivan_talking
                and runtime.audio_queue.empty()
            ):
                runtime.command_idle_prompt_due_at = 0.0
                runtime.model_audio_suppressed_until = 0.0
                runtime.model_action_suppressed_until = 0.0
                await session.send_realtime_input(text="What do you want me to do next?")
            await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(0.4)


def run():
    load_session_memory()
    atexit.register(save_session_memory)
    atexit.register(center_all_servos_now)

    def _shutdown_signal(_sig, _frame):
        runtime.shutdown_requested = True
        log_event(runtime.logger, "info", "shutdown_signal")
        center_all_servos_now()
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGTERM, _shutdown_signal)
        signal.signal(signal.SIGINT, _shutdown_signal)
    except Exception:
        pass
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        center_all_servos_now()


robot_audio.initialize(runtime)
robot_commands.initialize(runtime)
robot_camera.initialize(runtime)
robot_motion.initialize(runtime)
robot_ocr.initialize(runtime)

open_audio_streams = robot_audio.open_audio_streams
playback_worker = robot_audio.playback_worker
send_mic = robot_audio.send_mic
send_camera = robot_audio.send_camera
execute_robot_function = robot_commands.execute_robot_function
execute_local_voice_command = robot_commands.execute_local_voice_command
CameraManager = robot_camera.CameraManager
apply_servo_calibration = robot_motion.apply_servo_calibration
load_calibration_file = robot_motion.load_calibration_file
get_maestro_port = robot_motion.get_maestro_port
clamp = robot_motion.clamp
_smooth_point = robot_motion._smooth_point
_pick_primary_face = robot_motion._pick_primary_face
_pick_primary_box = robot_motion._pick_primary_box
_build_roi_from_box = robot_motion._build_roi_from_box
_offset_boxes = robot_motion._offset_boxes
_mediapipe_detections_to_faces = robot_motion._mediapipe_detections_to_faces
_get_channel_limits = robot_motion._get_channel_limits
_get_sorted_limits = robot_motion._get_sorted_limits
set_control_mode = robot_motion.set_control_mode
set_eyelids = robot_motion.set_eyelids
set_gaze = robot_motion.set_gaze
set_head_pose = robot_motion.set_head_pose
center_all_servos = robot_motion.center_all_servos
center_all_servos_now = robot_motion.center_all_servos_now
request_head_pose = robot_motion.request_head_pose
head_hold_worker = robot_motion.head_hold_worker
eye_movement_worker = robot_motion.eye_movement_worker
init_maestro = robot_motion.init_maestro
set_tracking_target = robot_motion.set_tracking_target

runtime.set_control_mode = set_control_mode
runtime.request_head_pose = request_head_pose
runtime.clamp = clamp
runtime._smooth_point = _smooth_point
runtime._pick_primary_face = _pick_primary_face
runtime._pick_primary_box = _pick_primary_box
runtime._build_roi_from_box = _build_roi_from_box
runtime._offset_boxes = _offset_boxes
runtime._mediapipe_detections_to_faces = _mediapipe_detections_to_faces
runtime._get_channel_limits = _get_channel_limits
runtime._get_sorted_limits = _get_sorted_limits
runtime.set_gaze = set_gaze
runtime.set_head_pose = set_head_pose
runtime.center_all_servos = center_all_servos
runtime.center_all_servos_now = center_all_servos_now
runtime.set_tracking_target = set_tracking_target
runtime.read_visible_text = robot_ocr.read_visible_text
runtime.get_intro_head_pose = robot_motion.get_intro_head_pose
runtime.perform_head_gesture = robot_motion.perform_head_gesture


if __name__ == "__main__":
    run()
