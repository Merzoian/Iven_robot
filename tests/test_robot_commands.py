import unittest

import robot_commands


class DummyRuntime:
    def __init__(self):
        self.command_enabled = True
        self.tracking_enabled = False
        self.control_mode = "command"
        self.tracked_lr = 11
        self.tracked_ud = -7
        self.tracked_head_yaw = 33
        self.tracked_head_pitch = -22
        self.last_tracking_update = 9.9
        self.tracking_resume_at = 4.0
        self.eye_manual_until = 5.0
        self.gaze_hold_enabled = False
        self.gaze_hold_lr = 3
        self.gaze_hold_ud = 4
        self.head_override_until = 0.0
        self.head_override_pose = {"yaw": 1500, "pitch": 1500, "tilt": 1500}
        self.head_target_pose = {"yaw": 1500, "pitch": 1500, "tilt": 1500}
        self.HEAD_NEUTRAL = {"yaw": 1500, "pitch": 1500, "tilt": 1500}
        self.HEAD_YAW_MIN = 1260
        self.HEAD_YAW_MAX = 1840
        self.HEAD_PITCH_MIN = 1280
        self.HEAD_PITCH_MAX = 1700
        self.HEAD_TILT_MIN = 1320
        self.HEAD_TILT_MAX = 1680
        self.CH_YAW = 8
        self.CH_FACE_PITCH = 7
        self.CH_TILT = 9
        self.COMMAND_TRACKING_PAUSE_S = 2.8
        self.maestro = None
        self.requested_head_pose = None
        self.centered = False
        self.gesture_calls = []

    def set_control_mode(self, mode):
        if mode == "tracking":
            self.control_mode = "tracking"
            self.tracking_enabled = True
            self.command_enabled = False
        elif mode in {"command", "intro"}:
            self.control_mode = mode
            self.tracking_enabled = False
            self.command_enabled = True
        return {
            "ok": True,
            "mode": mode,
            "tracking_enabled": self.tracking_enabled,
            "command_enabled": self.command_enabled,
        }

    def request_head_pose(self, yaw=None, pitch=None, tilt=None):
        self.requested_head_pose = {"yaw": yaw, "pitch": pitch, "tilt": tilt}
        if yaw is not None:
            self.head_target_pose["yaw"] = yaw
        if pitch is not None:
            self.head_target_pose["pitch"] = pitch
        if tilt is not None:
            self.head_target_pose["tilt"] = tilt

    def clamp(self, value, lo, hi):
        return max(lo, min(hi, value))

    def _get_sorted_limits(self, channel, fallback_min, fallback_max):
        return min(fallback_min, fallback_max), max(fallback_min, fallback_max), fallback_min, fallback_max

    def set_gaze(self, maestro, lr, ud):
        self.last_gaze = (lr, ud)

    def set_head_pose(self, maestro, yaw=None, pitch=None, tilt=None):
        self.last_head_pose = {"yaw": yaw, "pitch": pitch, "tilt": tilt}

    def center_all_servos(self, maestro):
        self.centered = True

    def get_intro_head_pose(self):
        return {"yaw": 1500, "pitch": 1410, "tilt": 1500}

    def perform_head_gesture(self, gesture):
        self.gesture_calls.append(gesture)
        return {"ok": True, "gesture": gesture}


class RobotCommandsTests(unittest.TestCase):
    def setUp(self):
        self.runtime = DummyRuntime()
        robot_commands.initialize(self.runtime)

    def test_set_mode_tracking_disables_command_mode(self):
        result = robot_commands.execute_robot_function("set_mode", {"mode": "tracking"})

        self.assertTrue(result["ok"])
        self.assertTrue(self.runtime.tracking_enabled)
        self.assertFalse(self.runtime.command_enabled)
        self.assertEqual(self.runtime.control_mode, "tracking")

    def test_set_mode_command_resets_tracking_state(self):
        result = robot_commands.execute_robot_function("set_mode", {"mode": "command"})

        self.assertTrue(result["ok"])
        self.assertFalse(self.runtime.tracking_enabled)
        self.assertTrue(self.runtime.command_enabled)
        self.assertEqual(self.runtime.tracked_lr, 0)
        self.assertEqual(self.runtime.tracked_ud, 0)
        self.assertEqual(self.runtime.tracked_head_yaw, 0)
        self.assertEqual(self.runtime.tracked_head_pitch, 0)
        self.assertEqual(self.runtime.last_tracking_update, 0.0)
        self.assertEqual(
            self.runtime.requested_head_pose,
            {"yaw": 1500, "pitch": 1500, "tilt": 1500},
        )

    def test_set_mode_intro_uses_intro_rest_pose(self):
        result = robot_commands.execute_robot_function("set_mode", {"mode": "intro"})

        self.assertTrue(result["ok"])
        self.assertFalse(self.runtime.tracking_enabled)
        self.assertTrue(self.runtime.command_enabled)
        self.assertEqual(self.runtime.control_mode, "intro")
        self.assertEqual(
            self.runtime.requested_head_pose,
            {"yaw": 1500, "pitch": 1410, "tilt": 1500},
        )

    def test_set_tracking_false_resets_tracking_state(self):
        self.runtime.tracking_enabled = True
        self.runtime.command_enabled = False

        result = robot_commands.execute_robot_function("set_tracking", {"enabled": False})

        self.assertEqual(result, {"ok": True, "tracking_enabled": False})
        self.assertFalse(self.runtime.tracking_enabled)
        self.assertTrue(self.runtime.command_enabled)
        self.assertEqual(self.runtime.tracking_resume_at, 0.0)
        self.assertEqual(self.runtime.eye_manual_until, 0.0)

    def test_look_direction_rejected_in_tracking_mode(self):
        self.runtime.command_enabled = False
        self.runtime.tracking_enabled = True

        result = robot_commands.execute_robot_function("look_direction", {"direction": "left"})

        self.assertFalse(result["ok"])
        self.assertIn("tracking mode", result["error"])

    def test_local_voice_command_enable_tracking(self):
        handled = robot_commands.execute_local_voice_command("please enable tracking")

        self.assertTrue(handled)
        self.assertTrue(self.runtime.tracking_enabled)
        self.assertFalse(self.runtime.command_enabled)

    def test_local_voice_command_intro_mode_switches_modes(self):
        handled = robot_commands.execute_local_voice_command("switch to intro mode")

        self.assertTrue(handled)
        self.assertEqual(self.runtime.control_mode, "intro")

    def test_local_voice_command_stop_following_returns_to_command_mode(self):
        self.runtime.tracking_enabled = True
        self.runtime.command_enabled = False

        handled = robot_commands.execute_local_voice_command("stop following")

        self.assertTrue(handled)
        self.assertFalse(self.runtime.tracking_enabled)
        self.assertTrue(self.runtime.command_enabled)

    def test_local_voice_command_look_left_updates_override_pose(self):
        handled = robot_commands.execute_local_voice_command("look left")

        self.assertTrue(handled)
        self.assertGreater(self.runtime.head_override_pose["yaw"], self.runtime.HEAD_NEUTRAL["yaw"])
        self.assertEqual(self.runtime.gaze_hold_lr, 0)
        self.assertEqual(self.runtime.gaze_hold_ud, 0)
        self.assertTrue(self.runtime.gaze_hold_enabled)

    def test_local_voice_command_center_invokes_center_servos(self):
        self.runtime.maestro = object()

        handled = robot_commands.execute_local_voice_command("center")

        self.assertTrue(handled)
        self.assertTrue(self.runtime.centered)

    def test_local_voice_command_ignored_for_manual_movement_in_tracking_mode(self):
        self.runtime.command_enabled = False
        self.runtime.tracking_enabled = True

        handled = robot_commands.execute_local_voice_command("look right")

        self.assertFalse(handled)

    def test_local_voice_command_read_this_triggers_document_ocr(self):
        calls = []
        self.runtime.read_visible_text = lambda mode="auto": calls.append(mode) or {"ok": True, "mode": mode}

        handled = robot_commands.execute_local_voice_command("can you read this")

        self.assertFalse(handled)
        self.assertEqual(calls, ["document"])

    def test_local_voice_command_read_this_equation_triggers_document_ocr(self):
        calls = []
        self.runtime.read_visible_text = lambda mode="auto": calls.append(mode) or {"ok": True, "mode": mode}

        handled = robot_commands.execute_local_voice_command("read this equation")

        self.assertFalse(handled)
        self.assertEqual(calls, ["document"])

    def test_read_visible_text_tool_uses_runtime_ocr_handler(self):
        self.runtime.read_visible_text = lambda mode="auto": {
            "ok": True,
            "text": "2 + 2",
            "math_expression": "2 + 2",
            "mode": mode,
        }

        result = robot_commands.execute_robot_function("read_visible_text", {})

        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "2 + 2")
        self.assertEqual(result["math_expression"], "2 + 2")
        self.assertEqual(result["mode"], "auto")

    def test_read_visible_text_tool_passes_document_mode(self):
        self.runtime.read_visible_text = lambda mode="auto": {"ok": True, "mode": mode}

        result = robot_commands.execute_robot_function("read_visible_text", {"mode": "document"})

        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "document")

    def test_describe_features_tool_returns_summary(self):
        result = robot_commands.execute_robot_function("describe_features", {})

        self.assertTrue(result["ok"])
        self.assertIn("Intro mode", result["features"])

    def test_feature_help_tool_returns_specific_explanation(self):
        result = robot_commands.execute_robot_function("feature_help", {"feature": "tracking mode"})

        self.assertTrue(result["ok"])
        self.assertIn("automatically follow", result["explanation"])

    def test_gesture_head_tool_routes_to_runtime_handler(self):
        result = robot_commands.execute_robot_function("gesture_head", {"gesture": "no"})

        self.assertEqual(result, {"ok": True, "gesture": "no"})
        self.assertEqual(self.runtime.gesture_calls, ["no"])


if __name__ == "__main__":
    unittest.main()
