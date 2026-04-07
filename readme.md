# Ivan Robot Runtime

Ivan is a Python control runtime for a conversational robotic head that combines Gemini live audio, camera awareness, servo motion, OCR, tracking, and short-term session memory.

This repository appears to be the active project source for the Ivan robot used in an Advanced Embedded Systems class project.

## What The Project Does

- Runs a live Gemini session with microphone input, spoken audio output, camera frames, and function calls.
- Controls eyes, jaw, head yaw, head pitch, and head tilt through a Pololu Maestro servo controller when the hardware is connected.
- Supports three control modes: `command`, `tracking`, and `intro`.
- Uses local OCR to read visible text, handwriting, numbers, and simple equations from the latest camera frame.
- Stores short session memory such as names, likes, favorites, and explicit reminders.
- Falls back to deterministic local voice-command handling for movement, mode switching, gestures, and OCR triggers.

## Entry Point

Start the runtime from [main4_robot.py](/home/redleader/gemini_robot/main4_robot.py). It imports `run()` from [robot_app.py](/home/redleader/gemini_robot/robot_app.py) and starts the full application.

```bash
python main4_robot.py
```

## Runtime Architecture

- [robot_app.py](/home/redleader/gemini_robot/robot_app.py): application startup, Gemini session loop, reconnect logic, shutdown handling, and runtime wiring.
- [robot_runtime.py](/home/redleader/gemini_robot/robot_runtime.py): config dataclasses, shared mutable runtime state, and JSON config loading.
- [robot_motion.py](/home/redleader/gemini_robot/robot_motion.py): servo calibration, blinking, gaze control, head hold, gestures, and tracking motion math.
- [robot_camera.py](/home/redleader/gemini_robot/robot_camera.py): Picamera2 capture, frame enhancement, face and person detection, tracking target updates, and preview HUD rendering.
- [robot_audio.py](/home/redleader/gemini_robot/robot_audio.py): microphone upload, speaker playback, jaw lip sync, speech suppression windows, and camera-send pacing.
- [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py): Gemini tool execution and deterministic spoken-command parsing.
- [robot_session.py](/home/redleader/gemini_robot/robot_session.py): handling of streaming transcripts, model audio chunks, tool calls, and mode sync back into Gemini.
- [robot_ocr.py](/home/redleader/gemini_robot/robot_ocr.py): OCR preprocessing, Tesseract execution, and visible-math extraction.
- [robot_prompt.py](/home/redleader/gemini_robot/robot_prompt.py): system instruction text and feature-tour wording used for the live model session.
- [robot_memory.py](/home/redleader/gemini_robot/robot_memory.py): memory extraction plus load and save behavior.
- [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py): function declarations exposed to Gemini.
- [robot_logging.py](/home/redleader/gemini_robot/robot_logging.py): logging configuration and structured runtime event helpers.
- [servo_controller.py](/home/redleader/gemini_robot/servo_controller.py): serial control wrapper for the Pololu Maestro board.
- [maestro.py](/home/redleader/gemini_robot/maestro.py): lower-level Maestro communication helpers.

## Project Files

- [robot_config.json](/home/redleader/gemini_robot/robot_config.json): runtime tuning, audio device indexes, tracking gains, OCR settings, frame sizes, and timing overrides.
- [ivan_servo_calibration.json](/home/redleader/gemini_robot/ivan_servo_calibration.json): servo pulse calibration values.
- [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json): persisted session memory.
- [iven_in_action.md](/home/redleader/gemini_robot/iven_in_action.md): architecture and runtime walkthrough.
- [final_project_report.md](/home/redleader/gemini_robot/final_project_report.md): project report draft.
- [final_project_report_v2.md](/home/redleader/gemini_robot/final_project_report_v2.md): revised project report.
- [final_project_report_presentation.md](/home/redleader/gemini_robot/final_project_report_presentation.md): presentation notes and report summary content.
- [video_presentation_script.md](/home/redleader/gemini_robot/video_presentation_script.md): presentation script.
- [backup_repo.sh](/home/redleader/gemini_robot/backup_repo.sh): stage, commit, and push helper script for the current branch.

## Requirements

The repository does not include a pinned dependency file, but the code currently expects:

- Python 3.11 or another modern Python 3 release
- `google-genai`
- `pyaudio`
- `numpy`
- `opencv-python`
- `mediapipe`
- `pyserial`
- Raspberry Pi `picamera2` support for the live camera path
- local `tesseract` for OCR

Hardware-specific features degrade gracefully:

- If the Maestro controller is unavailable, the app can still run in a reduced software-only state.
- If Picamera2 or related camera dependencies are unavailable, the camera path is disabled.
- If Tesseract is unavailable, OCR requests return an unavailable result instead of crashing the runtime.

## Environment Variables

- `GOOGLE_API_KEY`: required for the Gemini live connection.
- `IVAN_VOICE_NAME`: optional voice name, defaults to `Kore`.
- `IVAN_LOG_LEVEL`: optional log level, defaults to `INFO`.
- `IVAN_OCR_COMMAND`: optional OCR binary path, defaults to `tesseract`.
- `IVAN_OCR_LANG`: optional OCR language, defaults to `eng`.

The current live model configured in code is `gemini-2.5-flash-native-audio-latest`.

## Modes

### Command Mode

- Default manual-control mode.
- Allows direct look, head move, tilt, and center commands.
- Temporarily suppresses model speech and model movement reactions after a local movement command.
- Can send a delayed follow-up prompt after the user has been idle.

Common phrases:

- `enable command`
- `disable tracking`
- `stop following`
- `look left`
- `turn head right`
- `tilt left`
- `center`

### Tracking Mode

- Enables automatic following behavior.
- Rejects manual movement commands while tracking is active.
- Prioritizes face tracking, then person tracking, then recent target hold behavior.

Common phrases:

- `enable tracking`
- `start tracking`
- `tracking mode`
- `follow me`
- `stop tracking`

### Intro Mode

- Quiet nonverbal mode.
- Discards spoken model audio before playback.
- Holds the head slightly downward.
- Keeps blinking and subtle eye motion active.
- Supports local `yes` and `no` head gestures from simple feedback phrases.

Common phrases:

- `intro mode`
- `switch to intro mode`
- `enable intro`

## Gemini Tool Functions

The live session exposes these tool functions from [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py):

- `set_mode`
- `set_tracking`
- `look_direction`
- `move_head`
- `tilt_head`
- `center_servos`
- `describe_features`
- `feature_help`
- `gesture_head`
- `read_visible_text`

Execution is handled by [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py). Runtime mode changes are also synced back into the live Gemini session so the model stays aligned without forcing a reconnect.

## OCR, Vision, And Memory

- OCR reads from the latest camera frame.
- `read_visible_text` supports both `auto` and `document` modes.
- Document mode is intended for centered paper, worksheets, whiteboards, screens, and handwriting.
- Vision questions such as `what do you see` are handled through the live Gemini image context.
- Repeated partial transcripts are briefly deduplicated before local command execution and memory extraction.

Session memory is stored in [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json) and can currently capture phrases such as:

- `my name is ...`
- `I'm ...`
- `I like ...`
- `remember that ...`
- `my favorite ...`

## Tests

The `tests/` directory currently includes coverage for commands, memory, motion, OCR, runtime config loading, and session-response handling.

```bash
python -m unittest discover -s tests
```

## Backup Workflow

Use [backup_repo.sh](/home/redleader/gemini_robot/backup_repo.sh) to stage all changes, commit if needed, and push the current branch:

```bash
./backup_repo.sh
./backup_repo.sh "your message here"
```
