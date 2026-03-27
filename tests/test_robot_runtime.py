import os
import tempfile
import unittest

from robot_runtime import RobotConfig, load_robot_config


class RobotRuntimeConfigTests(unittest.TestCase):
    def setUp(self):
        self.default_config = RobotConfig(
            LOG_NAME="ivan.robot",
            LOG_LEVEL="INFO",
            MIC_INDEX=1,
            SPEAKER_INDEX=2,
            SAMPLE_RATE=48000,
            CHUNK=2048,
            CH_EYE_L_LR=1,
            CH_LID_L=2,
            CH_LID_R=3,
            CH_EYE_R_LR=4,
            CH_EYES_UD=5,
            CH_JAW=6,
            CH_FACE_PITCH=7,
            CH_FACE_YAW=8,
            CH_HEAD_TILT=9,
            CH_YAW=8,
            CH_TILT=9,
            TRACK_X_SIGN=1.0,
            TRACK_Y_SIGN=-1.0,
            HEAD_TRACK_X_SIGN=-1.0,
            HEAD_TRACK_Y_SIGN=-1.0,
            HEAD_TRACK_GAIN_X=1.2,
            HEAD_TRACK_GAIN_Y=1.46,
            HEAD_TRACK_DEADZONE_X=0.08,
            HEAD_TRACK_DEADZONE_Y=0.04,
            HEAD_TRACK_SETTLE_X=0.1,
            HEAD_TRACK_SETTLE_Y=0.08,
            HEAD_TRACK_EDGE_SOFTEN_X=0.75,
            HEAD_TRACK_EDGE_SOFTEN_Y=0.8,
            TRACK_CENTER_HOLD_X=0.12,
            TRACK_CENTER_HOLD_Y=0.07,
            TRACK_TARGET_SMOOTHING=0.42,
            TRACK_MOTION_SMOOTHING=0.28,
            TRACK_TARGET_HOLD_S=0.8,
            TRACK_FACE_PRIORITY_HOLD_S=1.0,
            PRIMARY_FACE_LOCK_S=1.4,
            PRIMARY_FACE_MATCH_NORM=0.18,
            FACE_ROI_EXPAND=1.9,
            FACE_ROI_MIN_SIZE=84,
            FACE_DETECTION_CONFIDENCE=0.58,
            PERSON_DETECTION_STRIDE=1,
            PERSON_DETECTION_WEIGHT_MIN=0.15,
            EYE_FIRST_HEAD_DELAY_S=0.18,
            REACQUIRE_START_S=0.3,
            REACQUIRE_SWEEP_S=3.4,
            REACQUIRE_SWEEP_X=220,
            REACQUIRE_SWEEP_Y=95,
            TRACK_PREDICTION_S=0.1,
            TRACK_PREDICTION_MAX_X=0.06,
            TRACK_PREDICTION_MAX_Y=0.1,
            LIGHT_LOW_MEAN=72.0,
            LIGHT_HIGH_MEAN=182.0,
            LIMIT_WARN_RATIO=0.9,
            HEAD_TRACK_SPEED_MIN=18,
            HEAD_TRACK_SPEED_MAX=75,
            HEAD_TRACK_ACCEL_MIN=4,
            HEAD_TRACK_ACCEL_MAX=12,
            HEAD_TRACK_STEP_X=26,
            HEAD_TRACK_STEP_Y=22,
            JAW_RMS_THRESHOLD=120.0,
            COMMAND_TRACKING_PAUSE_S=2.8,
            TRACKING_LOST_HOLD_S=3.2,
            CAMERA_CAPTURE_SIZE=(800, 600),
            CAMERA_DISPLAY_SIZE=(640, 480),
            MODEL_FRAME_MAX_SIZE=(800, 600),
            MODEL_JPEG_QUALITY=72,
            MODEL_FRAME_INTERVAL_S=0.45,
            OCR_COMMAND="tesseract",
            OCR_LANG="eng",
            OCR_PSM=6,
            OCR_DOCUMENT_PSM=6,
            OCR_TIMEOUT_S=5.0,
            OCR_DOCUMENT_CROP_RATIO=0.7,
        )

    def test_load_robot_config_returns_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = os.path.join(tmpdir, "missing.json")
            loaded = load_robot_config(missing_path, self.default_config)

        self.assertEqual(loaded, self.default_config)

    def test_load_robot_config_applies_partial_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "robot_config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write('{"LOG_LEVEL":"DEBUG","MODEL_JPEG_QUALITY":55}')

            loaded = load_robot_config(config_path, self.default_config)

        self.assertEqual(loaded.LOG_LEVEL, "DEBUG")
        self.assertEqual(loaded.MODEL_JPEG_QUALITY, 55)
        self.assertEqual(loaded.MIC_INDEX, self.default_config.MIC_INDEX)

    def test_load_robot_config_converts_list_sizes_to_tuples(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "robot_config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write('{"CAMERA_CAPTURE_SIZE":[1024,768],"MODEL_FRAME_MAX_SIZE":[640,480]}')

            loaded = load_robot_config(config_path, self.default_config)

        self.assertEqual(loaded.CAMERA_CAPTURE_SIZE, (1024, 768))
        self.assertEqual(loaded.MODEL_FRAME_MAX_SIZE, (640, 480))

    def test_load_robot_config_applies_ocr_document_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "robot_config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write('{"OCR_DOCUMENT_PSM":11,"OCR_DOCUMENT_CROP_RATIO":0.82}')

            loaded = load_robot_config(config_path, self.default_config)

        self.assertEqual(loaded.OCR_DOCUMENT_PSM, 11)
        self.assertEqual(loaded.OCR_DOCUMENT_CROP_RATIO, 0.82)


if __name__ == "__main__":
    unittest.main()
