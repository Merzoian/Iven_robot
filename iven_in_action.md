# Ivan in Action

This file is the architecture and execution walkthrough for the current Ivan robot project.

The runtime entry point is [main4_robot.py](/home/redleader/gemini_robot/main4_robot.py), which simply calls `run()` from [robot_app.py](/home/redleader/gemini_robot/robot_app.py).

## High-Level Flow

1. Load configuration, calibration, and saved session memory.
2. Initialize servo control if hardware is available.
3. Open microphone and speaker streams.
4. Start camera capture and local preview.
5. Connect to Gemini live with audio, image input, and robot tool declarations.
6. Send live mic and camera data to the model.
7. Receive transcription, speech audio, and tool calls from the model.
8. Apply movement, OCR, tracking, lip sync, memory updates, and command suppression logic in real time.
9. Trigger a delayed command-mode follow-up prompt when Ivan is idle after local commands.

## Project Structure

- [robot_app.py](/home/redleader/gemini_robot/robot_app.py): main runtime and orchestration.
- [robot_motion.py](/home/redleader/gemini_robot/robot_motion.py): natural motion loops, tracking motion, intro posture, gestures.
- [robot_audio.py](/home/redleader/gemini_robot/robot_audio.py): mic capture, playback, jaw animation, camera send pacing.
- [robot_camera.py](/home/redleader/gemini_robot/robot_camera.py): camera capture, enhancement, target detection, HUD, preview.
- [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py): local command parser and tool execution.
- [robot_ocr.py](/home/redleader/gemini_robot/robot_ocr.py): OCR and simple math extraction.
- [robot_prompt.py](/home/redleader/gemini_robot/robot_prompt.py): model behavior instructions.
- [robot_memory.py](/home/redleader/gemini_robot/robot_memory.py): session memory logic.
- [robot_session.py](/home/redleader/gemini_robot/robot_session.py): response handling for transcription, audio, and tool calls.
- [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py): Gemini tool schema.

## Runtime Startup

When the program starts, it:

- loads servo calibration from [ivan_servo_calibration.json](/home/redleader/gemini_robot/ivan_servo_calibration.json)
- loads runtime overrides from [robot_config.json](/home/redleader/gemini_robot/robot_config.json)
- restores session memory from [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json)
- installs cleanup and shutdown handlers
- enters the async runtime in `robot_app.run()`

## Mode System

Ivan has three main control modes.

### Command Mode

- Default conversational mode for direct movement requests.
- Manual head and gaze actions are allowed.
- Tracking is not active.
- Local movement and mode-switch commands can temporarily suppress model speech and tool reactions.
- After a short idle period, Ivan can ask what the user wants next.

Typical phrases:

- `enable command`
- `disable tracking`
- `stop following`
- `look left`
- `center`

### Tracking Mode

- Automatic following mode.
- Manual movement commands are rejected while tracking is active.
- Tracking uses recent visual targets and smoothing so motion is less jerky.

Tracking priority:

- hand
- face
- object
- fallback motion or remembered face location

Typical phrases:

- `enable tracking`
- `start tracking`
- `follow me`
- `stop tracking`

### Intro Mode

- Quiet nonverbal mode.
- Ivan does not produce spoken replies.
- The head stays slightly lowered.
- Blinking and subtle eye motion continue.
- Yes and no are expressed with `gesture_head`.
- Local spoken feedback like `yes`, `correct`, `no`, and `wrong` can trigger yes/no gestures.

Typical phrases:

- `intro mode`
- `switch to intro mode`
- `enable intro`

## Model Prompt And Identity

The system instruction in [robot_prompt.py](/home/redleader/gemini_robot/robot_prompt.py) tells Gemini that:

- Ivan is a robotic head
- he should introduce himself naturally
- he should offer a short feature tour before going deep
- he should use camera frames continuously
- he should use OCR when the user is showing text or math
- he should only move when explicitly asked
- in command mode, `look_direction` is only for left, right, up, down, or center
- in command mode, `tilt_head` is only for tilt left, right, or center
- after command-mode movement, he should stay quiet and wait for the next command
- he should only enable tracking when explicitly requested
- he should stay nonverbal in `intro` mode
- after enough silence, he may ask a simple follow-up such as `What do you want me to do next?`
- Valentina created the project and brought him to life for her Advanced Embedded Systems class at BYU-Idaho

## Tool API

Gemini receives these robot tools from [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py):

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

These tools are executed by [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py).

## Local Spoken Command Fallback

Ivan also has a deterministic local parser in `execute_local_voice_command()`.

This matters because movement and OCR triggers can still work even if the model does not issue a tool call.

Recognized movement and mode phrases include:

- `enable tracking`
- `stop tracking`
- `disable tracking`
- `switch to intro mode`
- `look left`
- `look right`
- `look up`
- `look down`
- `turn head left`
- `turn head right`
- `tilt left`
- `tilt right`
- `tilt left side`
- `tilt right side`
- `that is correct`
- `that is wrong`
- `center`
- `home`
- `neutral`

Local command handling also:

- flushes pending model audio after local movement and mode-switch commands
- suppresses model movement tool calls briefly after local movement commands
- schedules a delayed command-mode follow-up prompt

Recognized OCR phrases include:

- `read this`
- `can you read this`
- `what does this say`
- `read this equation`
- `solve this equation`

Prompt-guided live vision phrases include:

- `what do you see`
- `what are you seeing`

## Vision Pipeline

[robot_camera.py](/home/redleader/gemini_robot/robot_camera.py) manages the live camera path.

Main behavior:

- starts Picamera2 preview capture
- applies image enhancement for contrast and clarity
- performs face and person detection
- tracks recent targets with smoothing
- overlays recent speech as a HUD with separate `Heard` and `Said` captions
- keeps the latest frame and JPEG ready for OCR and Gemini input

Preview overlays and priorities:

- face marker uses landmark `436`
- hand boxes are labeled `hand`
- non-person object boxes can come from the IMX500 path
- tracking priority is hand, then face, then object, then fallback motion logic

## OCR And Visible Math

[robot_ocr.py](/home/redleader/gemini_robot/robot_ocr.py) performs local OCR with Tesseract.

Behavior:

- reads from the latest camera frame
- preprocesses multiple variants of the image
- supports `auto` mode and `document` mode
- extracts possible simple math expressions from recognized text
- returns the best-scoring OCR result

Best use cases:

- paper
- phone screens
- worksheets
- whiteboards
- handwriting
- printed labels
- numbers
- simple equations

Limitations:

- tiny text
- blurred text
- dense math
- complex formulas
- messy handwriting

## Audio And Lip Sync

[robot_audio.py](/home/redleader/gemini_robot/robot_audio.py) handles live audio input and output.

It:

- opens mic and speaker devices with fallbacks
- sends mic PCM audio to Gemini
- plays model audio back through the speaker
- drives jaw motion from speech loudness
- suppresses mic upload while Ivan is speaking to reduce feedback
- keeps mic upload paused briefly after speech to reduce self-capture
- pauses camera uploads while speech is actively playing
- changes camera upload speed by mode so tracking stays more responsive than intro mode

## Memory System

[robot_memory.py](/home/redleader/gemini_robot/robot_memory.py) stores short session memory.

It can extract and save:

- names
- likes
- remembered facts
- favorites such as `my favorite color is blue`

Memory is saved back to [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json).

## Session Handling

[robot_session.py](/home/redleader/gemini_robot/robot_session.py) processes each Gemini response.

For each response it may:

- store separate latest user and model transcriptions for the camera HUD
- update last user activity time
- update memory from the user’s words
- run the local spoken command parser
- queue model audio for playback
- suppress model audio or command tools during local quiet-mode windows
- execute tool calls and send tool responses back to Gemini

## Motion System

[robot_motion.py](/home/redleader/gemini_robot/robot_motion.py) contains the continuous movement behavior.

It is responsible for:

- smooth head hold behavior
- idle eye motion
- blinking and double-blinks
- tracking-based eye and head aiming
- intro-mode calmer posture
- gesture-based yes and no motion
- returning toward neutral or requested poses

## Failure And Recovery

The runtime is built to keep going when possible.

- If hardware setup fails, the program can continue in a reduced software-only state.
- If the live Gemini session disconnects, the runtime logs the reason, clears pending audio, recenters the servos, waits briefly, and reconnects.
- On exit, it stops camera and audio resources, saves memory, and recenters the servos.

## Backup Workflow

Use [backup_repo.sh](/home/redleader/gemini_robot/backup_repo.sh) to save and push changes:

```bash
./backup_repo.sh
./backup_repo.sh "your message here"
```

The script stages all changes, commits only if needed, and pushes the current branch to GitHub.
