import re
import time


_ctx = None

_FEATURES = {
    "conversation": "Ivan can carry on a live conversation, remember session facts, and respond naturally.",
    "memory": "Ivan can remember names, likes, and facts from the current session.",
    "camera": "Ivan can use camera frames to describe people, objects, actions, colors, and scene changes.",
    "ocr": "Ivan can read visible text, handwriting, labels, numbers, and simple math with OCR.",
    "command mode": "Command mode lets Ivan accept manual movement commands for the head and eyes.",
    "tracking mode": "Tracking mode lets Ivan automatically follow faces and motion with his eyes and head.",
    "intro mode": "Intro mode keeps Ivan quiet, looking slightly down, blinking naturally, and answering yes/no with head gestures.",
    "voice": "Ivan can speak in different languages and adapt his speaking style when asked.",
}


def _feature_list_text():
    return (
        "Here is what I can do:\n"
        "- Live conversation and memory\n"
        "- Camera awareness\n"
        "- Reading text and math with OCR\n"
        "- Command mode\n"
        "- Tracking mode\n"
        "- Intro mode\n"
        "- Voice style and language changes when asked"
    )


def _feature_help_text(feature):
    key = str(feature or "").strip().lower()
    if key in _FEATURES:
        return _FEATURES[key]
    if key.replace("_", " ") in _FEATURES:
        return _FEATURES[key.replace("_", " ")]
    return "I can explain conversation, memory, camera awareness, OCR, command mode, tracking mode, intro mode, or voice."


def initialize(context):
    global _ctx
    _ctx = context


def execute_robot_function(name, args):
    args = args or {}

    if name == "set_mode":
        mode = str(args.get("mode", "command")).lower()
        result = _ctx.set_control_mode(mode)
        if mode in {"command", "intro"}:
            _ctx.tracked_lr = 0
            _ctx.tracked_ud = 0
            _ctx.tracked_head_yaw = 0
            _ctx.tracked_head_pitch = 0
            _ctx.last_tracking_update = 0.0
            _ctx.tracking_resume_at = 0.0
            _ctx.eye_manual_until = 0.0
            _ctx.gaze_hold_enabled = False
            target_pose = _ctx.get_intro_head_pose() if mode == "intro" else _ctx.HEAD_NEUTRAL
            _ctx.request_head_pose(
                yaw=target_pose["yaw"],
                pitch=target_pose["pitch"],
                tilt=target_pose["tilt"],
            )
        return result

    if name == "set_tracking":
        _ctx.tracking_enabled = bool(args.get("enabled", True))
        _ctx.command_enabled = not _ctx.tracking_enabled
        if not _ctx.tracking_enabled:
            _ctx.tracked_lr = 0
            _ctx.tracked_ud = 0
            _ctx.tracked_head_yaw = 0
            _ctx.tracked_head_pitch = 0
            _ctx.last_tracking_update = 0.0
            _ctx.tracking_resume_at = 0.0
            _ctx.eye_manual_until = 0.0
            _ctx.request_head_pose(
                yaw=_ctx.HEAD_NEUTRAL["yaw"],
                pitch=_ctx.HEAD_NEUTRAL["pitch"],
                tilt=_ctx.HEAD_NEUTRAL["tilt"],
            )
        return {"ok": True, "tracking_enabled": _ctx.tracking_enabled}

    if name == "look_direction":
        if not _ctx.command_enabled:
            return {"ok": False, "error": "Movement command ignored in tracking mode"}
        direction = str(args.get("direction", "center")).lower().strip()
        strength = int(_ctx.clamp(int(args.get("strength", 90)), 0, 100))

        yaw = _ctx.head_target_pose["yaw"]
        pitch = _ctx.head_target_pose["pitch"]
        yaw_min, yaw_max, _, _ = _ctx._get_sorted_limits(_ctx.CH_YAW, _ctx.HEAD_YAW_MIN, _ctx.HEAD_YAW_MAX)
        pitch_min, pitch_max, _, _ = _ctx._get_sorted_limits(_ctx.CH_FACE_PITCH, _ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX)
        strength_pct = strength / 100.0
        if direction == "left":
            yaw_strength = max(0.80, strength_pct)
            yaw = _ctx.HEAD_NEUTRAL["yaw"] + int((yaw_max - _ctx.HEAD_NEUTRAL["yaw"]) * yaw_strength)
        elif direction == "right":
            yaw_strength = max(0.80, strength_pct)
            yaw = _ctx.HEAD_NEUTRAL["yaw"] - int((_ctx.HEAD_NEUTRAL["yaw"] - yaw_min) * yaw_strength)
        elif direction == "up":
            pitch = _ctx.HEAD_NEUTRAL["pitch"] + int((pitch_max - _ctx.HEAD_NEUTRAL["pitch"]) * strength_pct)
        elif direction == "down":
            pitch = _ctx.HEAD_NEUTRAL["pitch"] - int((_ctx.HEAD_NEUTRAL["pitch"] - pitch_min) * strength_pct)
        elif direction == "center":
            yaw = _ctx.HEAD_NEUTRAL["yaw"]
            pitch = _ctx.HEAD_NEUTRAL["pitch"]

        _ctx.request_head_pose(yaw=yaw, pitch=pitch)
        _ctx.head_override_pose["yaw"] = int(_ctx.clamp(yaw, yaw_min, yaw_max))
        _ctx.head_override_pose["pitch"] = int(_ctx.clamp(pitch, pitch_min, pitch_max))
        _ctx.head_override_pose["tilt"] = int(_ctx.clamp(_ctx.head_target_pose["tilt"], _ctx.HEAD_TILT_MIN, _ctx.HEAD_TILT_MAX))
        _ctx.head_override_until = time.time() + 3.2
        _ctx.tracking_resume_at = _ctx.head_override_until + 0.5
        if _ctx.maestro:
            _ctx.set_gaze(_ctx.maestro, 0, 0)
        _ctx.gaze_hold_enabled = True
        _ctx.gaze_hold_lr = 0
        _ctx.gaze_hold_ud = 0
        _ctx.eye_manual_until = time.time() + _ctx.COMMAND_TRACKING_PAUSE_S
        return {"ok": True, "direction": direction, "strength": strength}

    if name == "move_head":
        if not _ctx.command_enabled:
            return {"ok": False, "error": "Movement command ignored in tracking mode"}
        yaw = int(args.get("yaw", _ctx.head_target_pose["yaw"]))
        pitch = int(args.get("pitch", _ctx.head_target_pose["pitch"]))
        tilt = int(args.get("tilt", _ctx.head_target_pose["tilt"]))
        duration_arg = args.get("duration_s")
        duration_s = float(3.0 if duration_arg is None else duration_arg)
        duration_s = float(_ctx.clamp(duration_s, 0.2, 4.0))

        yaw_min, yaw_max, _, _ = _ctx._get_sorted_limits(_ctx.CH_YAW, _ctx.HEAD_YAW_MIN, _ctx.HEAD_YAW_MAX)
        pitch_min, pitch_max, _, _ = _ctx._get_sorted_limits(_ctx.CH_FACE_PITCH, _ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX)
        tilt_min, tilt_max, _, _ = _ctx._get_sorted_limits(_ctx.CH_TILT, _ctx.HEAD_TILT_MIN, _ctx.HEAD_TILT_MAX)
        _ctx.head_override_pose["yaw"] = int(_ctx.clamp(yaw, yaw_min, yaw_max))
        _ctx.head_override_pose["pitch"] = int(_ctx.clamp(pitch, pitch_min, pitch_max))
        _ctx.head_override_pose["tilt"] = int(_ctx.clamp(tilt, tilt_min, tilt_max))
        _ctx.request_head_pose(
            yaw=_ctx.head_override_pose["yaw"],
            pitch=_ctx.head_override_pose["pitch"],
            tilt=_ctx.head_override_pose["tilt"],
        )
        _ctx.head_override_until = time.time() + duration_s
        _ctx.tracking_resume_at = _ctx.head_override_until + 0.5

        if _ctx.maestro:
            _ctx.set_head_pose(
                _ctx.maestro,
                yaw=_ctx.head_override_pose["yaw"],
                pitch=_ctx.head_override_pose["pitch"],
                tilt=_ctx.head_override_pose["tilt"],
            )
        return {
            "ok": True,
            "yaw": _ctx.head_override_pose["yaw"],
            "pitch": _ctx.head_override_pose["pitch"],
            "tilt": _ctx.head_override_pose["tilt"],
            "duration_s": duration_s,
        }

    if name == "center_servos":
        if not _ctx.command_enabled:
            return {"ok": False, "error": "Movement command ignored in tracking mode"}
        _ctx.request_head_pose(
            yaw=_ctx.HEAD_NEUTRAL["yaw"],
            pitch=_ctx.HEAD_NEUTRAL["pitch"],
            tilt=_ctx.HEAD_NEUTRAL["tilt"],
        )
        _ctx.gaze_hold_enabled = True
        _ctx.gaze_hold_lr = 0
        _ctx.gaze_hold_ud = 0
        if _ctx.maestro:
            _ctx.center_all_servos(_ctx.maestro)
        return {"ok": True}

    if name == "gesture_head":
        if not _ctx.command_enabled:
            return {"ok": False, "error": "Movement command ignored in tracking mode"}
        return _ctx.perform_head_gesture(args.get("gesture", "yes"))

    if name == "read_visible_text":
        if not hasattr(_ctx, "read_visible_text"):
            return {"ok": False, "error": "OCR is not configured"}
        mode = str(args.get("mode", "auto")).lower().strip()
        if mode not in {"auto", "document"}:
            mode = "auto"
        return _ctx.read_visible_text(mode=mode)

    if name == "describe_features":
        return {"ok": True, "features": _feature_list_text()}

    if name == "feature_help":
        feature = args.get("feature", "")
        text = _feature_help_text(feature)
        return {"ok": True, "feature": feature, "explanation": text}

    return {"ok": False, "error": f"Unknown function: {name}"}


def execute_local_voice_command(text):
    if not text:
        return False
    t = text.lower().strip()

    if re.search(r"\b(tracking mode|enable tracking|start tracking|turn on tracking)\b", t) or "follow me" in t:
        execute_robot_function("set_mode", {"mode": "tracking"})
        return True
    if re.search(r"\b(command mode|disable tracking|stop tracking|turn off tracking)\b", t) or "stop following" in t:
        execute_robot_function("set_mode", {"mode": "command"})
        return True
    if re.search(r"\bintro mode\b", t) or re.search(r"\b(enable|start|switch to)\s+intro\b", t):
        execute_robot_function("set_mode", {"mode": "intro"})
        return True
    if re.search(r"\b(what can you do|what are your features|tell me your features|introduce yourself)\b", t):
        execute_robot_function("describe_features", {})
        return False
    if (
        re.search(r"\b(read|scan)\s+(this|that)\b", t)
        or re.search(r"\b(read|solve)\s+(this|that)\s+(equation|math|problem|text)\b", t)
        or re.search(r"\bwhat\s+does\s+(this|that)\s+say\b", t)
        or re.search(r"\bcan\s+you\s+read\s+(this|that)\b", t)
    ):
        execute_robot_function("read_visible_text", {"mode": "document"})
        return False

    if not _ctx.command_enabled:
        return False

    if re.search(r"\blook\s+left\b", t):
        execute_robot_function("look_direction", {"direction": "left", "strength": 100})
        return True
    if re.search(r"\blook\s+right\b", t):
        execute_robot_function("look_direction", {"direction": "right", "strength": 100})
        return True
    if re.search(r"\blook\s+up\b", t):
        execute_robot_function("look_direction", {"direction": "up", "strength": 85})
        return True
    if re.search(r"\blook\s+down\b", t):
        execute_robot_function("look_direction", {"direction": "down", "strength": 85})
        return True
    if re.search(r"\blook\s+(center|straight)\b", t):
        execute_robot_function("look_direction", {"direction": "center", "strength": 80})
        return True

    yaw_min, yaw_max, _, _ = _ctx._get_sorted_limits(_ctx.CH_YAW, _ctx.HEAD_YAW_MIN, _ctx.HEAD_YAW_MAX)
    pitch_min, pitch_max, _, _ = _ctx._get_sorted_limits(_ctx.CH_FACE_PITCH, _ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX)
    tilt_min, tilt_max, tilt_raw_min, tilt_raw_max = _ctx._get_sorted_limits(_ctx.CH_TILT, _ctx.HEAD_TILT_MIN, _ctx.HEAD_TILT_MAX)
    tilt_left_pulse = max(tilt_raw_min, tilt_raw_max)
    tilt_right_pulse = min(tilt_raw_min, tilt_raw_max)

    if re.search(r"\btilt\s+left\s+side\b", t):
        execute_robot_function("move_head", {"tilt": 1650, "duration_s": 3.0})
        return True
    if re.search(r"\btilt\s+right\s+side\b", t):
        execute_robot_function("move_head", {"tilt": 1360, "duration_s": 3.0})
        return True
    if re.search(r"\b(tilt|lean|head tilt)\s+left\b", t):
        execute_robot_function("move_head", {"tilt": tilt_left_pulse, "duration_s": 3.0})
        return True
    if re.search(r"\b(tilt|lean|head tilt)\s+right\b", t):
        execute_robot_function("move_head", {"tilt": tilt_right_pulse, "duration_s": 3.0})
        return True
    if re.search(r"\b(tilt|head)\s+up\b", t):
        execute_robot_function("move_head", {"pitch": pitch_max, "duration_s": 3.0})
        return True
    if re.search(r"\b(tilt|head)\s+down\b", t):
        execute_robot_function("move_head", {"pitch": pitch_min, "duration_s": 3.0})
        return True
    if re.search(r"\b(turn|move)\s+head\s+left\b", t) or re.search(r"\bturn\s+left\b", t):
        execute_robot_function("move_head", {"yaw": yaw_max, "duration_s": 1.8})
        return True
    if re.search(r"\b(turn|move)\s+head\s+right\b", t) or re.search(r"\bturn\s+right\b", t):
        execute_robot_function("move_head", {"yaw": yaw_min, "duration_s": 1.8})
        return True
    if re.search(r"\b(center|home|neutral)\b", t):
        execute_robot_function("center_servos", {})
        return True

    return False
