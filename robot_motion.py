import json
import math
import os
import random
import time

from servo_controller import ServoController


_ctx = None


def initialize(context):
    global _ctx
    _ctx = context


def apply_servo_calibration(maestro):
    if not maestro:
        return

    cfg = maestro.servos

    if _ctx.CH_JAW in cfg:
        jaw = cfg[_ctx.CH_JAW]
        if "min" in jaw:
            _ctx.JAW_CLOSED = jaw["min"]
        if "max" in jaw:
            _ctx.JAW_OPEN_MAX = jaw["max"]
        if "minclosed" in jaw:
            _ctx.JAW_CLOSED = jaw["minclosed"]
        if "maxopen" in jaw:
            _ctx.JAW_OPEN_MAX = jaw["maxopen"]

    if _ctx.CH_LID_L in cfg:
        lid_l = cfg[_ctx.CH_LID_L]
        if "min" in lid_l:
            _ctx.LID_L_CLOSED = lid_l["min"]
        if "max" in lid_l:
            _ctx.LID_L_OPEN = lid_l["max"]
        if "minclosed" in lid_l:
            _ctx.LID_L_CLOSED = lid_l["minclosed"]
        if "maxopen" in lid_l:
            _ctx.LID_L_OPEN = lid_l["maxopen"]

    if _ctx.CH_LID_R in cfg:
        lid_r = cfg[_ctx.CH_LID_R]
        if "min" in lid_r:
            _ctx.LID_R_CLOSED = lid_r["min"]
        if "max" in lid_r:
            _ctx.LID_R_OPEN = lid_r["max"]
        if "minclosed" in lid_r:
            _ctx.LID_R_CLOSED = lid_r["minclosed"]
        if "maxopen" in lid_r:
            _ctx.LID_R_OPEN = lid_r["maxopen"]

    if _ctx.CH_EYE_L_LR in cfg and _ctx.CH_EYE_R_LR in cfg:
        eye_l = cfg[_ctx.CH_EYE_L_LR]
        eye_r = cfg[_ctx.CH_EYE_R_LR]
        if "neutral" in eye_l and "neutral" in eye_r:
            _ctx.EYE_CENTER = eye_l["neutral"]
            _ctx.EYE_R_TRIM = eye_r["neutral"] - eye_l["neutral"]
        if "min" in eye_l and "min" in eye_r:
            _ctx.EYE_LR_MIN = min(eye_l["min"], eye_r["min"])
        if "max" in eye_l and "max" in eye_r:
            _ctx.EYE_LR_MAX = max(eye_l["max"], eye_r["max"])
        if "minleft" in eye_l and "minleft" in eye_r:
            _ctx.EYE_LR_MIN = min(eye_l["minleft"], eye_r["minleft"])
        if "maxright" in eye_l and "maxright" in eye_r:
            _ctx.EYE_LR_MAX = max(eye_l["maxright"], eye_r["maxright"])

    if _ctx.CH_EYES_UD in cfg:
        raw_min, raw_max = maestro.get_limits(_ctx.CH_EYES_UD)
        _ctx.EYE_UD_MIN, _ctx.EYE_UD_MAX = min(raw_min, raw_max), max(raw_min, raw_max)

    if _ctx.CH_YAW in cfg and _ctx.CH_FACE_PITCH in cfg and _ctx.CH_TILT in cfg:
        _ctx.HEAD_NEUTRAL = {
            "yaw": maestro.get_neutral(_ctx.CH_YAW, _ctx.HEAD_NEUTRAL["yaw"]),
            "pitch": maestro.get_neutral(_ctx.CH_FACE_PITCH, _ctx.HEAD_NEUTRAL["pitch"]),
            "tilt": maestro.get_neutral(_ctx.CH_TILT, _ctx.HEAD_NEUTRAL["tilt"]),
        }

    _ctx.HEAD_YAW_MIN, _ctx.HEAD_YAW_MAX = maestro.get_limits(_ctx.CH_YAW)
    _ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX = maestro.get_limits(_ctx.CH_FACE_PITCH)
    _ctx.HEAD_TILT_MIN, _ctx.HEAD_TILT_MAX = maestro.get_limits(_ctx.CH_TILT)


def _apply_calibration_overrides(payload):
    if not isinstance(payload, dict):
        return False

    updated = False
    mapping = {
        "JAW_CLOSED": "JAW_CLOSED",
        "JAW_OPEN_MAX": "JAW_OPEN_MAX",
        "LID_L_OPEN": "LID_L_OPEN",
        "LID_L_CLOSED": "LID_L_CLOSED",
        "LID_R_OPEN": "LID_R_OPEN",
        "LID_R_CLOSED": "LID_R_CLOSED",
        "EYE_CENTER": "EYE_CENTER",
        "EYE_R_TRIM": "EYE_R_TRIM",
        "EYE_LR_MIN": "EYE_LR_MIN",
        "EYE_LR_MAX": "EYE_LR_MAX",
        "EYE_UD_MIN": "EYE_UD_MIN",
        "EYE_UD_MAX": "EYE_UD_MAX",
        "HEAD_YAW_MIN": "HEAD_YAW_MIN",
        "HEAD_YAW_MAX": "HEAD_YAW_MAX",
        "HEAD_PITCH_MIN": "HEAD_PITCH_MIN",
        "HEAD_PITCH_MAX": "HEAD_PITCH_MAX",
        "HEAD_TILT_MIN": "HEAD_TILT_MIN",
        "HEAD_TILT_MAX": "HEAD_TILT_MAX",
    }

    for key, attr in mapping.items():
        if key in payload:
            try:
                setattr(_ctx, attr, int(payload[key]))
                updated = True
            except Exception:
                continue

    if "HEAD_NEUTRAL_YAW" in payload:
        _ctx.HEAD_NEUTRAL["yaw"] = int(payload["HEAD_NEUTRAL_YAW"])
        updated = True
    if "HEAD_NEUTRAL_PITCH" in payload:
        _ctx.HEAD_NEUTRAL["pitch"] = int(payload["HEAD_NEUTRAL_PITCH"])
        updated = True
    if "HEAD_NEUTRAL_TILT" in payload:
        _ctx.HEAD_NEUTRAL["tilt"] = int(payload["HEAD_NEUTRAL_TILT"])
        updated = True

    return updated


def _apply_calibration_to_maestro(maestro):
    if not maestro:
        return
    maestro.servos.setdefault(_ctx.CH_EYE_L_LR, {}).update({
        "neutral": int(_ctx.EYE_CENTER),
        "min": int(min(_ctx.EYE_LR_MIN, _ctx.EYE_LR_MAX)),
        "max": int(max(_ctx.EYE_LR_MIN, _ctx.EYE_LR_MAX)),
    })
    maestro.servos.setdefault(_ctx.CH_EYE_R_LR, {}).update({
        "neutral": int(_ctx.EYE_CENTER + _ctx.EYE_R_TRIM),
        "min": int(min(_ctx.EYE_LR_MIN, _ctx.EYE_LR_MAX)),
        "max": int(max(_ctx.EYE_LR_MIN, _ctx.EYE_LR_MAX)),
    })
    maestro.servos.setdefault(_ctx.CH_EYES_UD, {}).update({
        "neutral": int(_ctx.EYE_CENTER),
        "min": int(min(_ctx.EYE_UD_MIN, _ctx.EYE_UD_MAX)),
        "max": int(max(_ctx.EYE_UD_MIN, _ctx.EYE_UD_MAX)),
    })
    maestro.servos.setdefault(_ctx.CH_LID_L, {}).update({
        "neutral": int(_ctx.LID_L_CLOSED),
        "min": int(min(_ctx.LID_L_CLOSED, _ctx.LID_L_OPEN)),
        "max": int(max(_ctx.LID_L_CLOSED, _ctx.LID_L_OPEN)),
    })
    maestro.servos.setdefault(_ctx.CH_LID_R, {}).update({
        "neutral": int(_ctx.LID_R_CLOSED),
        "min": int(min(_ctx.LID_R_CLOSED, _ctx.LID_R_OPEN)),
        "max": int(max(_ctx.LID_R_CLOSED, _ctx.LID_R_OPEN)),
    })
    maestro.servos.setdefault(_ctx.CH_JAW, {}).update({
        "neutral": int(_ctx.JAW_CLOSED),
        "min": int(min(_ctx.JAW_CLOSED, _ctx.JAW_OPEN_MAX)),
        "max": int(max(_ctx.JAW_CLOSED, _ctx.JAW_OPEN_MAX)),
    })
    maestro.servos.setdefault(_ctx.CH_YAW, {}).update({
        "neutral": int(_ctx.HEAD_NEUTRAL["yaw"]),
        "min": int(_ctx.HEAD_YAW_MIN),
        "max": int(_ctx.HEAD_YAW_MAX),
    })
    maestro.servos.setdefault(_ctx.CH_FACE_PITCH, {}).update({
        "neutral": int(_ctx.HEAD_NEUTRAL["pitch"]),
        "min": int(_ctx.HEAD_PITCH_MIN),
        "max": int(_ctx.HEAD_PITCH_MAX),
    })
    maestro.servos.setdefault(_ctx.CH_TILT, {}).update({
        "neutral": int(_ctx.HEAD_NEUTRAL["tilt"]),
        "min": int(_ctx.HEAD_TILT_MIN),
        "max": int(_ctx.HEAD_TILT_MAX),
    })


def _reset_head_state_to_neutral():
    _ctx.head_override_pose["yaw"] = _ctx.HEAD_NEUTRAL["yaw"]
    _ctx.head_override_pose["pitch"] = _ctx.HEAD_NEUTRAL["pitch"]
    _ctx.head_override_pose["tilt"] = _ctx.HEAD_NEUTRAL["tilt"]
    _ctx.head_target_pose["yaw"] = _ctx.HEAD_NEUTRAL["yaw"]
    _ctx.head_target_pose["pitch"] = _ctx.HEAD_NEUTRAL["pitch"]
    _ctx.head_target_pose["tilt"] = _ctx.HEAD_NEUTRAL["tilt"]
    _ctx.head_current_pose["yaw"] = _ctx.HEAD_NEUTRAL["yaw"]
    _ctx.head_current_pose["pitch"] = _ctx.HEAD_NEUTRAL["pitch"]
    _ctx.head_current_pose["tilt"] = _ctx.HEAD_NEUTRAL["tilt"]


def load_calibration_file():
    if not os.path.exists(_ctx.CALIBRATION_PATH):
        return False
    try:
        with open(_ctx.CALIBRATION_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if _apply_calibration_overrides(payload):
            print(f"Loaded servo calibration from {_ctx.CALIBRATION_PATH}")
            return True
    except Exception as e:
        print(f"Calibration load warning: {e}")
    return False


def get_maestro_port():
    for port in ("/dev/ttyACM0", "/dev/ttyACM1"):
        if os.path.exists(port):
            return port
    return None


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _soft_track_error(norm, deadzone, edge_soften):
    abs_norm = abs(norm)
    if abs_norm <= deadzone:
        return 0.0
    err = (abs_norm - deadzone) / max(1e-6, 0.5 - deadzone)
    if err > edge_soften:
        edge_span = max(1e-6, 1.0 - edge_soften)
        edge_ratio = (err - edge_soften) / edge_span
        err = edge_soften + (1.0 - edge_soften) * (edge_ratio ** 0.6)
    return math.copysign(err, norm)


def _smooth_point(prev_point, point, alpha):
    if prev_point is None:
        return point
    return (
        prev_point[0] + ((point[0] - prev_point[0]) * alpha),
        prev_point[1] + ((point[1] - prev_point[1]) * alpha),
    )


def _pick_primary_face(faces, frame_w, frame_h, locked_center=None):
    if faces is None or len(faces) == 0:
        return None
    if locked_center is None or frame_w <= 0 or frame_h <= 0:
        return max(faces, key=lambda f: (f[2] * f[3], f[4] if len(f) > 4 else 0.0))

    best_face = None
    best_score = None
    for face in faces:
        x, y, fw, fh = face[:4]
        cx = (x + (fw * 0.5)) / frame_w
        cy = (y + (fh * 0.5)) / frame_h
        dx = cx - locked_center[0]
        dy = cy - locked_center[1]
        dist = math.hypot(dx, dy)
        conf = face[4] if len(face) > 4 else 0.0
        area_score = fw * fh
        score = (dist, -conf, -area_score)
        if dist <= _ctx.PRIMARY_FACE_MATCH_NORM and (best_score is None or score < best_score):
            best_face = face
            best_score = score

    if best_face is not None:
        return best_face
    return max(faces, key=lambda f: (f[2] * f[3], f[4] if len(f) > 4 else 0.0))


def _pick_primary_box(boxes, frame_w, frame_h, locked_center=None):
    if boxes is None or len(boxes) == 0:
        return None
    if locked_center is None or frame_w <= 0 or frame_h <= 0:
        return max(boxes, key=lambda b: b[2] * b[3])

    best_box = None
    best_score = None
    for box in boxes:
        x, y, bw, bh = box
        cx = (x + (bw * 0.5)) / frame_w
        cy = (y + (bh * 0.5)) / frame_h
        dist = math.hypot(cx - locked_center[0], cy - locked_center[1])
        score = (dist, -(bw * bh))
        if dist <= _ctx.PRIMARY_FACE_MATCH_NORM * 1.6 and (best_score is None or score < best_score):
            best_box = box
            best_score = score

    if best_box is not None:
        return best_box
    return max(boxes, key=lambda b: b[2] * b[3])


def _build_roi_from_box(box, frame_w, frame_h, expand=1.0, min_size=0):
    if box is None or frame_w <= 0 or frame_h <= 0:
        return None
    x, y, bw, bh = box[:4]
    cx = x + (bw * 0.5)
    cy = y + (bh * 0.5)
    size = max(bw, bh, min_size) * expand
    half_w = size * 0.5
    half_h = size * 0.5
    x0 = int(clamp(round(cx - half_w), 0, frame_w - 1))
    y0 = int(clamp(round(cy - half_h), 0, frame_h - 1))
    x1 = int(clamp(round(cx + half_w), x0 + 1, frame_w))
    y1 = int(clamp(round(cy + half_h), y0 + 1, frame_h))
    return (x0, y0, x1 - x0, y1 - y0)


def _offset_boxes(boxes, off_x, off_y):
    if boxes is None or len(boxes) == 0:
        return []
    shifted = []
    for box in boxes:
        if len(box) > 4:
            x, y, bw, bh, extra = box
            shifted.append((x + off_x, y + off_y, bw, bh, extra))
        else:
            x, y, bw, bh = box
            shifted.append((x + off_x, y + off_y, bw, bh))
    return shifted


def _mediapipe_detections_to_faces(detections, frame_w, frame_h):
    faces = []
    if not detections:
        return faces
    for detection in detections:
        score = 0.0
        try:
            if detection.score:
                score = float(detection.score[0])
        except Exception:
            score = 0.0
        if score < _ctx.FACE_DETECTION_CONFIDENCE:
            continue
        try:
            rel_box = detection.location_data.relative_bounding_box
        except Exception:
            continue
        x = int(rel_box.xmin * frame_w)
        y = int(rel_box.ymin * frame_h)
        w = int(rel_box.width * frame_w)
        h = int(rel_box.height * frame_h)
        x = int(clamp(x, 0, max(0, frame_w - 1)))
        y = int(clamp(y, 0, max(0, frame_h - 1)))
        w = int(clamp(w, 1, frame_w - x))
        h = int(clamp(h, 1, frame_h - y))
        aspect = w / max(1.0, h)
        area = w * h
        if area < 900 or aspect < 0.55 or aspect > 1.45:
            continue
        faces.append((x, y, w, h, score))
    return faces


def _get_channel_limits(channel, fallback_min, fallback_max):
    if _ctx.maestro:
        try:
            return _ctx.maestro.get_limits(channel)
        except Exception:
            pass
    return fallback_min, fallback_max


def _get_sorted_limits(channel, fallback_min, fallback_max):
    raw_min, raw_max = _get_channel_limits(channel, fallback_min, fallback_max)
    return min(raw_min, raw_max), max(raw_min, raw_max), raw_min, raw_max


def set_control_mode(mode):
    mode = str(mode).strip().lower()
    if mode == "tracking":
        _ctx.control_mode = "tracking"
        _ctx.tracking_enabled = True
        _ctx.command_enabled = False
    elif mode in {"command", "intro"}:
        _ctx.control_mode = mode
        _ctx.tracking_enabled = False
        _ctx.command_enabled = True
    else:
        mode = getattr(_ctx, "control_mode", "command")
    return {
        "ok": True,
        "mode": mode,
        "tracking_enabled": _ctx.tracking_enabled,
        "command_enabled": _ctx.command_enabled,
    }


def set_eyelids(maestro, closed):
    if closed:
        maestro.set_target(_ctx.CH_LID_L, _ctx.LID_L_CLOSED)
        maestro.set_target(_ctx.CH_LID_R, _ctx.LID_R_CLOSED)
    else:
        maestro.set_target(_ctx.CH_LID_L, _ctx.LID_L_OPEN)
        maestro.set_target(_ctx.CH_LID_R, _ctx.LID_R_OPEN)


def set_gaze(maestro, lr_offset, ud_offset):
    left_lr = clamp(_ctx.EYE_CENTER + lr_offset, _ctx.EYE_LR_MIN, _ctx.EYE_LR_MAX)
    right_base = _ctx.EYE_CENTER - lr_offset if _ctx.EYE_R_INVERT else _ctx.EYE_CENTER + lr_offset
    right_lr = clamp(right_base + _ctx.EYE_R_TRIM, _ctx.EYE_LR_MIN, _ctx.EYE_LR_MAX)
    eyes_ud = clamp(_ctx.EYE_CENTER + ud_offset, _ctx.EYE_UD_MIN, _ctx.EYE_UD_MAX)

    maestro.set_target(_ctx.CH_EYE_L_LR, left_lr)
    maestro.set_target(_ctx.CH_EYE_R_LR, right_lr)
    maestro.set_target(_ctx.CH_EYES_UD, eyes_ud)


def set_head_pose(maestro, yaw=1500, pitch=1500, tilt=1500):
    yaw_min, yaw_max, _, _ = _get_sorted_limits(_ctx.CH_YAW, _ctx.HEAD_YAW_MIN, _ctx.HEAD_YAW_MAX)
    pitch_min, pitch_max, _, _ = _get_sorted_limits(_ctx.CH_FACE_PITCH, _ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX)
    tilt_min, tilt_max, _, _ = _get_sorted_limits(_ctx.CH_TILT, _ctx.HEAD_TILT_MIN, _ctx.HEAD_TILT_MAX)
    maestro.set_target(_ctx.CH_YAW, int(clamp(yaw, yaw_min, yaw_max)))
    maestro.set_target(_ctx.CH_FACE_PITCH, int(clamp(pitch, pitch_min, pitch_max)))
    maestro.set_target(_ctx.CH_TILT, int(clamp(tilt, tilt_min, tilt_max)))


def center_all_servos(maestro):
    if not maestro:
        return
    set_gaze(maestro, 0, 0)
    set_eyelids(maestro, closed=False)
    set_head_pose(
        maestro,
        yaw=_ctx.HEAD_NEUTRAL["yaw"],
        pitch=_ctx.HEAD_NEUTRAL["pitch"],
        tilt=_ctx.HEAD_NEUTRAL["tilt"],
    )
    maestro.set_target(_ctx.CH_JAW, _ctx.JAW_CLOSED)


def center_all_servos_now():
    if not _ctx.maestro:
        return
    try:
        _reset_head_state_to_neutral()
        center_all_servos(_ctx.maestro)
        time.sleep(0.35)
    except Exception:
        pass


def _apply_head_tracking_dynamics(maestro, yaw_err, pitch_err, confidence):
    if not maestro:
        return
    mag = max(abs(yaw_err), abs(pitch_err))
    mag_ratio = clamp(mag / 220.0, 0.0, 1.0)
    conf_ratio = clamp(confidence, 0.0, 1.0)
    speed = int(round(
        _ctx.HEAD_TRACK_SPEED_MIN
        + ((_ctx.HEAD_TRACK_SPEED_MAX - _ctx.HEAD_TRACK_SPEED_MIN) * (0.60 * mag_ratio + 0.40 * conf_ratio))
    ))
    accel = int(round(
        _ctx.HEAD_TRACK_ACCEL_MIN
        + ((_ctx.HEAD_TRACK_ACCEL_MAX - _ctx.HEAD_TRACK_ACCEL_MIN) * (0.55 * mag_ratio + 0.45 * conf_ratio))
    ))
    for channel in (_ctx.CH_FACE_PITCH, _ctx.CH_FACE_YAW, _ctx.CH_HEAD_TILT):
        try:
            maestro.set_speed(channel, speed)
            maestro.set_accel(channel, accel)
        except Exception:
            pass


def request_head_pose(yaw=None, pitch=None, tilt=None):
    yaw_min, yaw_max = sorted((_ctx.HEAD_YAW_MIN, _ctx.HEAD_YAW_MAX))
    pitch_min, pitch_max = sorted((_ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX))
    tilt_min, tilt_max = sorted((_ctx.HEAD_TILT_MIN, _ctx.HEAD_TILT_MAX))
    if yaw is not None:
        _ctx.head_target_pose["yaw"] = int(clamp(yaw, yaw_min, yaw_max))
    if pitch is not None:
        _ctx.head_target_pose["pitch"] = int(clamp(pitch, pitch_min, pitch_max))
    if tilt is not None:
        _ctx.head_target_pose["tilt"] = int(clamp(tilt, tilt_min, tilt_max))


def get_intro_head_pose():
    pitch_min, pitch_max = sorted((_ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX))
    pitch_span_down = max(0, _ctx.HEAD_NEUTRAL["pitch"] - pitch_min)
    intro_pitch = int(clamp(_ctx.HEAD_NEUTRAL["pitch"] - int(round(pitch_span_down * 0.38)), pitch_min, pitch_max))
    return {
        "yaw": _ctx.HEAD_NEUTRAL["yaw"],
        "pitch": intro_pitch,
        "tilt": _ctx.HEAD_NEUTRAL["tilt"],
    }


def _lerp_int(current, target, alpha):
    return int(round(current + ((target - current) * alpha)))


def _apply_override_pose(yaw, pitch, tilt, duration_s):
    yaw_min, yaw_max, _, _ = _get_sorted_limits(_ctx.CH_YAW, _ctx.HEAD_YAW_MIN, _ctx.HEAD_YAW_MAX)
    pitch_min, pitch_max, _, _ = _get_sorted_limits(_ctx.CH_FACE_PITCH, _ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX)
    tilt_min, tilt_max, _, _ = _get_sorted_limits(_ctx.CH_TILT, _ctx.HEAD_TILT_MIN, _ctx.HEAD_TILT_MAX)
    _ctx.head_override_pose["yaw"] = int(clamp(yaw, yaw_min, yaw_max))
    _ctx.head_override_pose["pitch"] = int(clamp(pitch, pitch_min, pitch_max))
    _ctx.head_override_pose["tilt"] = int(clamp(tilt, tilt_min, tilt_max))
    request_head_pose(
        yaw=_ctx.head_override_pose["yaw"],
        pitch=_ctx.head_override_pose["pitch"],
        tilt=_ctx.head_override_pose["tilt"],
    )
    _ctx.head_override_until = time.time() + duration_s
    _ctx.tracking_resume_at = _ctx.head_override_until + 0.2
    if _ctx.maestro:
        set_head_pose(
            _ctx.maestro,
            yaw=_ctx.head_override_pose["yaw"],
            pitch=_ctx.head_override_pose["pitch"],
            tilt=_ctx.head_override_pose["tilt"],
        )


def perform_head_gesture(gesture):
    gesture = str(gesture or "").strip().lower()
    rest_pose = get_intro_head_pose() if getattr(_ctx, "control_mode", "command") == "intro" else dict(_ctx.head_target_pose)
    if gesture not in {"yes", "no"}:
        return {"ok": False, "error": f"Unknown gesture: {gesture}"}

    yaw_min, yaw_max = sorted((_ctx.HEAD_YAW_MIN, _ctx.HEAD_YAW_MAX))
    pitch_min, pitch_max = sorted((_ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX))
    tilt = rest_pose["tilt"]

    if gesture == "yes":
        down_pitch = int(clamp(rest_pose["pitch"] - 122, pitch_min, pitch_max))
        up_pitch = int(clamp(rest_pose["pitch"] + 72, pitch_min, pitch_max))
        sequence = [
            (rest_pose["yaw"], down_pitch, tilt, 0.22),
            (rest_pose["yaw"], up_pitch, tilt, 0.20),
            (rest_pose["yaw"], down_pitch, tilt, 0.20),
            (rest_pose["yaw"], up_pitch, tilt, 0.18),
            (rest_pose["yaw"], rest_pose["pitch"], tilt, 0.24),
        ]
    else:
        left_yaw = int(clamp(rest_pose["yaw"] + 132, yaw_min, yaw_max))
        right_yaw = int(clamp(rest_pose["yaw"] - 132, yaw_min, yaw_max))
        sequence = [
            (left_yaw, rest_pose["pitch"], tilt, 0.24),
            (right_yaw, rest_pose["pitch"], tilt, 0.24),
            (rest_pose["yaw"], rest_pose["pitch"], tilt, 0.26),
        ]

    for yaw, pitch, tilt_val, hold_s in sequence:
        _apply_override_pose(yaw, pitch, tilt_val, hold_s)
        time.sleep(hold_s)

    request_head_pose(**rest_pose)
    return {"ok": True, "gesture": gesture}


def head_hold_worker(maestro):
    if not maestro:
        return

    while not _ctx.shutdown_requested:
        now = time.time()
        track_age = now - _ctx.last_tracking_update
        pitch_min, pitch_max = sorted((_ctx.HEAD_PITCH_MIN, _ctx.HEAD_PITCH_MAX))
        if now < _ctx.head_override_until:
            _ctx.tracking_state = "override"
            desired_yaw = _ctx.head_override_pose["yaw"]
            desired_pitch = _ctx.head_override_pose["pitch"]
            desired_tilt = _ctx.head_override_pose["tilt"]
        elif _ctx.tracking_enabled and now >= _ctx.tracking_resume_at and (now - _ctx.last_tracking_update) < _ctx.TRACKING_LOST_HOLD_S:
            if track_age < _ctx.REACQUIRE_START_S:
                desired_yaw = _ctx.HEAD_NEUTRAL["yaw"] + _ctx.tracked_head_yaw
                desired_pitch = _ctx.HEAD_NEUTRAL["pitch"] + _ctx.tracked_head_pitch
                desired_tilt = _ctx.HEAD_NEUTRAL["tilt"] + int(clamp(_ctx.tracked_lr * 0.30, -110, 110))
                _ctx.tracking_state = "locked"
            else:
                sweep_phase = min(1.0, (track_age - _ctx.REACQUIRE_START_S) / max(1e-6, _ctx.REACQUIRE_SWEEP_S))
                yaw_wave = math.sin(sweep_phase * math.pi * 2.6)
                yaw_envelope = min(1.0, 0.35 + (sweep_phase * 1.20))
                pitch_stage = min(1.0, max(0.0, (sweep_phase - 0.18) / 0.82))
                pitch_wave = math.sin(pitch_stage * math.pi * 1.35)
                pitch_envelope = min(1.0, 0.20 + (pitch_stage * 1.05))
                desired_yaw = _ctx.HEAD_NEUTRAL["yaw"] + int(clamp(
                    _ctx.tracked_head_yaw + (math.copysign(_ctx.REACQUIRE_SWEEP_X, _ctx.last_seen_x_norm or 1.0) * yaw_wave * yaw_envelope),
                    -int(min(abs(_ctx.HEAD_YAW_MAX - _ctx.HEAD_NEUTRAL["yaw"]), abs(_ctx.HEAD_NEUTRAL["yaw"] - _ctx.HEAD_YAW_MIN)) * 0.98),
                    int(min(abs(_ctx.HEAD_YAW_MAX - _ctx.HEAD_NEUTRAL["yaw"]), abs(_ctx.HEAD_NEUTRAL["yaw"] - _ctx.HEAD_YAW_MIN)) * 0.98),
                ))
                desired_pitch = _ctx.HEAD_NEUTRAL["pitch"] + int(clamp(
                    _ctx.tracked_head_pitch + (math.copysign(_ctx.REACQUIRE_SWEEP_Y, _ctx.last_seen_y_norm or 1.0) * pitch_wave * pitch_envelope),
                    -int(min(abs(_ctx.HEAD_PITCH_MAX - _ctx.HEAD_NEUTRAL["pitch"]), abs(_ctx.HEAD_NEUTRAL["pitch"] - _ctx.HEAD_PITCH_MIN)) * 0.98),
                    int(min(abs(_ctx.HEAD_PITCH_MAX - _ctx.HEAD_NEUTRAL["pitch"]), abs(_ctx.HEAD_NEUTRAL["pitch"] - _ctx.HEAD_PITCH_MIN)) * 0.98),
                ))
                desired_tilt = _ctx.HEAD_NEUTRAL["tilt"] + int(clamp(_ctx.last_seen_x_norm * 110.0 * yaw_wave * yaw_envelope, -120, 120))
                _ctx.tracking_state = "reacquiring"
        else:
            _ctx.tracking_state = "idle"
            desired_yaw = _ctx.head_target_pose["yaw"]
            breath_phase = (now % 4.0) / 4.0
            breath_scale = 0.6 if getattr(_ctx, "control_mode", "command") == "intro" else 1.0
            breath_offset = int(round(8 * breath_scale * math.sin(2 * math.pi * breath_phase)))
            desired_pitch = int(clamp(_ctx.head_target_pose["pitch"] + breath_offset, pitch_min, pitch_max))
            desired_tilt = _ctx.head_target_pose["tilt"]

        if _ctx.tracking_enabled and now >= _ctx.tracking_resume_at and (now - _ctx.last_tracking_update) < _ctx.TRACKING_LOST_HOLD_S:
            conf_ratio = clamp(_ctx.tracking_confidence, 0.20, 1.0)
            yaw_alpha = 0.24 + (0.28 * conf_ratio)
            pitch_alpha = 0.22 + (0.30 * conf_ratio)
            tilt_alpha = 0.16 + (0.20 * conf_ratio)
            _ctx.head_current_pose["yaw"] = int((1.0 - yaw_alpha) * _ctx.head_current_pose["yaw"] + yaw_alpha * desired_yaw)
            _ctx.head_current_pose["pitch"] = int((1.0 - pitch_alpha) * _ctx.head_current_pose["pitch"] + pitch_alpha * desired_pitch)
            _ctx.head_current_pose["tilt"] = int((1.0 - tilt_alpha) * _ctx.head_current_pose["tilt"] + tilt_alpha * desired_tilt)
        else:
            _ctx.head_current_pose["yaw"] = int(0.80 * _ctx.head_current_pose["yaw"] + 0.20 * desired_yaw)
            _ctx.head_current_pose["pitch"] = int(0.80 * _ctx.head_current_pose["pitch"] + 0.20 * desired_pitch)
            _ctx.head_current_pose["tilt"] = int(0.82 * _ctx.head_current_pose["tilt"] + 0.18 * desired_tilt)
        _apply_head_tracking_dynamics(
            maestro,
            desired_yaw - _ctx.head_current_pose["yaw"],
            desired_pitch - _ctx.head_current_pose["pitch"],
            _ctx.tracking_confidence,
        )
        set_head_pose(
            maestro,
            yaw=_ctx.head_current_pose["yaw"],
            pitch=_ctx.head_current_pose["pitch"],
            tilt=_ctx.head_current_pose["tilt"],
        )
        time.sleep(0.035)


def eye_movement_worker(maestro):
    if not maestro:
        return

    maestro.set_speed(_ctx.CH_LID_L, 22)
    maestro.set_speed(_ctx.CH_LID_R, 22)
    maestro.set_speed(_ctx.CH_EYE_L_LR, 10)
    maestro.set_speed(_ctx.CH_EYE_R_LR, 10)
    maestro.set_speed(_ctx.CH_EYES_UD, 9)

    set_eyelids(maestro, closed=False)
    set_gaze(maestro, 0, 0)

    next_blink_at = time.time() + random.uniform(1.8, 3.6)
    current_lr = 0
    current_ud = 0

    while not _ctx.shutdown_requested:
        now = time.time()
        in_intro_mode = getattr(_ctx, "control_mode", "command") == "intro"
        blink_base = (1.8, 3.2) if in_intro_mode else ((2.4, 4.0) if _ctx.is_ivan_talking else (1.8, 3.5))

        if now >= next_blink_at:
            set_eyelids(maestro, closed=True)
            time.sleep(random.uniform(0.08, 0.14))
            set_eyelids(maestro, closed=False)
            if random.random() < 0.14 and not _ctx.is_ivan_talking:
                time.sleep(random.uniform(0.06, 0.14))
                set_eyelids(maestro, closed=True)
                time.sleep(random.uniform(0.04, 0.09))
                set_eyelids(maestro, closed=False)
            elif random.random() < 0.12:
                time.sleep(random.uniform(0.02, 0.05))
                set_eyelids(maestro, closed=True)
                time.sleep(random.uniform(0.02, 0.04))
                set_eyelids(maestro, closed=False)
            next_blink_at = now + random.uniform(*blink_base)

        if _ctx.tracking_enabled and time.time() >= _ctx.eye_manual_until and (time.time() - _ctx.last_tracking_update) < _ctx.TRACKING_LOST_HOLD_S:
            set_gaze(maestro, _ctx.tracked_lr, _ctx.tracked_ud)
            time.sleep(0.08 if _ctx.is_ivan_talking else 0.10)
            continue

        if _ctx.gaze_hold_enabled:
            set_gaze(maestro, _ctx.gaze_hold_lr, _ctx.gaze_hold_ud)
            time.sleep(0.08)
            continue

        if _ctx.is_ivan_talking:
            if random.random() < 0.38:
                target_lr = random.randint(-34, 34)
                target_ud = random.randint(-22, 16)
                current_lr = _lerp_int(current_lr, target_lr, 0.24)
                current_ud = _lerp_int(current_ud, target_ud, 0.22)
                set_gaze(maestro, current_lr, current_ud)
            time.sleep(random.uniform(0.12, 0.18))
            continue

        if in_intro_mode:
            r = random.random()
            if r < 0.54:
                target_lr = clamp(current_lr + random.randint(-14, 14), -62, 62)
                target_ud = clamp(current_ud + random.randint(-9, 9), -42, 16)
                current_lr = _lerp_int(current_lr, target_lr, 0.52)
                current_ud = _lerp_int(current_ud, target_ud, 0.46)
                set_gaze(maestro, current_lr, current_ud)
                time.sleep(random.uniform(0.14, 0.30))
            elif r < 0.82:
                target_lr = random.randint(-58, 58)
                target_ud = random.randint(-34, 12)
                current_lr = _lerp_int(current_lr, target_lr, 0.36)
                current_ud = _lerp_int(current_ud, target_ud, 0.32)
                set_gaze(maestro, current_lr, current_ud)
                time.sleep(random.uniform(0.24, 0.52))
            elif r < 0.92:
                current_lr = _lerp_int(current_lr, 0, 0.18)
                current_ud = _lerp_int(current_ud, -8, 0.14)
                set_gaze(maestro, current_lr, current_ud)
                time.sleep(random.uniform(0.18, 0.36))
            else:
                time.sleep(random.uniform(0.08, 0.18))
            continue

        r = random.random()
        if r < 0.48:
            target_lr = clamp(current_lr + random.randint(-20, 20), -88, 88)
            target_ud = clamp(current_ud + random.randint(-14, 14), -58, 52)
            current_lr = _lerp_int(current_lr, target_lr, 0.56)
            current_ud = _lerp_int(current_ud, target_ud, 0.52)
            set_gaze(maestro, current_lr, current_ud)
            time.sleep(random.uniform(0.10, 0.24))
        elif r < 0.74:
            target_lr = random.randint(-76, 76)
            target_ud = random.randint(-48, 44)
            current_lr = _lerp_int(current_lr, target_lr, 0.44)
            current_ud = _lerp_int(current_ud, target_ud, 0.40)
            set_gaze(maestro, current_lr, current_ud)
            time.sleep(random.uniform(0.20, 0.54))
        elif r < 0.90:
            current_lr = _lerp_int(current_lr, 0, 0.58)
            current_ud = _lerp_int(current_ud, 0, 0.58)
            set_gaze(maestro, current_lr, current_ud)
            time.sleep(random.uniform(0.14, 0.32))
        else:
            time.sleep(random.uniform(0.08, 0.16))


def init_maestro():
    servo_port = get_maestro_port()
    try:
        if servo_port:
            _ctx.maestro = ServoController(port=servo_port)
            load_calibration_file()
            _apply_calibration_to_maestro(_ctx.maestro)
            apply_servo_calibration(_ctx.maestro)
            _reset_head_state_to_neutral()
            for channel in (_ctx.CH_EYE_L_LR, _ctx.CH_LID_L, _ctx.CH_LID_R, _ctx.CH_EYE_R_LR, _ctx.CH_EYES_UD):
                _ctx.maestro.set_speed(channel, 60)
                _ctx.maestro.set_accel(channel, 8)
            for channel in (_ctx.CH_FACE_PITCH, _ctx.CH_FACE_YAW, _ctx.CH_HEAD_TILT):
                _ctx.maestro.set_speed(channel, 35)
                _ctx.maestro.set_accel(channel, 8)
            _ctx.maestro.set_speed(_ctx.CH_JAW, 45)
            _ctx.maestro.set_accel(_ctx.CH_JAW, 0)
            _ctx.maestro.set_target(_ctx.CH_JAW, _ctx.JAW_CLOSED)
            set_head_pose(_ctx.maestro, yaw=_ctx.HEAD_NEUTRAL["yaw"], pitch=_ctx.HEAD_NEUTRAL["pitch"], tilt=_ctx.HEAD_NEUTRAL["tilt"])
            print(f"Maestro connected at {servo_port}")
        else:
            raise RuntimeError("No /dev/ttyACM0 or /dev/ttyACM1 found")
    except Exception as e:
        print(f"Maestro not connected: {e}")
        _ctx.maestro = None


def set_tracking_target(frame_w, frame_h, center_x, center_y):
    if frame_w <= 0 or frame_h <= 0:
        return

    yaw_limit = int(max(40, min(
        abs(_ctx.HEAD_YAW_MAX - _ctx.HEAD_NEUTRAL["yaw"]),
        abs(_ctx.HEAD_NEUTRAL["yaw"] - _ctx.HEAD_YAW_MIN),
    ) * 0.98))
    pitch_limit = int(max(35, min(
        abs(_ctx.HEAD_PITCH_MAX - _ctx.HEAD_NEUTRAL["pitch"]),
        abs(_ctx.HEAD_NEUTRAL["pitch"] - _ctx.HEAD_PITCH_MIN),
    ) * 0.98))

    now = time.time()
    prev_update = _ctx.last_tracking_update
    raw_x_norm = (center_x / frame_w) - 0.5
    raw_y_norm = (center_y / frame_h) - 0.5
    centered_x = abs(raw_x_norm) < _ctx.TRACK_CENTER_HOLD_X
    centered_y = abs(raw_y_norm) < _ctx.TRACK_CENTER_HOLD_Y
    dt = now - prev_update if prev_update > 0.0 else 0.0
    if dt > 1e-4:
        inst_vx = (raw_x_norm - _ctx.last_target_norm_x) / dt
        inst_vy = (raw_y_norm - _ctx.last_target_norm_y) / dt
        _ctx.last_target_velocity_x = (0.55 * _ctx.last_target_velocity_x) + (0.45 * inst_vx)
        _ctx.last_target_velocity_y = (0.55 * _ctx.last_target_velocity_y) + (0.45 * inst_vy)
    predicted_x_norm = raw_x_norm if centered_x else raw_x_norm + (_ctx.last_target_velocity_x * _ctx.TRACK_PREDICTION_S)
    predicted_y_norm = raw_y_norm if centered_y else raw_y_norm + (_ctx.last_target_velocity_y * _ctx.TRACK_PREDICTION_S)
    x_norm = clamp(predicted_x_norm, raw_x_norm - _ctx.TRACK_PREDICTION_MAX_X, raw_x_norm + _ctx.TRACK_PREDICTION_MAX_X)
    y_norm = clamp(predicted_y_norm, raw_y_norm - _ctx.TRACK_PREDICTION_MAX_Y, raw_y_norm + _ctx.TRACK_PREDICTION_MAX_Y)
    x_norm = clamp(x_norm, -0.5, 0.5)
    y_norm = clamp(y_norm, -0.5, 0.5)
    _ctx.last_target_norm_x = raw_x_norm
    _ctx.last_target_norm_y = raw_y_norm
    _ctx.last_seen_x_norm = x_norm
    _ctx.last_seen_y_norm = y_norm
    _ctx.tracking_state = "locked"
    x_track = _soft_track_error(x_norm, _ctx.HEAD_TRACK_DEADZONE_X, _ctx.HEAD_TRACK_EDGE_SOFTEN_X)
    y_track = _soft_track_error(y_norm, _ctx.HEAD_TRACK_DEADZONE_Y, _ctx.HEAD_TRACK_EDGE_SOFTEN_Y)

    head_allowed = now >= _ctx.tracking_head_enable_at
    if (abs(x_track) > 0.0 or abs(y_track) > 0.0) and (prev_update == 0.0 or (now - prev_update) > 0.30):
        _ctx.tracking_head_enable_at = now + _ctx.EYE_FIRST_HEAD_DELAY_S
        head_allowed = False

    if centered_x:
        _ctx.tracked_head_yaw = int(0.72 * _ctx.tracked_head_yaw)
    elif x_track and head_allowed:
        desired_head_yaw = _ctx.HEAD_TRACK_X_SIGN * x_track * yaw_limit * _ctx.HEAD_TRACK_GAIN_X
        _ctx.tracked_head_yaw = int(clamp(0.80 * _ctx.tracked_head_yaw + 0.20 * desired_head_yaw, -yaw_limit, yaw_limit))
    else:
        _ctx.tracked_head_yaw = int(0.86 * _ctx.tracked_head_yaw)

    if centered_y:
        _ctx.tracked_head_pitch = int(0.80 * _ctx.tracked_head_pitch)
    elif y_track and head_allowed:
        desired_head_pitch = _ctx.HEAD_TRACK_Y_SIGN * y_track * pitch_limit * _ctx.HEAD_TRACK_GAIN_Y
        _ctx.tracked_head_pitch = int(clamp(0.62 * _ctx.tracked_head_pitch + 0.38 * desired_head_pitch, -pitch_limit, pitch_limit))
    else:
        _ctx.tracked_head_pitch = int(0.90 * _ctx.tracked_head_pitch)

    head_x_norm = 0.0 if yaw_limit <= 0 else (-_ctx.HEAD_TRACK_X_SIGN * _ctx.tracked_head_yaw) / max(1.0, yaw_limit)
    head_y_norm = 0.0 if pitch_limit <= 0 else (-_ctx.HEAD_TRACK_Y_SIGN * _ctx.tracked_head_pitch) / max(1.0, pitch_limit)
    residual_x = clamp(x_norm - head_x_norm, -0.40, 0.40)
    residual_y = clamp(y_norm - head_y_norm, -0.36, 0.36)
    target_lr = int(clamp(_ctx.TRACK_X_SIGN * residual_x * 325, -180, 180))
    target_ud = int(clamp(_ctx.TRACK_Y_SIGN * residual_y * 240, -130, 130))

    if centered_x:
        _ctx.tracked_lr = int(0.58 * _ctx.tracked_lr)
    else:
        _ctx.tracked_lr = int(0.55 * _ctx.tracked_lr + 0.45 * target_lr)
    if centered_y:
        _ctx.tracked_ud = int(0.70 * _ctx.tracked_ud)
    else:
        _ctx.tracked_ud = int(0.55 * _ctx.tracked_ud + 0.45 * target_ud)
    _ctx.last_tracking_update = now
