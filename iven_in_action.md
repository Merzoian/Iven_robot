# Iven in Action

Here is the execution-order walkthrough of `main4_robot.py`.

## Startup

When you run the file, it first loads saved session memory from `ivan_session_memory.json`, registers cleanup handlers, and installs SIGINT/SIGTERM shutdown hooks. Then it enters `asyncio.run(main())`.

## 1. Global setup

At import time it defines:

- Audio device indexes, sample rate, chunk size, and ALSA/JACK env vars.
- Servo channel mappings for eyes, eyelids, jaw, pitch, yaw, and tilt.
- Default calibration values and runtime state flags like `tracking_enabled`, `command_enabled`, `control_mode`, `audio_queue`, current head pose, and session memory.

## 2. Calibration helpers

Before any motion, the file has utilities to load servo limits and neutral values:

- `apply_servo_calibration()` reads servo metadata already present in the `ServoController` and copies it into globals.
- `_apply_calibration_overrides()` reads JSON override fields into globals.
- `_apply_calibration_to_maestro()` pushes the global calibration values back into `maestro.servos`.
- `load_calibration_file()` loads `ivan_servo_calibration.json`.

So calibration can come from both the controller config and a local JSON file.

## 3. Basic hardware helpers

The next small helpers are used everywhere:

- `get_maestro_port()` finds the USB serial port.
- `clamp()` and channel limit helpers constrain motion.
- `set_control_mode()` flips between `tracking`, `command`, and `intro` modes.
- `open_audio_streams()` opens mic and speaker streams with fallbacks.

## 4. Servo motion primitives

These are the low-level movement functions:

- `set_eyelids()` opens/closes lids.
- `set_gaze()` moves the eye servos.
- `set_head_pose()` moves yaw/pitch/tilt.
- `center_all_servos()` restores neutral eyes, lids, head, and jaw.
- `request_head_pose()` updates the desired resting head pose, which the background head thread smooths toward.

## 5. Background movement threads

Once the Maestro is connected, two daemon threads run continuously:

`head_hold_worker()`

- If a manual head override is active, it holds that pose.
- Else if tracking is active and fresh target data exists, it points the head toward the target.
- Else it returns toward the requested resting pose with a small breathing-like pitch motion.
- In `intro` mode, the resting pose keeps the head slightly lowered.
- It smooths motion each cycle so it looks less robotic.

`eye_movement_worker()`

- Sets eyelid and eye servo speeds.
- Blinks at random intervals.
- Occasionally double-blinks.
- If tracking is active, follows the tracked target.
- If gaze is manually held, keeps eyes fixed.
- While speaking, keeps eye motion smaller and steadier.
- In `intro` mode, eye motion stays calmer and lower-energy while blinking remains natural.
- While idle, performs random micro-saccades and gaze drifts.

## 6. Audio error suppression

The ALSA error handler suppresses low-level sound library warnings so the console stays cleaner.

## 7. Maestro initialization

`init_maestro()`:

- Finds the Maestro USB port.
- Instantiates `ServoController`.
- Loads calibration JSON.
- Pushes calibration into the controller and re-reads limits.
- Resets head state to neutral.
- Sets servo speeds/accelerations.
- Closes the jaw and sets the head to neutral.

If anything fails, it keeps running with `maestro = None`, so the program can still do audio/model work.

## 8. Tracking target conversion

`set_tracking_target()` converts camera coordinates into smoothed eye offsets `tracked_lr` and `tracked_ud`. The eye and head worker threads consume those values.

## 9. Memory system

There are three layers here:

- `save_session_memory()` writes name/likes/facts to disk.
- `load_session_memory()` restores them at startup.
- `apply_memory_from_text()` extracts user facts from transcribed speech.

Examples it recognizes:

- "my name is ..."
- "I am ..."
- "I like ..."
- "remember that ..."
- "my favorite color is blue"

## 10. System prompt generation

`build_system_instruction()` builds the prompt sent to Gemini. It tells the model:

- its name is Ivan,
- it is a robotic head,
- it is in a live conversation,
- to introduce itself naturally when asked,
- to offer a short feature tour when someone asks what it can do,
- to explain one feature and then ask whether the user wants to know how to use it well,
- to remember user details,
- to use camera frames,
- to only move when explicitly asked,
- to only enable tracking when explicitly asked,
- to stay silent and use head gestures only while in `intro` mode,
- and it includes stored session memory.

## 11. Robot tool API

`execute_robot_function()` is the server-side implementation of tool calls from Gemini.

Supported actions:

- `set_mode`
- `set_tracking`
- `look_direction`
- `move_head`
- `center_servos`
- `gesture_head`
- `describe_features`
- `feature_help`
- `read_visible_text`

Behavior details:

- In `tracking` mode, manual movement commands are rejected.
- `set_mode` can switch into `intro`, which keeps Ivan nonverbal with a lowered resting head pose.
- `look_direction` changes head yaw/pitch and then centers the eyes.
- `move_head` directly sets calibrated pulse values for yaw/pitch/tilt for a limited duration.
- `center_servos` returns everything to neutral.
- `gesture_head` performs a nonverbal yes/no response using nodding or side-to-side head movement.
- `describe_features` returns a short overview of Ivan's capabilities.
- `feature_help` explains one named feature and how it is best used.
- `read_visible_text` runs OCR for visible text, numbers, handwriting, or simple math.

## 12. Spoken command fallback

`execute_local_voice_command()` is a deterministic local parser. It lets the robot respond to spoken commands even if the model does not emit a tool call.

It recognizes phrases like:

- "enable tracking"
- "stop tracking"
- "switch to intro mode"
- "look left/right/up/down"
- "turn head left/right"
- "tilt left/right"
- "center", "home", "neutral"

This is important because it means movement can happen directly from transcription text.

## 13. Camera manager

`CameraManager` handles the camera pipeline.

`start()`:

- Starts Picamera2 preview mode.
- Applies camera controls like exposure/white-balance/contrast/sharpness.

`_enhance_frame()`:

- Improves contrast and sharpness before display and model upload.

`_track_from_frame()`:

- If tracking is off, does nothing.
- If tracking is on, downsamples the frame and tries face detection first.
- If a face is found, picks the largest face and sends its center to `set_tracking_target()`.
- If no face is found but a face was seen recently, it temporarily keeps using the last known face.
- If no face is available, it falls back to motion detection using frame differencing and image moments.

`_draw_hud()`:

- Draws recent recognized speech onto the camera preview window.

`capture_loop()`:

- Runs continuously.
- Captures frames, rotates them 180 degrees, enhances them, tracks faces/motion, draws HUD text, displays a local OpenCV preview window, compresses frames to JPEG, and stores the latest one for Gemini upload.

`stop()`:

- Stops Picamera2 and closes the OpenCV windows.

## 14. Audio output and lip sync

`playback_worker()`:

- Waits for model-generated audio in `audio_queue`.
- Marks Ivan as speaking.
- Computes RMS loudness.
- Opens the jaw proportionally to loudness.
- Upsamples 16 kHz model audio to 48 kHz for playback.
- Duplicates mono to stereo if needed.
- Plays through the speaker stream.
- Closes the jaw when audio finishes.

## 15. Audio input

`send_mic()`:

- Continuously reads microphone audio.
- If Ivan is currently speaking, it suppresses mic upload to avoid feedback.
- Downsamples 48 kHz mic audio to 16 kHz by taking every third sample.
- Sends PCM audio to Gemini live input.

## 16. Camera upload to Gemini

`send_camera()`:

- Continuously checks for the latest JPEG from `CameraManager`.
- Sends frames to Gemini as realtime image input about every 170 ms.

## 17. Main async runtime

`main()` is the real orchestrator.

It does this in order:

1. Calls `init_maestro()`.
2. Starts eye/head worker threads if servo hardware exists.
3. Creates a Gemini client using `GOOGLE_API_KEY`.
4. Opens PyAudio and mic/speaker streams.
5. Starts the playback worker task.
6. Creates `CameraManager` and starts camera capture.
7. Declares the robot tool schema for Gemini.
8. Enters a reconnecting loop around `client.aio.live.connect(...)`.

Inside the live session:

- It configures audio output, the selected voice from `IVAN_VOICE_NAME` or default `Achird`, transcriptions, tool declarations, and the system instruction.
- Starts `send_mic()` and `send_camera()` tasks.
- Iterates over `session.receive()` responses.

For each response:

- If there is input transcription, it stores it for the HUD, updates memory, and runs local spoken-command matching.
- If the model emits audio parts, it pushes them into `audio_queue` unless Ivan is in `intro` mode.
- If the model emits function calls, it runs `execute_robot_function()` and sends tool responses back to Gemini.

If the session crashes:

- It logs the reconnect reason.
- Clears pending audio.
- Recenters servos.
- Waits one second.
- Reconnects.

## 18. Cleanup

On exit, `main()`:

- Cancels background async tasks.
- Stops camera/audio devices.
- Terminates PyAudio.
- Saves session memory.
- Recenters servos.

## Overall flow

In one sentence: microphone and camera go into Gemini, Gemini returns speech and optional tool calls, and the script turns those into spoken responses, lip-synced jaw motion, feature-aware conversation, natural eye/head animation, optional face/motion tracking, intro-mode nonverbal behavior, and short-term remembered user facts.
