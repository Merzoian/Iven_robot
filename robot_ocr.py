import re
import shutil
import subprocess
import tempfile

from robot_logging import log_event


_ctx = None


def initialize(context):
    global _ctx
    _ctx = context
    _ctx.ocr_available = bool(shutil.which(_ctx.OCR_COMMAND))


def _extract_math_expression(text):
    if not text:
        return None
    match = re.search(r"([0-9][0-9\s+\-*/().=xX]{1,40}[0-9)])", text)
    if match:
        return " ".join(match.group(1).split())
    match = re.search(r"([0-9][0-9\s+\-*/().=xX]{1,40}[0-9])", text)
    if match:
        return " ".join(match.group(1).split())
    return None


def _center_crop(frame_bgr, crop_ratio):
    h = len(frame_bgr)
    w = len(frame_bgr[0]) if h else 0
    crop_ratio = max(0.25, min(1.0, float(crop_ratio)))
    crop_w = max(1, int(round(w * crop_ratio)))
    crop_h = max(1, int(round(h * crop_ratio)))
    x0 = max(0, (w - crop_w) // 2)
    y0 = max(0, (h - crop_h) // 2)
    try:
        return frame_bgr[y0:y0 + crop_h, x0:x0 + crop_w]
    except TypeError:
        return [row[x0:x0 + crop_w] for row in frame_bgr[y0:y0 + crop_h]]


def _preprocess_variants(frame_bgr, mode="auto"):
    gray = _ctx.cv2.cvtColor(frame_bgr, _ctx.cv2.COLOR_BGR2GRAY)
    scale = 2.4 if mode == "document" else 2.0
    upscaled = _ctx.cv2.resize(gray, None, fx=scale, fy=scale, interpolation=_ctx.cv2.INTER_CUBIC)
    median = _ctx.cv2.medianBlur(upscaled, 3)
    _, otsu = _ctx.cv2.threshold(median, 0, 255, _ctx.cv2.THRESH_BINARY + _ctx.cv2.THRESH_OTSU)
    adaptive = _ctx.cv2.adaptiveThreshold(
        median,
        255,
        _ctx.cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        _ctx.cv2.THRESH_BINARY,
        31,
        11,
    )
    variants = [upscaled, otsu, adaptive]
    if mode == "document":
        _, inv_otsu = _ctx.cv2.threshold(median, 0, 255, _ctx.cv2.THRESH_BINARY_INV + _ctx.cv2.THRESH_OTSU)
        variants.append(inv_otsu)
    return variants


def _score_text(text):
    if not text:
        return 0
    alnum = sum(ch.isalnum() for ch in text)
    math_chars = sum(ch in "+-*/=()xX" for ch in text)
    spaces = sum(ch.isspace() for ch in text)
    return (alnum * 3) + (math_chars * 4) + spaces


def _run_tesseract(image, psm):
    ok, encoded = _ctx.cv2.imencode(".png", image)
    if not ok:
        return ""
    with tempfile.NamedTemporaryFile(suffix=".png") as temp_file:
        temp_file.write(encoded.tobytes())
        temp_file.flush()
        result = subprocess.run(
            [
                _ctx.OCR_COMMAND,
                temp_file.name,
                "stdout",
                "--oem",
                "3",
                "--psm",
                str(psm),
                "-l",
                _ctx.OCR_LANG,
                "-c",
                "preserve_interword_spaces=1",
            ],
            capture_output=True,
            text=True,
            timeout=_ctx.OCR_TIMEOUT_S,
            check=False,
        )
    return " ".join((result.stdout or "").split()).strip()


def read_visible_text(mode="auto"):
    frame = getattr(_ctx, "latest_camera_frame", None)
    if frame is None:
        return {"ok": False, "error": "No camera frame is available yet"}

    if not getattr(_ctx, "ocr_available", False):
        return {
            "ok": False,
            "error": "Local OCR is unavailable. Install the tesseract binary to enable it.",
        }

    mode = str(mode or "auto").lower().strip()
    if mode not in {"auto", "document"}:
        mode = "auto"

    frames_to_try = [(frame, _ctx.OCR_PSM, "full-frame", "auto")]
    if mode == "document":
        frames_to_try.insert(
            0,
            (
                _center_crop(frame, _ctx.OCR_DOCUMENT_CROP_RATIO),
                _ctx.OCR_DOCUMENT_PSM,
                "document-crop",
                "document",
            ),
        )

    best_text = ""
    best_score = -1
    best_source = "full-frame"
    try:
        for candidate_frame, psm, source, variant_mode in frames_to_try:
            for variant in _preprocess_variants(candidate_frame, mode=variant_mode):
                text = _run_tesseract(variant, psm)
                score = _score_text(text)
                if score > best_score:
                    best_text = text
                    best_score = score
                    best_source = source
        if not best_text:
            return {"ok": False, "error": "No readable text detected in the current frame"}
        expression = _extract_math_expression(best_text)
        log_event(
            _ctx.logger,
            "info",
            "ocr_read",
            mode=mode,
            source=best_source,
            text=best_text[:120],
            math_expression=expression,
        )
        return {
            "ok": True,
            "text": best_text,
            "math_expression": expression,
            "engine": "tesseract",
            "mode": mode,
            "source": best_source,
        }
    except Exception as e:
        log_event(_ctx.logger, "warning", "ocr_error", error=str(e))
        return {"ok": False, "error": f"OCR failed: {e}"}
