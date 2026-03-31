# Final Project Report

## Project Title

Ivan: A Conversational Robotic Head with Live Gemini Audio, Vision, OCR, Tracking, and Servo Motion

## Student Information

- Student: Valentina
- Program: Computer Engineering
- Institution: Brigham Young University-Idaho
- Course: Advanced Embedded Systems
- Date: March 30, 2026

## Abstract

This project presents Ivan, a conversational robotic head designed to combine embedded systems, real-time media processing, artificial intelligence, and physical actuation into a single interactive platform. Ivan accepts live microphone input, processes camera context, produces spoken responses, and controls head and eye motion through a Pololu Maestro servo controller. The system integrates Google Gemini live audio for natural conversation, local fallback command handling for deterministic control, optical character recognition for reading visible text and simple equations, and short session memory for basic personalized interaction.

The project was developed as an applied embedded systems solution that demonstrates the integration of software intelligence with hardware motion control. Ivan supports multiple operating modes, including command mode, tracking mode, and intro mode, allowing the system to adapt its behavior to different interaction scenarios. The final implementation shows that a robotic head can deliver responsive multimodal interaction while remaining robust when some hardware or software components are unavailable. The project also highlights practical engineering concerns such as asynchronous event handling, mode synchronization, audio suppression, and graceful degradation.

## 1. Introduction

Modern embedded systems increasingly combine sensing, computation, networking, and physical output to produce interactive behavior. Robotics systems in particular benefit from multimodal interfaces, where voice, vision, and motion are coordinated to create more natural communication between people and machines. The objective of this project was to build a robotic head capable of real-time conversation, visual awareness, physical motion, and selective memory while operating on embedded hardware.

Ivan was created as a runtime system for a conversational robotic head. The design goal was not simply to animate servos or produce scripted speech, but to create an integrated system that can listen to a user, respond with synthesized speech, observe its environment through a camera, read visible text through OCR, and physically express behavior using head and eye movement. This made the project a strong example of embedded systems engineering because it required reliable coordination between hardware control, real-time software services, and AI-assisted interaction.

The completed project demonstrates a functioning architecture for embedded conversational robotics. It combines cloud-based Gemini live interaction with local control paths so that critical movement and mode-switching behaviors remain responsive even when model tool calls are delayed or unavailable. As a result, Ivan is both an AI-driven and a deterministic embedded system.

## 2. Project Objectives

The major objectives of the project were as follows:

- Design and implement a conversational robotic head capable of real-time spoken interaction.
- Integrate live audio and visual context using the Gemini API.
- Control physical motion through servos for eyes, jaw, head yaw, head pitch, and head tilt.
- Support multiple behavioral modes for different interaction styles.
- Add local OCR so the robot can read visible text, handwriting, numbers, and simple equations.
- Provide short session memory so the robot can remember names, preferences, and simple facts.
- Implement deterministic local voice command handling as a fallback to improve responsiveness.
- Build a modular Python codebase that separates runtime management, audio, camera, motion, OCR, commands, memory, and session handling.
- Validate major subsystems with automated tests.

## 3. Problem Statement

Many simple robot heads can move or speak, but far fewer can combine live conversation, visual awareness, local reasoning tasks, and physically expressive behavior in a coordinated embedded runtime. A major challenge is that each subsystem operates at different speeds and with different reliability constraints. Audio streaming must occur continuously, camera frames must be paced and resized appropriately, movement commands must remain safe and understandable, and the overall runtime must stay usable even if hardware such as a camera or servo controller is unavailable.

The problem addressed in this project was therefore how to design a robotic head runtime that provides:

- natural voice interaction
- physical motion control
- multimodal awareness through a camera
- OCR-based text reading
- local fallback behavior
- basic conversational memory
- practical robustness in an embedded environment

## 4. System Overview

Ivan is built as a Python runtime whose main entry point is `main4_robot.py`. This file imports `run()` from `robot_app.py`, which starts the full runtime. The system architecture is modular and organized around functional subsystems.

At a high level, the system works as follows:

1. The runtime loads configuration, calibration data, and saved session memory.
2. Hardware interfaces are initialized, including the Maestro servo controller when available.
3. Audio input and output streams are opened.
4. Camera capture starts if Picamera2 support is present.
5. Gemini tool declarations and a system prompt are created.
6. A live Gemini session is opened using audio, transcription, and camera context.
7. User speech and camera frames are streamed into the live session.
8. Model responses, transcripts, and tool calls are received.
9. Local command execution, OCR, movement, and memory updates are performed.
10. The system reconnects automatically if the live session drops.

This design creates a multimodal loop in which Ivan continuously listens, observes, thinks, and acts.

## 5. Hardware and Software Requirements

### 5.1 Hardware Components

The project was designed around embedded robotics hardware and optional peripherals. Based on the repository and runtime design, the main hardware components are:

- Raspberry Pi or equivalent embedded Linux platform
- camera module compatible with Picamera2
- microphone input device
- speaker or audio output device
- Pololu Maestro servo controller
- servos for eyes, jaw, head yaw, head pitch, and head tilt

Some hardware features are optional at runtime. If the servo controller is unavailable, the software can continue in a reduced mode. If camera support is missing, the vision path is disabled. This was an intentional design choice to improve development flexibility and fault tolerance.

### 5.2 Software Components

The repository does not currently include a pinned dependency manifest, but the implementation expects the following major software dependencies:

- Python 3
- `google-genai`
- `pyaudio`
- `numpy`
- `opencv-python`
- `mediapipe`
- `pyserial`
- `picamera2`
- local `tesseract`

### 5.3 Configuration and Runtime Files

The project uses several configuration and state files:

- `robot_config.json` for runtime tuning, device indexes, frame size, timing, tracking gains, and OCR settings
- `ivan_servo_calibration.json` for servo pulse calibration
- `ivan_session_memory.json` for saved short session memory

Environment variables are also used, including:

- `GOOGLE_API_KEY`
- `IVAN_VOICE_NAME`
- `IVAN_LOG_LEVEL`
- `IVAN_OCR_COMMAND`
- `IVAN_OCR_LANG`

## 6. Software Architecture

The architecture of Ivan is modular, with each Python file focusing on a specific runtime concern. This separation of responsibilities made the project easier to develop, reason about, and test.

### 6.1 Main Runtime Files

- `robot_app.py`: assembles the runtime, starts the Gemini connection loop, manages reconnects, and handles shutdown
- `robot_runtime.py`: stores shared mutable runtime state and loads JSON configuration
- `robot_motion.py`: handles servo calibration, head hold logic, gaze control, blinking, gestures, and tracking math
- `robot_camera.py`: manages Picamera2 capture, frame enhancement, detection, preview HUD behavior, and JPEG generation
- `robot_audio.py`: handles microphone capture, speaker playback, jaw lip sync, and camera-send pacing
- `robot_commands.py`: executes Gemini tool calls and deterministic local spoken commands
- `robot_session.py`: processes transcripts, model audio chunks, and tool-call responses
- `robot_ocr.py`: performs OCR preprocessing, Tesseract execution, and visible math extraction
- `robot_prompt.py`: defines the system instruction and feature-tour wording
- `robot_memory.py`: extracts, loads, and saves session memory
- `robot_tools.py`: declares the robot tools exposed to Gemini
- `servo_controller.py`: provides serial control for the Maestro board

### 6.2 Architectural Benefits

This architecture provides several important engineering advantages:

- clear separation of hardware control and AI logic
- independent testing of critical subsystems
- easier debugging and maintenance
- graceful handling of optional hardware
- better scalability for future features

## 7. Functional Design

### 7.1 Conversational AI Integration

One of the central features of Ivan is its live Gemini session. The runtime uses Gemini for:

- live microphone input
- spoken audio output
- user and model transcript handling
- camera-aware contextual responses
- tool calls for robot actions

The configured live model is `gemini-2.5-flash-native-audio-latest`. The prompt instructs Gemini to use camera context continuously, keep movement behavior explicit, provide short feature tours, read visible text when needed, and remain nonverbal in intro mode.

An important part of the design is that mode changes are synchronized back into the live Gemini session so the model stays aligned with current runtime behavior without requiring a reconnect.

### 7.2 Motion Control

Ivan controls physical expression through a Pololu Maestro servo controller. Motion support includes:

- eye movement
- jaw movement during speech playback
- head yaw
- head pitch
- head tilt
- gestures such as yes/no style head motions

This gives the robot a stronger physical presence and helps connect conversational output with embodiment. In addition to direct commands, motion is also influenced by tracking behavior and quiet-mode suppression windows that prevent unwanted reactions immediately after manual local movement.

### 7.3 Camera Awareness and Tracking

The camera subsystem allows Ivan to observe its environment. The camera pipeline performs:

- live capture through Picamera2
- frame enhancement
- face detection
- person detection fallback
- target smoothing
- tracking target retention
- JPEG preparation for Gemini input

Tracking priority favors a primary face first, then a detected person, then recent remembered targets. This helps Ivan follow a person more naturally during interaction.

### 7.4 Optical Character Recognition

Ivan includes local OCR using Tesseract. OCR is designed to read:

- visible text
- handwriting
- numbers
- simple equations

The OCR system supports `auto` and `document` modes. This allows the robot to respond to commands such as reading a worksheet, paper, whiteboard, or phone screen. OCR was implemented locally so that the robot can perform basic visible-text extraction without relying solely on model interpretation.

### 7.5 Session Memory

The project includes a short-term memory system that can store facts spoken by the user. The current extractor supports patterns such as:

- "my name is ..."
- "I'm ..."
- "I like ..."
- "remember that ..."
- "my favorite ..."

This memory is saved to `ivan_session_memory.json`, allowing limited persistence across sessions.

### 7.6 Local Fallback Voice Commands

A strong design decision in this project was to implement deterministic local voice-command handling in addition to Gemini tool calls. This means Ivan can still respond reliably to important requests such as:

- enabling or disabling tracking
- switching modes
- moving eyes or head
- centering servos
- triggering OCR
- performing intro-mode yes/no gestures

This fallback path improves responsiveness and avoids total dependence on model tool execution for basic robot control.

## 8. Operating Modes

Ivan supports three primary operating modes.

### 8.1 Command Mode

Command mode is the default manual-control state. In this mode, the user can directly request movements such as looking left, turning the head, tilting, or centering the servos. After local movement commands, the runtime temporarily suppresses model speech and model movement reactions so the local command remains the dominant behavior.

### 8.2 Tracking Mode

Tracking mode enables automatic following behavior. Manual movement commands are rejected while tracking is active in order to avoid conflicting control signals. The camera subsystem drives tracking decisions based on face and person detection.

### 8.3 Intro Mode

Intro mode is a quiet, nonverbal presentation mode. Spoken output is suppressed, while blinking and subtle motion can continue. The default head pose is slightly lowered, and simple gesture feedback such as yes/no motion is still available. This mode is useful for demonstrations where speech should not interrupt the interaction.

## 9. Implementation Process

The implementation process focused on combining embedded device control with an AI-assisted multimodal runtime. The software was structured so that initialization, streaming, command execution, OCR, and shutdown were handled in distinct modules.

The startup sequence begins by loading configuration, calibration, and session memory. Hardware is initialized where available, then worker threads and asynchronous tasks are started. Audio input and output are opened, the camera loop is launched if supported, and a Gemini live session is created. From that point forward, the runtime continuously streams microphone audio and paced camera frames to the model while listening for transcripts, audio chunks, and tool calls.

Local command fallback and memory extraction are applied to transcripts so the robot can act even when the model does not immediately issue a tool call. This is a practical embedded-systems design choice because it reduces latency for important controls and improves perceived responsiveness.

## 10. Testing and Validation

The repository includes a `tests/` directory with automated tests covering multiple subsystems:

- `test_robot_commands.py`
- `test_robot_memory.py`
- `test_robot_motion.py`
- `test_robot_ocr.py`
- `test_robot_runtime.py`
- `test_robot_session.py`

These tests indicate that the project was validated beyond manual demonstration alone. Based on the available test structure, the following areas are explicitly covered:

- command parsing and execution behavior
- session memory extraction and persistence logic
- motion-related logic
- OCR behavior
- runtime configuration loading
- session-response handling

In addition to automated tests, the project design itself reflects validation against real runtime concerns:

- reconnection behavior if the live Gemini session drops
- disabled camera operation when camera support is unavailable
- reduced runtime behavior when the Maestro controller is unavailable
- OCR error reporting when Tesseract is not installed
- transcript deduplication to avoid repeated command triggering

Together, these indicate that the project was tested for both correct functionality and practical fault tolerance.

## 11. Results

The final project successfully produced a robotic head runtime with the following demonstrated capabilities:

- live voice-based interaction through Gemini audio
- physical head and eye movement through servo control
- jaw motion tied to speech playback
- camera-aware conversation
- automatic face/person tracking
- local OCR for text and simple equations
- deterministic local voice command handling
- multiple runtime modes
- short-term session memory
- modular code organization with automated tests

The project met its primary engineering objective of integrating AI interaction with embedded hardware control in a single runtime. It also demonstrated a thoughtful balance between cloud-assisted intelligence and local deterministic control.

## 12. Challenges and Solutions

### 12.1 Real-Time Coordination

One of the biggest challenges in this project was coordinating real-time audio, camera input, model responses, and servo motion. These processes operate at different speeds and can interfere with one another if not carefully managed.

This was addressed by separating functionality across dedicated modules and runtime tasks, using pacing logic for camera frames, and implementing suppression windows for speech and movement after local commands.

### 12.2 Hardware Availability

Embedded development often suffers from changing hardware availability during testing. A camera may be disconnected, a servo controller may not be present, or OCR software may not be installed on a development device.

The project addressed this by degrading gracefully. Hardware-dependent features can be disabled without crashing the full runtime, which improves development workflow and robustness.

### 12.3 Duplicate or Conflicting Commands

Live streaming transcripts can contain repeated partial phrases, and model responses can sometimes overlap with local command logic. This can lead to duplicate actions or conflicting movements.

The project mitigates this with brief transcript deduplication and temporary suppression of model movement and speech immediately after local manual commands.

### 12.4 Alignment Between Mode and Model

If the runtime switches mode locally but the AI model is unaware of the change, the robot may behave inconsistently.

The implementation solves this by sending mode updates back into the live session so Gemini remains aligned with the current operating state.

## 13. Engineering Significance

This project is a strong example of embedded systems engineering because it required the integration of:

- real-time sensor input
- actuator control
- asynchronous software processes
- fault-tolerant runtime behavior
- multimodal AI interaction
- modular software design

Rather than focusing on a single subsystem, Ivan demonstrates full-stack embedded integration from low-level serial servo control to high-level conversational AI. This makes it a meaningful capstone-style project for an advanced embedded systems course.

## 14. Limitations

Although the project achieved its primary goals, several limitations remain:

- the repository does not currently provide a pinned dependency file
- session memory is intentionally simple and limited in scope
- OCR quality depends on camera angle, lighting, and Tesseract accuracy
- tracking quality depends on available detections and camera conditions
- the system relies on networked Gemini access for full conversational capability
- hardware calibration and physical smoothness depend on the servo setup

These limitations are normal for an evolving embedded robotics platform and provide a useful basis for future work.

## 15. Future Improvements

Several logical extensions could improve the project:

- add a pinned requirements file for easier deployment
- expand memory beyond short pattern-based storage
- improve gesture expressiveness and emotional state modeling
- add stronger camera-based scene understanding
- improve OCR preprocessing for handwriting and low-light conditions
- add long-term usage logging and analytics
- improve mechanical enclosure and cable management
- support additional safety limits and servo diagnostics
- add a graphical dashboard for runtime status and configuration

## 16. Conclusion

Ivan successfully demonstrates how embedded systems, robotics, and modern AI services can be combined into a practical interactive platform. The final system can listen, speak, see, read text, remember simple information, and move with physical expression. It supports multiple operating modes and continues to function in reduced form even when some hardware features are unavailable.

From an engineering perspective, the most important achievement of the project is not any single feature, but the successful coordination of many subsystems into one coherent runtime. The design shows strong attention to modularity, fault tolerance, human interaction, and real-time control. For an Advanced Embedded Systems project, Ivan represents a complete and technically meaningful implementation that combines software architecture, hardware interfacing, and intelligent behavior in a single robotic application.

## 17. References

1. Google Gemini API documentation
2. Python 3 documentation
3. OpenCV documentation
4. MediaPipe documentation
5. Tesseract OCR documentation
6. PyAudio documentation
7. Pololu Maestro servo controller documentation
8. Raspberry Pi and Picamera2 documentation
