import time

from robot_logging import log_event


_SUPPRESSED_COMMAND_TOOLS = {
    "set_mode",
    "set_tracking",
    "look_direction",
    "move_head",
    "tilt_head",
    "center_servos",
    "gesture_head",
}


async def handle_session_response(response, session, runtime, apply_memory_from_text, execute_local_voice_command, execute_robot_function):
    if response.server_content:
        in_tx = response.server_content.input_transcription
        if in_tx and in_tx.text:
            cleaned_input = " ".join(in_tx.text.strip().split())[:280]
            now = time.time()
            runtime.latest_user_transcription = cleaned_input
            runtime.latest_user_transcription_at = now
            runtime.latest_transcription = cleaned_input
            runtime.latest_transcription_at = now
            runtime.last_user_activity_at = now
            apply_memory_from_text(in_tx.text)
            execute_local_voice_command(in_tx.text)

        out_tx = getattr(response.server_content, "output_transcription", None)
        if out_tx and getattr(out_tx, "text", None) and time.time() >= getattr(runtime, "model_audio_suppressed_until", 0.0):
            cleaned_output = " ".join(out_tx.text.strip().split())[:280]
            now = time.time()
            runtime.latest_model_transcription = cleaned_output
            runtime.latest_model_transcription_at = now
            runtime.latest_transcription = cleaned_output
            runtime.latest_transcription_at = now

        if response.server_content.model_turn:
            for part in response.server_content.model_turn.parts:
                if part.inline_data:
                    if getattr(runtime, "control_mode", "command") == "intro":
                        continue
                    if time.time() < getattr(runtime, "model_audio_suppressed_until", 0.0):
                        continue
                    await runtime.audio_queue.put(part.inline_data.data)

    if response.tool_call and response.tool_call.function_calls:
        responses = []
        for fc in response.tool_call.function_calls:
            log_event(runtime.logger, "info", "tool_call", name=fc.name, args=fc.args)
            print(f"Tool call: {fc.name} args={fc.args}")
            if time.time() < getattr(runtime, "model_action_suppressed_until", 0.0) and fc.name in _SUPPRESSED_COMMAND_TOOLS:
                result = {"ok": True, "suppressed": True, "name": fc.name}
            else:
                result = execute_robot_function(fc.name, fc.args)
            responses.append(
                {
                    "id": fc.id,
                    "name": fc.name,
                    "response": result,
                }
            )
        if responses:
            await session.send_tool_response(function_responses=responses)
