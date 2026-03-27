import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import robot_ocr


class RobotOcrTests(unittest.TestCase):
    def test_read_visible_text_returns_clear_error_when_ocr_unavailable(self):
        runtime = SimpleNamespace(
            OCR_COMMAND="tesseract",
            OCR_LANG="eng",
            OCR_PSM=6,
            OCR_DOCUMENT_PSM=6,
            OCR_TIMEOUT_S=5.0,
            OCR_DOCUMENT_CROP_RATIO=0.7,
            cv2=None,
            logger=logging.getLogger("test.robot_ocr"),
            latest_camera_frame=object(),
            ocr_available=False,
        )
        robot_ocr.initialize(runtime)
        runtime.ocr_available = False

        result = robot_ocr.read_visible_text()

        self.assertFalse(result["ok"])
        self.assertIn("unavailable", result["error"].lower())

    def test_center_crop_uses_middle_of_frame(self):
        frame = [[(row, col) for col in range(10)] for row in range(8)]

        cropped = robot_ocr._center_crop(frame, 0.5)

        self.assertEqual(len(cropped), 4)
        self.assertEqual(len(cropped[0]), 5)
        self.assertEqual(cropped[0][0], (2, 2))

    def test_read_visible_text_document_mode_prefers_document_crop(self):
        runtime = SimpleNamespace(
            OCR_COMMAND="tesseract",
            OCR_LANG="eng",
            OCR_PSM=6,
            OCR_DOCUMENT_PSM=11,
            OCR_TIMEOUT_S=5.0,
            OCR_DOCUMENT_CROP_RATIO=0.7,
            cv2=object(),
            logger=logging.getLogger("test.robot_ocr"),
            latest_camera_frame="full-frame",
            ocr_available=True,
        )
        robot_ocr.initialize(runtime)
        runtime.ocr_available = True

        def fake_crop(frame, ratio):
            self.assertEqual(frame, "full-frame")
            self.assertEqual(ratio, 0.7)
            return "document-frame"

        def fake_preprocess(frame, mode="auto"):
            return [f"{frame}:{mode}"]

        def fake_run(image, psm):
            if image == "document-frame:document" and psm == 11:
                return "2 + 2"
            return ""

        with patch.object(robot_ocr, "_center_crop", side_effect=fake_crop), patch.object(
            robot_ocr, "_preprocess_variants", side_effect=fake_preprocess
        ), patch.object(robot_ocr, "_run_tesseract", side_effect=fake_run):
            result = robot_ocr.read_visible_text(mode="document")

        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "2 + 2")
        self.assertEqual(result["math_expression"], "2 + 2")
        self.assertEqual(result["mode"], "document")
        self.assertEqual(result["source"], "document-crop")


if __name__ == "__main__":
    unittest.main()
