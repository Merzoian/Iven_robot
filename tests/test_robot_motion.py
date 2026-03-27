import unittest

import robot_motion


class DummyMotionRuntime:
    def __init__(self):
        self.CH_JAW = 6
        self.CH_LID_L = 2
        self.CH_LID_R = 3
        self.CH_EYE_L_LR = 1
        self.CH_EYE_R_LR = 4
        self.CH_EYES_UD = 5
        self.CH_YAW = 8
        self.CH_FACE_PITCH = 7
        self.CH_TILT = 9
        self.CH_HEAD_TILT = 9

        self.HEAD_NEUTRAL = {"yaw": 1500, "pitch": 1500, "tilt": 1500}
        self.HEAD_YAW_MIN = 1260
        self.HEAD_YAW_MAX = 1840
        self.HEAD_PITCH_MIN = 1280
        self.HEAD_PITCH_MAX = 1700
        self.HEAD_TILT_MIN = 1320
        self.HEAD_TILT_MAX = 1680

        self.EYE_CENTER = 1500
        self.EYE_R_TRIM = 0
        self.EYE_R_INVERT = False
        self.EYE_LR_MIN = 1280
        self.EYE_LR_MAX = 1720
        self.EYE_UD_MIN = 1360
        self.EYE_UD_MAX = 1760

        self.TRACK_X_SIGN = 1.0
        self.TRACK_Y_SIGN = -1.0
        self.HEAD_TRACK_X_SIGN = -1.0
        self.HEAD_TRACK_Y_SIGN = -1.0
        self.HEAD_TRACK_GAIN_X = 1.20
        self.HEAD_TRACK_GAIN_Y = 1.46
        self.HEAD_TRACK_DEADZONE_X = 0.08
        self.HEAD_TRACK_DEADZONE_Y = 0.04
        self.HEAD_TRACK_EDGE_SOFTEN_X = 0.75
        self.HEAD_TRACK_EDGE_SOFTEN_Y = 0.80
        self.TRACK_CENTER_HOLD_X = 0.12
        self.TRACK_CENTER_HOLD_Y = 0.07
        self.TRACK_PREDICTION_S = 0.10
        self.TRACK_PREDICTION_MAX_X = 0.06
        self.TRACK_PREDICTION_MAX_Y = 0.10
        self.EYE_FIRST_HEAD_DELAY_S = 0.18
        self.PRIMARY_FACE_MATCH_NORM = 0.18

        self.tracking_enabled = False
        self.command_enabled = True
        self.control_mode = "command"
        self.tracked_lr = 0
        self.tracked_ud = 0
        self.tracked_head_yaw = 0
        self.tracked_head_pitch = 0
        self.last_tracking_update = 0.0
        self.tracking_head_enable_at = 0.0
        self.tracking_state = "idle"
        self.last_seen_x_norm = 0.0
        self.last_seen_y_norm = 0.0
        self.last_target_norm_x = 0.0
        self.last_target_norm_y = 0.0
        self.last_target_velocity_x = 0.0
        self.last_target_velocity_y = 0.0
        self.maestro = None


class RobotMotionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = DummyMotionRuntime()
        robot_motion.initialize(self.runtime)

    def test_clamp_limits_value_to_range(self):
        self.assertEqual(robot_motion.clamp(5, 0, 3), 3)
        self.assertEqual(robot_motion.clamp(-1, 0, 3), 0)
        self.assertEqual(robot_motion.clamp(2, 0, 3), 2)

    def test_smooth_point_interpolates_from_previous_point(self):
        result = robot_motion._smooth_point((10.0, 20.0), (20.0, 40.0), 0.25)

        self.assertEqual(result, (12.5, 25.0))

    def test_set_control_mode_tracking_and_command(self):
        tracking_result = robot_motion.set_control_mode("tracking")
        self.assertTrue(tracking_result["tracking_enabled"])
        self.assertFalse(tracking_result["command_enabled"])
        self.assertEqual(self.runtime.control_mode, "tracking")

        command_result = robot_motion.set_control_mode("command")
        self.assertFalse(command_result["tracking_enabled"])
        self.assertTrue(command_result["command_enabled"])
        self.assertEqual(self.runtime.control_mode, "command")

    def test_set_control_mode_intro_keeps_manual_commands_enabled(self):
        intro_result = robot_motion.set_control_mode("intro")

        self.assertTrue(intro_result["ok"])
        self.assertFalse(intro_result["tracking_enabled"])
        self.assertTrue(intro_result["command_enabled"])
        self.assertEqual(self.runtime.control_mode, "intro")

    def test_get_intro_head_pose_lowers_pitch_from_neutral(self):
        pose = robot_motion.get_intro_head_pose()

        self.assertEqual(pose["yaw"], self.runtime.HEAD_NEUTRAL["yaw"])
        self.assertEqual(pose["tilt"], self.runtime.HEAD_NEUTRAL["tilt"])
        self.assertLess(pose["pitch"], self.runtime.HEAD_NEUTRAL["pitch"])

    def test_pick_primary_face_prefers_locked_nearby_face(self):
        faces = [
            (10, 10, 40, 40, 0.90),
            (100, 100, 50, 50, 0.95),
        ]
        locked_center = ((10 + 20) / 200.0, (10 + 20) / 200.0)

        picked = robot_motion._pick_primary_face(faces, 200.0, 200.0, locked_center)

        self.assertEqual(picked, faces[0])

    def test_set_tracking_target_updates_locked_state_and_offsets(self):
        robot_motion.set_tracking_target(640, 480, 520, 120)

        self.assertEqual(self.runtime.tracking_state, "locked")
        self.assertNotEqual(self.runtime.last_tracking_update, 0.0)
        self.assertGreater(self.runtime.tracked_lr, 0)
        self.assertGreater(abs(self.runtime.last_seen_x_norm), 0.0)
        self.assertGreater(abs(self.runtime.last_seen_y_norm), 0.0)

    def test_set_tracking_target_damps_when_centered(self):
        self.runtime.tracked_lr = 100
        self.runtime.tracked_ud = 80
        self.runtime.tracked_head_yaw = 60
        self.runtime.tracked_head_pitch = 50

        robot_motion.set_tracking_target(640, 480, 320, 240)

        self.assertLess(self.runtime.tracked_lr, 100)
        self.assertLess(self.runtime.tracked_ud, 80)
        self.assertLess(self.runtime.tracked_head_yaw, 60)
        self.assertLess(self.runtime.tracked_head_pitch, 50)


if __name__ == "__main__":
    unittest.main()
