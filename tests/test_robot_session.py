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

    async def send_tool_response(self, function_responses):
        self.tool_responses.append(function_responses)


def make_response(transcription_text=None, audio_chunks=None, function_calls=None):
    parts = []
    for chunk in audio_chunks or []:
        parts.append(SimpleNamespace(inline_data=SimpleNamespace(data=chunk)))

    server_content = None
    if transcription_text is not None or parts:
        input_tx = SimpleNamespace(text=transcription_text) if transcription_text is not None else None
        model_turn = SimpleNamespace(parts=parts) if parts else None
        server_content = SimpleNamespace(
            input_transcription=input_tx,
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
        self.assertGreaterEqual(self.runtime.latest_transcription_at, before)
        apply_memory.assert_called_once_with("  hello    there  ")
        execute_local_voice_command.assert_called_once_with("  hello    there  ")

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


if __name__ == "__main__":
    unittest.main()
