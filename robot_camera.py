import asyncio
import os
import time


_ctx = None


def initialize(context):
    global _ctx
    _ctx = context


class CameraManager:
    def __init__(self):
        self.picam2 = None
        self.latest_jpeg = None
        self.prev_gray = None
        self.running = False
        self.face_cascade = None
        self.face_detector = None
        self.person_detector = None
        self.frame_index = 0
        self.last_face = None
        self.last_face_at = 0.0
        self.primary_face_center = None
        self.primary_face_box = None
        self.primary_face_at = 0.0
        self.last_target = None
        self.last_target_at = 0.0
        self.smoothed_target = None
        self.detect_box = None
        self.detect_box_frame_size = None
        self.detect_label = ""
        self.detect_color = (60, 255, 120)
        self.detect_at = 0.0
        self.motion_blur = None
        if _ctx.CAMERA_AVAILABLE:
            cascade_path = os.path.join(_ctx.cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            self.face_cascade = _ctx.cv2.CascadeClassifier(cascade_path)
            try:
                self.person_detector = _ctx.cv2.HOGDescriptor()
                self.person_detector.setSVMDetector(_ctx.cv2.HOGDescriptor_getDefaultPeopleDetector())
            except Exception:
                self.person_detector = None
        if _ctx.MEDIAPIPE_AVAILABLE:
            try:
                self.face_detector = _ctx.mp.solutions.face_detection.FaceDetection(
                    model_selection=0,
                    min_detection_confidence=_ctx.FACE_DETECTION_CONFIDENCE,
                )
            except Exception:
                self.face_detector = None

    async def start(self):
        if not _ctx.CAMERA_AVAILABLE or self.picam2 is not None:
            return

        if self.face_detector is None and _ctx.MEDIAPIPE_AVAILABLE:
            try:
                self.face_detector = _ctx.mp.solutions.face_detection.FaceDetection(
                    model_selection=0,
                    min_detection_confidence=_ctx.FACE_DETECTION_CONFIDENCE,
                )
            except Exception:
                self.face_detector = None

        self.picam2 = _ctx.Picamera2()
        config = self.picam2.create_preview_configuration(main={"format": "RGB888", "size": _ctx.CAMERA_CAPTURE_SIZE})
        self.picam2.configure(config)
        self.picam2.start()
        try:
            self.picam2.set_controls(
                {
                    "AeEnable": True,
                    "AwbEnable": False,
                    "ColourGains": (1.6, 2.4),
                    "Contrast": 1.10,
                    "Sharpness": 1.45,
                }
            )
        except Exception:
            pass
        self.running = True
        print("Raspberry Pi AI camera stream active.")

    def _prepare_model_frame(self, frame_bgr):
        model_frame = frame_bgr
        h, w = model_frame.shape[:2]
        max_w, max_h = _ctx.MODEL_FRAME_MAX_SIZE
        scale = min(max_w / max(1, w), max_h / max(1, h))
        if scale < 0.98 or scale > 1.02:
            model_frame = _ctx.cv2.resize(
                model_frame,
                (int(round(w * scale)), int(round(h * scale))),
                interpolation=_ctx.cv2.INTER_CUBIC if scale > 1.0 else _ctx.cv2.INTER_AREA,
            )
        return model_frame

    def _enhance_frame(self, frame_bgr):
        lab = _ctx.cv2.cvtColor(frame_bgr, _ctx.cv2.COLOR_BGR2LAB)
        l, a, bb = _ctx.cv2.split(lab)
        mean_l = float(_ctx.np.mean(l))
        clahe = _ctx.cv2.createCLAHE(clipLimit=1.7, tileGridSize=(8, 8))
        l = clahe.apply(l)
        if mean_l < _ctx.LIGHT_LOW_MEAN:
            alpha = 1.10 + ((_ctx.LIGHT_LOW_MEAN - mean_l) / max(1.0, _ctx.LIGHT_LOW_MEAN)) * 0.28
            beta = 8 + int((_ctx.LIGHT_LOW_MEAN - mean_l) * 0.20)
            l = _ctx.cv2.convertScaleAbs(l, alpha=alpha, beta=beta)
        elif mean_l > _ctx.LIGHT_HIGH_MEAN:
            alpha = 0.96
            beta = -int((mean_l - _ctx.LIGHT_HIGH_MEAN) * 0.10)
            l = _ctx.cv2.convertScaleAbs(l, alpha=alpha, beta=beta)
        enhanced = _ctx.cv2.cvtColor(_ctx.cv2.merge([l, a, bb]), _ctx.cv2.COLOR_LAB2BGR)
        gamma = 1.08
        lut = _ctx.np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in _ctx.np.arange(256)], dtype=_ctx.np.uint8)
        enhanced = _ctx.cv2.LUT(enhanced, lut)
        blur = _ctx.cv2.GaussianBlur(enhanced, (0, 0), 1.1)
        sharpened = _ctx.cv2.addWeighted(enhanced, 1.30, blur, -0.30, 0)
        return _ctx.cv2.convertScaleAbs(sharpened, alpha=1.03, beta=5)

    def _track_from_frame(self, frame_bgr):
        if not _ctx.tracking_enabled:
            self.detect_box = None
            self.detect_box_frame_size = None
            self.detect_label = ""
            self.detect_color = (60, 255, 120)
            _ctx.tracked_target_kind = ""
            _ctx.tracking_state = "idle"
            _ctx.tracking_confidence = 0.0
            return

        h, w = frame_bgr.shape[:2]
        frame_small = _ctx.cv2.resize(frame_bgr, (320, 240))
        gray_full = _ctx.cv2.cvtColor(frame_bgr, _ctx.cv2.COLOR_BGR2GRAY)
        gray = _ctx.cv2.resize(gray_full, (320, 240))
        self.frame_index += 1

        faces = []
        roi_box = None
        if self.primary_face_box and (time.time() - self.primary_face_at) < _ctx.PRIMARY_FACE_LOCK_S:
            roi_box = _ctx._build_roi_from_box(
                self.primary_face_box,
                320,
                240,
                expand=_ctx.FACE_ROI_EXPAND,
                min_size=_ctx.FACE_ROI_MIN_SIZE,
            )
        if self.face_detector is not None:
            if roi_box is not None:
                rx, ry, rw, rh = roi_box
                roi_rgb = _ctx.cv2.cvtColor(frame_small[ry:ry + rh, rx:rx + rw], _ctx.cv2.COLOR_BGR2RGB)
                result = self.face_detector.process(roi_rgb)
                faces = _ctx._offset_boxes(
                    _ctx._mediapipe_detections_to_faces(getattr(result, "detections", None), rw, rh),
                    rx,
                    ry,
                )
            if len(faces) == 0:
                rgb_small = _ctx.cv2.cvtColor(frame_small, _ctx.cv2.COLOR_BGR2RGB)
                result = self.face_detector.process(rgb_small)
                faces = _ctx._mediapipe_detections_to_faces(getattr(result, "detections", None), 320, 240)
        if len(faces) == 0 and self.face_cascade is not None and not self.face_cascade.empty():
            if roi_box is not None:
                rx, ry, rw, rh = roi_box
                roi_gray = gray[ry:ry + rh, rx:rx + rw]
                roi_faces = self.face_cascade.detectMultiScale(
                    roi_gray,
                    scaleFactor=1.08,
                    minNeighbors=6,
                    minSize=(36, 36),
                )
                faces = _ctx._offset_boxes(roi_faces, rx, ry)
            if len(faces) == 0:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.10, minNeighbors=6, minSize=(40, 40))

        if len(faces) > 0:
            locked_center = None
            if self.primary_face_center and (time.time() - self.primary_face_at) < _ctx.PRIMARY_FACE_LOCK_S:
                locked_center = self.primary_face_center
            face = _ctx._pick_primary_face(faces, 320.0, 240.0, locked_center)
            x, y, fw, fh = face[:4]
            face_conf = float(face[4]) if len(face) > 4 else _ctx.FACE_DETECTION_CONFIDENCE
            sx = w / 320.0
            sy = h / 240.0
            cx = (x + fw / 2) * sx
            cy = (y + fh / 2) * sy
            self.smoothed_target = _ctx._smooth_point(self.smoothed_target, (cx, cy), _ctx.TRACK_TARGET_SMOOTHING)
            smooth_x, smooth_y = self.smoothed_target
            self.primary_face_center = ((x + (fw * 0.5)) / 320.0, (y + (fh * 0.5)) / 240.0)
            self.primary_face_box = (x, y, fw, fh)
            self.primary_face_at = time.time()
            self.detect_box = (int(x * sx), int(y * sy), int(fw * sx), int(fh * sy))
            self.detect_box_frame_size = (w, h)
            self.detect_label = "Primary Face"
            self.detect_color = (80, 220, 255)
            self.detect_at = time.time()
            _ctx.tracked_target_kind = "face"
            _ctx.tracking_confidence = _ctx.clamp(0.55 + (0.45 * float(face_conf)), 0.0, 1.0)
            self.last_face = (int(smooth_x), int(smooth_y))
            self.last_face_at = time.time()
            self.last_target = self.last_face
            self.last_target_at = self.last_face_at
            _ctx.set_tracking_target(w, h, smooth_x, smooth_y)
            return

        person_boxes = []
        if self.person_detector is not None and (self.frame_index % _ctx.PERSON_DETECTION_STRIDE == 0):
            rects, weights = self.person_detector.detectMultiScale(
                frame_small,
                winStride=(8, 8),
                padding=(8, 8),
                scale=1.05,
            )
            person_boxes = [
                (
                    int((x / 320.0) * w),
                    int((y / 240.0) * h),
                    int((bw / 320.0) * w),
                    int((bh / 240.0) * h),
                )
                for (x, y, bw, bh), weight in zip(rects, weights)
                if bw >= 36 and bh >= 72 and float(weight) >= _ctx.PERSON_DETECTION_WEIGHT_MIN
            ]

        if person_boxes:
            locked_center = None
            if self.last_target and (time.time() - self.last_target_at) < _ctx.TRACK_TARGET_HOLD_S:
                locked_center = (self.last_target[0] / max(1.0, w), self.last_target[1] / max(1.0, h))
            x, y, bw, bh = _ctx._pick_primary_box(person_boxes, float(w), float(h), locked_center)
            cx = x + (bw * 0.5)
            cy = y + (bh * 0.35)
            self.smoothed_target = _ctx._smooth_point(self.smoothed_target, (cx, cy), _ctx.TRACK_MOTION_SMOOTHING)
            smooth_x, smooth_y = self.smoothed_target
            self.detect_box = (int(x), int(y), int(bw), int(bh))
            self.detect_box_frame_size = (w, h)
            self.detect_label = "Person"
            self.detect_color = (120, 255, 80)
            self.detect_at = time.time()
            _ctx.tracked_target_kind = "person"
            _ctx.tracking_confidence = 0.62
            self.last_target = (int(smooth_x), int(smooth_y))
            self.last_target_at = time.time()
            _ctx.set_tracking_target(w, h, smooth_x, smooth_y)
            self.prev_gray = gray
            return

        if self.last_face and (time.time() - self.last_face_at) < _ctx.TRACK_FACE_PRIORITY_HOLD_S:
            self.last_target = self.last_face
            self.last_target_at = time.time()
            self.detect_box = None
            self.detect_box_frame_size = None
            self.detect_label = ""
            _ctx.tracked_target_kind = "face-hold"
            _ctx.tracking_confidence = 0.46
            _ctx.set_tracking_target(w, h, self.last_face[0], self.last_face[1])
            self.prev_gray = gray
            return

        if self.last_target and (time.time() - self.last_target_at) < _ctx.TRACK_TARGET_HOLD_S:
            self.detect_box = None
            self.detect_box_frame_size = None
            self.detect_label = ""
            _ctx.tracked_target_kind = "hold"
            _ctx.tracking_confidence = 0.34
            _ctx.set_tracking_target(w, h, self.last_target[0], self.last_target[1])
            self.prev_gray = gray
            return
        elif self.smoothed_target is not None:
            self.smoothed_target = _ctx._smooth_point(self.smoothed_target, (w * 0.5, h * 0.5), 0.08)
            if self.primary_face_center and (time.time() - self.primary_face_at) > _ctx.PRIMARY_FACE_LOCK_S:
                self.primary_face_center = None
                self.primary_face_box = None
            _ctx.tracked_target_kind = ""
            _ctx.tracking_confidence = 0.18

        if self.detect_box is not None and (time.time() - self.detect_at) > 0.30:
            self.detect_box = None
            self.detect_box_frame_size = None
            self.detect_label = ""
            self.detect_color = (60, 255, 120)

        self.prev_gray = gray

    def _draw_hud(self, frame):
        now = time.time()
        if _ctx.tracking_enabled:
            h, w = frame.shape[:2]
            cx = w // 2
            cy = h // 2
            dz_w = int(w * _ctx.HEAD_TRACK_DEADZONE_X * 2.0)
            dz_h = int(h * _ctx.HEAD_TRACK_DEADZONE_Y * 2.0)
            _ctx.cv2.rectangle(frame, (cx - dz_w, cy - dz_h), (cx + dz_w, cy + dz_h), (80, 180, 255), 1)
            _ctx.cv2.line(frame, (cx - 14, cy), (cx + 14, cy), (255, 210, 90), 1)
            _ctx.cv2.line(frame, (cx, cy - 14), (cx, cy + 14), (255, 210, 90), 1)
            yaw_span = max(1.0, min(abs(_ctx.HEAD_YAW_MAX - _ctx.HEAD_NEUTRAL["yaw"]), abs(_ctx.HEAD_NEUTRAL["yaw"] - _ctx.HEAD_YAW_MIN)) * 0.98)
            pitch_span = max(1.0, min(abs(_ctx.HEAD_PITCH_MAX - _ctx.HEAD_NEUTRAL["pitch"]), abs(_ctx.HEAD_NEUTRAL["pitch"] - _ctx.HEAD_PITCH_MIN)) * 0.98)
            yaw_ratio = abs(_ctx.tracked_head_yaw) / yaw_span
            pitch_ratio = abs(_ctx.tracked_head_pitch) / pitch_span
            if yaw_ratio >= _ctx.LIMIT_WARN_RATIO:
                side_x = 20 if _ctx.tracked_head_yaw > 0 else (w - 20)
                _ctx.cv2.circle(frame, (side_x, cy), 7, (60, 120, 255), -1)
            if pitch_ratio >= _ctx.LIMIT_WARN_RATIO:
                side_y = 20 if _ctx.tracked_head_pitch > 0 else (h - 20)
                _ctx.cv2.circle(frame, (cx, side_y), 7, (60, 120, 255), -1)
        if self.detect_box is not None:
            x, y, bw, bh = self.detect_box
            if self.detect_box_frame_size:
                src_w, src_h = self.detect_box_frame_size
                if src_w > 0 and src_h > 0:
                    scale_x = frame.shape[1] / src_w
                    scale_y = frame.shape[0] / src_h
                    x = int(round(x * scale_x))
                    y = int(round(y * scale_y))
                    bw = int(round(bw * scale_x))
                    bh = int(round(bh * scale_y))
            x = int(_ctx.clamp(x, 0, max(0, frame.shape[1] - 1)))
            y = int(_ctx.clamp(y, 0, max(0, frame.shape[0] - 1)))
            bw = int(_ctx.clamp(bw, 1, frame.shape[1] - x))
            bh = int(_ctx.clamp(bh, 1, frame.shape[0] - y))
            box_color = tuple(int(c) for c in self.detect_color)
            _ctx.cv2.rectangle(frame, (x, y), (x + bw, y + bh), box_color, 2)
            if self.detect_label:
                _ctx.cv2.putText(frame, self.detect_label, (x, max(18, y - 8)), _ctx.cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, _ctx.cv2.LINE_AA)
                _ctx.cv2.putText(frame, self.detect_label, (x, max(18, y - 8)), _ctx.cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_color, 1, _ctx.cv2.LINE_AA)
        if _ctx.tracking_enabled:
            state_text = f"Tracking: {_ctx.tracking_state}"
            if _ctx.tracked_target_kind:
                state_text += f" ({_ctx.tracked_target_kind})"
            _ctx.cv2.putText(frame, state_text, (12, 24), _ctx.cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 4, _ctx.cv2.LINE_AA)
            _ctx.cv2.putText(frame, state_text, (12, 24), _ctx.cv2.FONT_HERSHEY_SIMPLEX, 0.58, (120, 220, 255), 1, _ctx.cv2.LINE_AA)
        caption_blocks = []
        if getattr(_ctx, "latest_user_transcription", "") and (now - getattr(_ctx, "latest_user_transcription_at", 0.0)) < 8.0:
            caption_blocks.append(("Heard", _ctx.latest_user_transcription, (90, 255, 120)))
        if getattr(_ctx, "latest_model_transcription", "") and (now - getattr(_ctx, "latest_model_transcription_at", 0.0)) < 8.0:
            caption_blocks.append(("Said", _ctx.latest_model_transcription, (120, 220, 255)))

        if caption_blocks:
            max_chars = 60
            rendered_lines = []
            for label, text, color in caption_blocks:
                remaining = text
                label_used = False
                while remaining and len(rendered_lines) < 5:
                    split_at = remaining.rfind(" ", 0, max_chars)
                    if len(remaining) <= max_chars:
                        split_at = len(remaining)
                    elif split_at <= 0:
                        split_at = max_chars
                    chunk = remaining[:split_at].strip()
                    remaining = remaining[split_at:].strip()
                    prefix = f"{label}: " if not label_used else ""
                    label_used = True
                    rendered_lines.append((f"{prefix}{chunk}", color))
            y0 = frame.shape[0] - 18 - (len(rendered_lines) - 1) * 22
            for idx, (line, color) in enumerate(rendered_lines):
                y = y0 + idx * 22
                _ctx.cv2.putText(frame, line, (12, y), _ctx.cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 4, _ctx.cv2.LINE_AA)
                _ctx.cv2.putText(frame, line, (12, y), _ctx.cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 1, _ctx.cv2.LINE_AA)

    async def capture_loop(self):
        if not _ctx.CAMERA_AVAILABLE:
            print("Camera modules unavailable (cv2/picamera2 missing). Running audio-only.")
            return

        while not _ctx.shutdown_requested:
            try:
                if self.picam2 is None:
                    await self.start()

                frame = self.picam2.capture_array()
                frame = _ctx.cv2.rotate(frame, _ctx.cv2.ROTATE_180)
                frame = self._enhance_frame(frame)
                _ctx.latest_camera_frame = frame.copy()
                self._track_from_frame(frame)
                model_frame = self._prepare_model_frame(frame)
                display_frame = _ctx.cv2.resize(frame, _ctx.CAMERA_DISPLAY_SIZE, interpolation=_ctx.cv2.INTER_AREA)
                self._draw_hud(display_frame)

                try:
                    _ctx.cv2.imshow("Ivan AI Camera", display_frame)
                    _ctx.cv2.waitKey(1)
                except Exception:
                    pass

                ok, buf = _ctx.cv2.imencode(".jpg", model_frame, [int(_ctx.cv2.IMWRITE_JPEG_QUALITY), _ctx.MODEL_JPEG_QUALITY])
                if ok:
                    self.latest_jpeg = buf.tobytes()

                await asyncio.sleep(0.02)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Camera stream error: {e}")
                await self.stop()
                await asyncio.sleep(0.8)

    async def stop(self):
        self.running = False
        if self.picam2 is not None:
            try:
                self.picam2.stop()
            except Exception:
                pass
            try:
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None
        if self.face_detector is not None:
            try:
                self.face_detector.close()
            except Exception:
                pass
            self.face_detector = None
        try:
            _ctx.cv2.destroyAllWindows()
        except Exception:
            pass
