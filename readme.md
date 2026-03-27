  1. Command vs Tracking modes (mutually exclusive)
      - Enable command mode: say “enable command”
      - Disable command mode (switch to tracking): say “disable command”
      - Enable tracking mode: say “enable tracking”
      - Disable tracking mode (switch to command): say “disable tracking”
      - Only one mode is active at a time.
  2. Head movement commands (no mixing)
      - Tilt left/right (only head tilt servo):
          - “tilt left”
          - “tilt right”
      - Pitch up/down (only head pitch servo):
          - “head up” / “nod up”
          - “head down” / “nod down”
      - Yaw left/right (only head yaw servo):
          - “yaw left” / “turn head left”
          - “yaw right” / “turn head right”
  3. Center/Neutral
      - Say “center”, “home”, or “neutral”
      - All servos return to neutral, including head tilt.
  4. Camera overlays
      - Face landmark 436 marker only (no face box).
      - Hand boxes labeled “hand”.
      - Object boxes from IMX500 (non-person).
  5. Tracking priority (when tracking is enabled)
      - Hand > Face (L436) > Objects (non-person) > Fallback motion/face logic.
  6. Conversation style
      - Ivan introduces himself naturally when asked.
      - If someone asks what he can do, he offers a short feature tour first.
      - If someone asks about a specific feature, he explains it briefly and asks whether they want the best way to use it.
      - You can change his TTS voice with `IVAN_VOICE_NAME` if you want a different tone.

Backup command:
- Run `./backup_repo.sh` to save all tracked and new files in this repo, create a commit if needed, and push to GitHub.
- Run `./backup_repo.sh "your message here"` if you want a custom commit message.
