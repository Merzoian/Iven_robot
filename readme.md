# Ivan Robot

Ivan is a Python runtime for a conversational robotic head with live Gemini audio, camera awareness, servo motion, OCR, tracking, and short session memory.

Valentina, a Senior Computer Engineering student at BYU-Idaho, created the project for her Advanced Embedded Systems class.

## What The Project Does

- Runs a live Gemini session with microphone input, spoken audio output, camera frames, and tool calls.
- Controls eyes, jaw, head yaw, head pitch, and head tilt through a Pololu Maestro servo controller when hardware is present.
- Supports three modes: `command`, `tracking`, and `intro`.
- Uses local OCR to read visible text, handwriting, numbers, and simple math from the latest camera frame.
- Stores short session memory such as names, likes, and remembered facts.
- Falls back to deterministic local voice-command handling for movement, mode switching, and OCR triggers.

## Entry Point

Run [main4_robot.py](/home/redleader/gemini_robot/main4_robot.py). It imports `run()` from [robot_app.py](/home/redleader/gemini_robot/robot_app.py) and starts the full runtime.

```bash
python main4_robot.py
```

## Main Files

- [robot_app.py](/home/redleader/gemini_robot/robot_app.py): runtime assembly, Gemini connection loop, shutdown, reconnects, and startup wiring.
- [robot_runtime.py](/home/redleader/gemini_robot/robot_runtime.py): shared runtime state and JSON config loading.
- [robot_motion.py](/home/redleader/gemini_robot/robot_motion.py): servo calibration, head hold logic, gaze control, blinking, gestures, and tracking math.
- [robot_camera.py](/home/redleader/gemini_robot/robot_camera.py): Picamera2 capture, frame enhancement, face/person detection, preview HUD, and JPEG preparation.
- [robot_audio.py](/home/redleader/gemini_robot/robot_audio.py): microphone capture, speaker playback, jaw lip sync, and camera-send pacing.
- [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py): Gemini tool execution and local spoken command parsing.
- [robot_session.py](/home/redleader/gemini_robot/robot_session.py): response handling for transcripts, audio chunks, and tool calls.
- [robot_ocr.py](/home/redleader/gemini_robot/robot_ocr.py): local Tesseract OCR and visible-math extraction.
- [robot_prompt.py](/home/redleader/gemini_robot/robot_prompt.py): system instruction text and feature-tour wording.
- [robot_memory.py](/home/redleader/gemini_robot/robot_memory.py): session memory extraction, load, and save logic.
- [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py): tool declarations exposed to Gemini.
- [servo_controller.py](/home/redleader/gemini_robot/servo_controller.py): serial control for the Maestro board.

## Runtime Requirements

The repository does not currently include a pinned dependency file, but the code expects:

- Python 3
- `google-genai`
- `pyaudio`
- `numpy`
- `opencv-python`
- `mediapipe`
- `pyserial`
- Raspberry Pi `picamera2` support for the live camera path
- local `tesseract` for OCR

Hardware-specific features are optional at runtime:

- If the Maestro servo controller is unavailable, the app can still run in a reduced software-only state.
- If Picamera2 or camera dependencies are unavailable, the camera path is disabled.
- If Tesseract is unavailable, OCR requests return a clear unavailable error.

## Environment Variables

- `GOOGLE_API_KEY`: required for the Gemini live connection.
- `IVAN_VOICE_NAME`: optional voice name, defaults to `Kore`.
- `IVAN_LOG_LEVEL`: optional log level, defaults to `INFO`.
- `IVAN_OCR_COMMAND`: optional OCR binary path, defaults to `tesseract`.
- `IVAN_OCR_LANG`: optional OCR language, defaults to `eng`.

The live model configured in the code is `gemini-2.5-flash-native-audio-latest`.

## Modes

### Command Mode

- Default mode for manual movement commands.
- Manual look, head move, tilt, and center commands are allowed.
- After a local movement command, Ivan briefly suppresses model speech and model movement reactions.
- If the user stays idle long enough, Ivan can send a single follow-up prompt asking what to do next.

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
- Manual movement commands are rejected while tracking is active.
- The camera path prioritizes face tracking, then person tracking, then fallback remembered target behavior.

Common phrases:

- `enable tracking`
- `start tracking`
- `tracking mode`
- `follow me`
- `stop tracking`

### Intro Mode

- Quiet nonverbal mode.
- Spoken audio output is suppressed.
- The head rests slightly downward.
- Blinking and subtle eye motion continue.
- `yes` and `no` style feedback can trigger local head gestures.
- In intro mode, `wrong` or `no` uses a more explicit `left -> right -> center` head gesture.

Common phrases:

- `intro mode`
- `switch to intro mode`
- `enable intro`

## Tool Functions Exposed To Gemini

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

These are declared in [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py) and executed by [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py).

Mode changes are also synced back into the live Gemini session so the model stays aligned with the current runtime mode without forcing a reconnect.

## OCR And Vision

- OCR reads from the latest camera frame.
- `read_visible_text` supports `auto` and `document` modes.
- Document mode is intended for centered paper, phone screens, worksheets, whiteboards, and handwriting.
- Scene-description requests such as `what do you see` are handled through the live Gemini vision context.
- Model camera frames are resized both up and down to stay within the configured max frame size.

OCR-related phrases handled locally include:

- `read this`
- `can you read this`
- `what does this say`
- `read this equation`
- `solve this equation`

## Memory

Session memory is stored in [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json).

The current memory extractor can save:

- `my name is ...`
- `I'm ...`
- `I like ...`
- `remember that ...`
- `my favorite ...`

Repeated streaming partial transcripts are deduplicated briefly before local command execution and memory extraction so one spoken request is less likely to trigger duplicate movements or OCR runs.

## Config Files

- [robot_config.json](/home/redleader/gemini_robot/robot_config.json): JSON overrides for runtime tuning, device indexes, tracking gains, OCR settings, frame size, and timing.
- [ivan_servo_calibration.json](/home/redleader/gemini_robot/ivan_servo_calibration.json): servo pulse calibration.
- [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json): saved short-term session memory.

## Tests

The `tests/` directory currently covers commands, memory, motion, OCR, runtime config loading, and session-response handling.

```bash
python -m unittest discover -s tests
```

## Backup Workflow

Use [backup_repo.sh](/home/redleader/gemini_robot/backup_repo.sh) to stage, commit if needed, and push the current branch:

```bash
./backup_repo.sh
./backup_repo.sh "your message here"
```
