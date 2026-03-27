import time

from robot_logging import log_event


async def handle_session_response(response, session, runtime, apply_memory_from_text, execute_local_voice_command, execute_robot_function):
    if response.server_content:
        in_tx = response.server_content.input_transcription
        if in_tx and in_tx.text:
            runtime.latest_transcription = " ".join(in_tx.text.strip().split())[:280]
            runtime.latest_transcription_at = time.time()
            apply_memory_from_text(in_tx.text)
            execute_local_voice_command(in_tx.text)

        if response.server_content.model_turn:
            for part in response.server_content.model_turn.parts:
                if part.inline_data:
                    if getattr(runtime, "control_mode", "command") == "intro":
                        continue
                    await runtime.audio_queue.put(part.inline_data.data)

    if response.tool_call and response.tool_call.function_calls:
        responses = []
        for fc in response.tool_call.function_calls:
            log_event(runtime.logger, "info", "tool_call", name=fc.name, args=fc.args)
            print(f"Tool call: {fc.name} args={fc.args}")
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
