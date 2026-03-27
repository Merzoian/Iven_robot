# Ivan Robot

Ivan is a conversational robotic head with live audio, live camera input, servo-driven motion, OCR, tracking, and short-term memory.

Valentina, a Senior Computer Engineering student at BYU-Idaho, created this project and brought Ivan to life for her Advanced Embedded Systems class.

## What Ivan Can Do

- Hold a live conversation through Gemini realtime audio.
- Remember names, likes, and short facts during a session.
- Move eyes, jaw, and head with servo control.
- Track faces and motion automatically.
- Stay in a quiet nonverbal `intro` mode with yes/no head gestures.
- Describe what he sees through the camera.
- Read visible text, handwriting, numbers, and simple math with local OCR.
- Speak with configurable voice output.

## Main Entry Point

- Run [main4_robot.py](/home/redleader/gemini_robot/main4_robot.py). It simply starts [robot_app.py](/home/redleader/gemini_robot/robot_app.py).

## Core Files

- [robot_app.py](/home/redleader/gemini_robot/robot_app.py): main runtime, Gemini session loop, hardware startup, reconnect behavior.
- [robot_motion.py](/home/redleader/gemini_robot/robot_motion.py): head and eye movement behavior, tracking motion, blinking, gestures.
- [robot_camera.py](/home/redleader/gemini_robot/robot_camera.py): Picamera2 capture, frame enhancement, tracking, HUD, preview.
- [robot_audio.py](/home/redleader/gemini_robot/robot_audio.py): microphone input, speaker playback, jaw lip sync, camera upload pacing.
- [robot_commands.py](/home/redleader/gemini_robot/robot_commands.py): tool execution and deterministic spoken command parsing.
- [robot_ocr.py](/home/redleader/gemini_robot/robot_ocr.py): local OCR with Tesseract, document mode, simple math extraction.
- [robot_prompt.py](/home/redleader/gemini_robot/robot_prompt.py): Ivan’s system instruction and feature wording.
- [robot_memory.py](/home/redleader/gemini_robot/robot_memory.py): session memory load/save and fact extraction.
- [robot_tools.py](/home/redleader/gemini_robot/robot_tools.py): tool schema exposed to Gemini.
- [robot_config.json](/home/redleader/gemini_robot/robot_config.json): runtime tuning overrides.
- [ivan_servo_calibration.json](/home/redleader/gemini_robot/ivan_servo_calibration.json): servo calibration data.

## Control Modes

### Command Mode

Use command mode for direct movement requests.

- Ivan accepts manual head and gaze movement commands.
- Tracking is disabled.
- This is the default conversational mode unless you switch modes.

Say:

- `enable command`
- `disable tracking`
- `stop following`

### Tracking Mode

Use tracking mode when Ivan should follow what is in front of him.

- Ivan follows targets automatically.
- Manual movement commands are rejected while tracking is active.
- Tracking priority is hand, then face, then detected objects, then fallback motion or face logic.

Say:

- `enable tracking`
- `start tracking`
- `follow me`

### Intro Mode

Use intro mode for quiet nonverbal behavior.

- Ivan does not speak in intro mode.
- He keeps his head slightly lowered.
- He still blinks and performs subtle eye movement.
- He answers yes or no with head gestures only.

Say:

- `intro mode`
- `switch to intro mode`
- `enable intro`

## Movement Phrases

### Head Direction

- `look left`
- `look right`
- `look up`
- `look down`
- `look center`

### Direct Head Motion

- `turn head left`
- `turn head right`
- `tilt left`
- `tilt right`
- `head up`
- `head down`

### Neutral Position

- `center`
- `home`
- `neutral`

## Vision And OCR Phrases

### Scene Awareness

- `what do you see`
- `what are you seeing`

### Reading Text

- `read this`
- `can you read this`
- `what does this say`

### Reading Math

- `read this equation`
- `solve this equation`

Notes:

- OCR works best when the text is centered, steady, and close enough to read.
- `document` OCR mode is used for paper, phones, whiteboards, worksheets, and handwriting.
- Simple visible equations can be read and answered directly when they are clear.

## Conversation Behavior

- Ivan introduces himself naturally when asked who he is or what he can do.
- If someone asks about features, he gives a short feature tour first.
- If someone asks about one feature, he explains it briefly and asks whether they want the best way to use it.
- Ivan knows Valentina created this project and brought him to life for her Advanced Embedded Systems class at BYU-Idaho.
- Voice output can be changed with `IVAN_VOICE_NAME`.

## Camera Preview Notes

- The preview shows a recent speech HUD.
- Face landmark `436` is used as the face marker instead of a full face box.
- Hand boxes are labeled `hand`.
- Non-person object boxes can come from the IMX500 path when available.

## Memory

Ivan stores short session memory in [ivan_session_memory.json](/home/redleader/gemini_robot/ivan_session_memory.json).

He can remember phrases such as:

- `my name is ...`
- `i am ...`
- `i like ...`
- `remember that ...`
- `my favorite color is ...`

## Local OCR Requirements

- OCR depends on the local `tesseract` binary.
- The default OCR command comes from `IVAN_OCR_COMMAND` or falls back to `tesseract`.
- The default OCR language comes from `IVAN_OCR_LANG` or falls back to `eng`.

## Backup Workflow

Use the repo backup script to save and push changes.

```bash
./backup_repo.sh
./backup_repo.sh "your message here"
```

It stages changes, creates a commit only when needed, and pushes the current branch to GitHub.
