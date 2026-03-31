import asyncio
import logging
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import robot_session


class DummySession:
    def __init__(self):
        self.tool_responses = []
        self.realtime_inputs = []

    async def send_tool_response(self, function_responses):
        self.tool_responses.append(function_responses)

    async def send_realtime_input(self, **kwargs):
        self.realtime_inputs.append(kwargs)


def make_response(transcription_text=None, output_transcription_text=None, audio_chunks=None, function_calls=None):
    parts = []
    for chunk in audio_chunks or []:
        parts.append(SimpleNamespace(inline_data=SimpleNamespace(data=chunk)))

    server_content = None
    if transcription_text is not None or output_transcription_text is not None or parts:
        input_tx = SimpleNamespace(text=transcription_text) if transcription_text is not None else None
        output_tx = SimpleNamespace(text=output_transcription_text) if output_transcription_text is not None else None
        model_turn = SimpleNamespace(parts=parts) if parts else None
        server_content = SimpleNamespace(
            input_transcription=input_tx,
            output_transcription=output_tx,
            model_turn=model_turn,
        )

    tool_call = None
    if function_calls:
        tool_call = SimpleNamespace(function_calls=function_calls)

    return SimpleNamespace(server_content=server_content, tool_call=tool_call)


class RobotSessionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = SimpleNamespace(
            latest_transcription="",
            latest_transcription_at=0.0,
            latest_user_transcription="",
            latest_user_transcription_at=0.0,
            latest_model_transcription="",
            latest_model_transcription_at=0.0,
            last_user_activity_at=0.0,
            model_audio_suppressed_until=0.0,
            model_action_suppressed_until=0.0,
            audio_queue=asyncio.Queue(),
            logger=logging.getLogger("test.robot_session"),
            control_mode="command",
        )

    async def test_handle_session_response_updates_transcription_and_callbacks(self):
        response = make_response(transcription_text="  hello    there  ")
        session = DummySession()
        apply_memory = mock.Mock()
        execute_local_voice_command = mock.Mock()
        execute_robot_function = mock.Mock()

        before = time.time()
        await robot_session.handle_session_response(
            response,
            session,
            self.runtime,
            apply_memory,
            execute_local_voice_command,
            execute_robot_function,
        )

        self.assertEqual(self.runtime.latest_transcription, "hello there")
        self.assertEqual(self.runtime.latest_user_transcription, "hello there")
        self.assertGreaterEqual(self.runtime.latest_transcription_at, before)
        apply_memory.assert_called_once_with("  hello    there  ")
        execute_local_voice_command.assert_called_once_with("  hello    there  ")

    async def test_handle_session_response_updates_output_transcription(self):
        response = make_response(output_transcription_text="  what   do you want me to do next  ")
        session = DummySession()

        await robot_session.handle_session_response(
            response,
            session,
            self.runtime,
            mock.Mock(),
            mock.Mock(),
            mock.Mock(),
        )

        self.assertEqual(self.runtime.latest_model_transcription, "what do you want me to do next")
        self.assertEqual(self.runtime.latest_transcription, "what do you want me to do next")

    async def test_handle_session_response_suppresses_output_while_local_command_quiet_mode_active(self):
        self.runtime.model_audio_suppressed_until = time.time() + 10.0
        response = make_response(output_transcription_text="speak now", audio_chunks=[b"a"])

        await robot_session.handle_session_response(
            response,
            DummySession(),
            self.runtime,
            mock.Mock(),
            mock.Mock(),
            mock.Mock(),
        )

        self.assertEqual(self.runtime.latest_model_transcription, "")
        self.assertTrue(self.runtime.audio_queue.empty())

    async def test_handle_session_response_enqueues_audio_parts(self):
        response = make_response(audio_chunks=[b"a", b"b"])
        session = DummySession()

        await robot_session.handle_session_response(
            response,
            session,
            self.runtime,
            mock.Mock(),
            mock.Mock(),
            mock.Mock(),
        )

        self.assertEqual(await self.runtime.audio_queue.get(), b"a")
        self.assertEqual(await self.runtime.audio_queue.get(), b"b")

    async def test_handle_session_response_sends_tool_responses(self):
        function_calls = [
            SimpleNamespace(id="1", name="set_mode", args={"mode": "tracking"}),
            SimpleNamespace(id="2", name="center_servos", args={}),
        ]
        response = make_response(function_calls=function_calls)
        session = DummySession()
        execute_robot_function = mock.Mock(side_effect=[{"ok": True}, {"ok": True, "done": 1}])

        await robot_session.handle_session_response(
            response,
            session,
            self.runtime,
            mock.Mock(),
            mock.Mock(),
            execute_robot_function,
        )

        self.assertEqual(execute_robot_function.call_count, 2)
        self.assertEqual(
            session.tool_responses,
            [[
                {"id": "1", "name": "set_mode", "response": {"ok": True}},
                {"id": "2", "name": "center_servos", "response": {"ok": True, "done": 1}},
            ]],
        )

    async def test_handle_session_response_suppresses_command_tool_calls_while_quiet_mode_active(self):
        self.runtime.model_action_suppressed_until = time.time() + 10.0
        function_calls = [SimpleNamespace(id="1", name="look_direction", args={"direction": "left"})]
        session = DummySession()
        execute_robot_function = mock.Mock()

        await robot_session.handle_session_response(
            make_response(function_calls=function_calls),
            session,
            self.runtime,
            mock.Mock(),
            mock.Mock(),
            execute_robot_function,
        )

        execute_robot_function.assert_not_called()
        self.assertEqual(
            session.tool_responses,
            [[{"id": "1", "name": "look_direction", "response": {"ok": True, "suppressed": True, "name": "look_direction"}}]],
        )

    async def test_handle_session_response_discards_audio_in_intro_mode(self):
        self.runtime.control_mode = "intro"
        response = make_response(audio_chunks=[b"a", b"b"])
        session = DummySession()

        await robot_session.handle_session_response(
            response,
            session,
            self.runtime,
            mock.Mock(),
            mock.Mock(),
            mock.Mock(),
        )

        self.assertTrue(self.runtime.audio_queue.empty())

    async def test_handle_session_response_syncs_mode_after_local_command(self):
        session = DummySession()

        def local_command(_text):
            self.runtime.control_mode = "intro"
            self.runtime.tracking_enabled = False

        await robot_session.handle_session_response(
            make_response(transcription_text="switch to intro mode"),
            session,
            self.runtime,
            mock.Mock(),
            local_command,
            mock.Mock(),
        )

        self.assertEqual(len(session.realtime_inputs), 1)
        self.assertIn("intro mode", session.realtime_inputs[0]["text"])

    async def test_handle_session_response_dedupes_repeated_partial_transcripts(self):
        session = DummySession()
        apply_memory = mock.Mock()
        execute_local_voice_command = mock.Mock()
        response = make_response(transcription_text="look left")

        await robot_session.handle_session_response(
            response,
            session,
            self.runtime,
            apply_memory,
            execute_local_voice_command,
            mock.Mock(),
        )
        await robot_session.handle_session_response(
            response,
            session,
            self.runtime,
            apply_memory,
            execute_local_voice_command,
            mock.Mock(),
        )

        apply_memory.assert_called_once_with("look left")
        execute_local_voice_command.assert_called_once_with("look left")


if __name__ == "__main__":
    unittest.main()
