# Ivan in Action

This document is the current architecture and runtime walkthrough for the Ivan robot project.

The executable entry point is [main4_robot.py](/home/redleader/gemini_robot/main4_robot.py), which simply calls `run()` from [robot_app.py](/home/redleader/gemini_robot/robot_app.py).

## High-Level Runtime Flow

1. Load runtime config, servo calibration, and saved session memory.
2. Initialize the Maestro servo controller if available.
3. Open microphone and speaker streams through PyAudio.
4. Start the camera capture loop if Picamera2 is available.
5. Build Gemini tool declarations and the current system instruction.
6. Connect to Gemini live using `gemini-2.5-flash-native-audio-latest`.
7. Stream microphone audio and paced camera JPEG frames to the live session.
8. Receive user transcripts, model transcripts, model audio chunks, and tool calls.
9. Update memory, run local command fallback logic, execute robot actions, and manage quiet-mode suppression windows.
10. Reconnect automatically if the live session drops.

## Project Structure

- [robot_app.py](/home/redleader/gemini_robot/robot_app.py): startup, wiring, Gemini session loop, reconnect behavior, and shutdown.
- [robot_runtime.py](/home/redleader/gemini_robot/robot_runtime.py): shared config and mutable runtime state.
- [robot_motion.py](/home/redleader/gemini_robot/robot_motion.py): servo calibration, tracking math, head hold, blinking, gaze, and gestures.
- [robot_audio.py](/home/redleader/gemini_robot/robot_audio.py): mic upload, speaker playback, jaw lip sync, and camera-send pacing.
- [robot_camera.py](/home/redleader/gemini_robot/robot_camera.py): camera capture, enhancement, detection, target smoothing, and preview HUD.
- [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py): robot tool execution and deterministic spoken command parsing.
- [robot_session.py](/home/redleader/gemini_robot/robot_session.py): response handling for transcripts, audio chunks, and tool-call responses.
- [robot_ocr.py](/home/redleader/gemini_robot/robot_ocr.py): OCR preprocessing, Tesseract execution, and simple math extraction.
- [robot_prompt.py](/home/redleader/gemini_robot/robot_prompt.py): system prompt text and feature-tour wording.
- [robot_memory.py](/home/redleader/gemini_robot/robot_memory.py): memory extraction, load, and save behavior.
- [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py): Gemini function declarations.

## Startup Sequence

When `run()` starts, the runtime:

- restores session memory from [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json)
- registers exit handlers to save memory and recenter servos
- installs `SIGTERM` and `SIGINT` shutdown handlers
- enters `asyncio.run(main())`

Inside `main()` it then:

- initializes Maestro hardware if present
- starts the eye-movement and head-hold worker threads when servos are available
- creates the Gemini client using `GOOGLE_API_KEY`
- selects the voice from `IVAN_VOICE_NAME`, defaulting to `Kore`
- opens PyAudio input and output streams
- starts playback and camera tasks
- connects to the live Gemini session

## Mode System

Ivan has three control modes.

### Command Mode

- Default manual-control mode.
- Eye and head movement commands are allowed.
- Local movement commands trigger a short quiet window that suppresses model speech and model movement tool calls.
- After idle time, a delayed prompt can send `What do you want me to do next?`

Typical phrases:

- `command mode`
- `disable tracking`
- `stop following`
- `look left`
- `look center`
- `turn head left`
- `tilt right`

### Tracking Mode

- Automatic following mode.
- Manual movement commands are rejected.
- Tracking state is updated from camera detections and smoothed target history.

Tracking priority in the current camera pipeline:

- primary face
- detected person
- recent face hold
- recent target hold
- fallback motion logic

Typical phrases:

- `tracking mode`
- `enable tracking`
- `start tracking`
- `follow me`
- `stop tracking`

### Intro Mode

- Quiet nonverbal mode.
- Model audio is discarded before playback.
- The default head pose is slightly lowered.
- Blinking and subtle eye motion continue.
- Local phrases such as `correct` or `wrong` can trigger `yes` or `no` head gestures.
- The intro-mode `wrong` gesture now performs `left -> right -> center`.

Typical phrases:

- `intro mode`
- `switch to intro mode`
- `enable intro`

## Gemini Configuration

Each live connection is created with:

- `response_modalities` set to audio
- input and output audio transcription enabled
- the robot tool declarations from [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py)
- a system instruction built by [robot_prompt.py](/home/redleader/gemini_robot/robot_prompt.py)

The prompt currently tells Gemini to:

- introduce Ivan naturally
- use camera context continuously
- use OCR when visible text or math is shown
- only move when movement is explicitly requested
- keep movement semantics separated between look, head move, and head tilt
- stay nonverbal in `intro` mode
- offer short feature tours before going deep
- remember session facts provided by the user

When the runtime changes mode during a live session, [robot_session.py](/home/redleader/gemini_robot/robot_session.py) now sends a short mode-update message so Gemini stays aligned with the current mode without dropping session context.

## Tool API

Gemini receives these robot tools:

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

Execution happens in [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py).

Important current behavior:

- command tools are suppressed for a short window after local movement commands
- `tilt_head` is separate from left/right look direction
- `read_visible_text` supports `auto` and `document`

## Local Spoken Command Fallback

User transcripts are also checked by `execute_local_voice_command()` so the robot can stay responsive even without a model tool call.

Current locally recognized categories include:

- mode switching such as `enable tracking`, `stop tracking`, and `intro mode`
- OCR triggers such as `read this` and `solve this equation`
- look commands such as `look left`, `look up`, and `look center`
- head movement commands such as `turn head left` and `turn head right`
- tilt commands such as `tilt left`, `tilt right`, `head up`, and `head down`
- neutral commands such as `center`, `home`, and `neutral`
- intro-mode yes/no feedback phrases such as `that is correct` and `that is wrong`

After local movement or mode-switch commands, the runtime can:

- flush pending model audio
- suppress model audio temporarily
- suppress model movement tool calls temporarily
- schedule a delayed command-mode follow-up prompt

Repeated identical streaming transcripts are also deduplicated briefly before local command execution so one spoken phrase is less likely to trigger the same action more than once.

## Camera Pipeline

[robot_camera.py](/home/redleader/gemini_robot/robot_camera.py) manages the live camera path.

Current behavior includes:

- Picamera2 preview capture at the configured capture size
- frame enhancement using CLAHE, brightness adjustment, gamma, and sharpening
- MediaPipe face detection when available
- OpenCV Haar cascade face fallback
- OpenCV HOG person detection fallback
- target smoothing and target hold behavior for tracking
- JPEG encoding for Gemini input
- preview overlays for detections and recent speech text

Model-upload frames are clamped to the configured maximum size even when the capture size is larger than the model frame target.

The preview HUD can display:

- recent user speech as `Heard`
- recent model speech as `Said`
- current detection labels such as `Primary Face` or `Person`

## Audio Pipeline

[robot_audio.py](/home/redleader/gemini_robot/robot_audio.py) handles both streaming directions.

It currently:

- opens mic and speaker devices with fallbacks
- sends microphone PCM audio to Gemini
- plays model audio through the selected output device
- drives jaw motion from playback RMS
- blocks mic upload while Ivan is talking
- waits briefly after speech to reduce self-capture
- slows or speeds camera uploads based on control mode

Camera frame pacing is mode-sensitive:

- `tracking` sends faster
- `command` sends at a moderate rate
- `intro` sends more slowly

## OCR Flow

[robot_ocr.py](/home/redleader/gemini_robot/robot_ocr.py) reads from the latest camera frame and uses the local Tesseract binary.

Important current behavior:

- OCR availability is checked at runtime
- `document` mode uses a centered crop before preprocessing
- multiple image variants are tested
- simple visible math expressions are extracted when possible
- clear errors are returned if OCR is unavailable or no frame exists

## Memory Flow

[robot_memory.py](/home/redleader/gemini_robot/robot_memory.py) stores short session memory in [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json).

The current extractor saves:

- name
- likes
- remembered facts
- favorites expressed in natural language

## Session Handling

[robot_session.py](/home/redleader/gemini_robot/robot_session.py) processes each live response.

For each response it may:

- update latest user, model, and combined transcription fields
- update last user activity time
- store memory from the user transcript
- run the local spoken command parser
- skip duplicate near-identical partial transcripts for local actions and memory updates
- queue model audio for playback
- discard model audio during intro mode or local quiet windows
- send a short live mode-update message after successful mode changes
- execute tool calls and send function responses back to Gemini

## Failure And Recovery

The runtime is designed to keep going when possible.

- Missing servo hardware falls back to reduced software-only behavior.
- Missing camera dependencies disable the camera path instead of crashing startup.
- OCR can be unavailable without preventing the rest of the app from running.
- If the live Gemini session errors, the runtime logs it, clears pending audio, recenters the servos, waits briefly, and reconnects.
- On shutdown, the runtime stops background tasks, closes audio streams, saves memory, and recenters the servos.

## Backup Workflow

Use [backup_repo.sh](/home/redleader/gemini_robot/backup_repo.sh) to stage, commit if needed, and push the current branch:

```bash
./backup_repo.sh
./backup_repo.sh "your message here"
```
