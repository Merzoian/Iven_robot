# Ivan Final Project Report

## Title Page

**Project Title:** Ivan: A Conversational Robotic Head with Live AI, Vision, OCR, and Servo Control  
**Student:** Valentina  
**Program:** Computer Engineering  
**Institution:** Brigham Young University-Idaho  
**Course:** Advanced Embedded Systems  
**Date:** March 30, 2026

---

## Table of Contents

1. Abstract
2. Introduction
3. Objectives
4. System Overview
5. Architecture
6. Main Features
7. Testing and Results
8. Challenges
9. Conclusion
10. Future Work
11. References
12. Diagrams

---

## 1. Abstract

Ivan is a conversational robotic head designed as an embedded systems project. The system combines live voice interaction, camera awareness, servo motion, OCR, and session memory in a single runtime. It uses Gemini for live audio interaction and local command logic for fast deterministic control. The project demonstrates how embedded hardware and AI services can be integrated into a responsive robotic platform.

## 2. Introduction

The goal of this project was to build an interactive robotic head that could communicate through speech, observe through a camera, move using servos, and respond intelligently to user input. Ivan was designed to combine embedded control with real-time AI-assisted interaction. This makes the project a strong example of applied embedded systems design.

## 3. Objectives

- Build a conversational robotic head
- Integrate voice, vision, and motion
- Support multiple behavioral modes
- Add OCR for reading visible text
- Add simple memory for user facts
- Maintain responsiveness with local fallback commands

## 4. System Overview

Ivan starts from `main4_robot.py`, which launches the main runtime in `robot_app.py`. The software loads configuration, starts hardware interfaces, opens audio and camera streams, connects to Gemini live audio, and manages movement, OCR, memory, and tool execution.

The runtime combines:

- microphone input
- speaker output
- camera frames
- Gemini live model interaction
- servo control
- local OCR
- local command fallback

## 5. Architecture

The system is organized into separate modules:

- `robot_app.py` for startup, runtime flow, reconnects, and shutdown
- `robot_audio.py` for microphone and speaker streaming
- `robot_camera.py` for capture, detection, and frame preparation
- `robot_motion.py` for servo movement, tracking math, and gestures
- `robot_commands.py` for command parsing and tool execution
- `robot_ocr.py` for visible text recognition
- `robot_memory.py` for session memory
- `robot_session.py` for transcript, audio, and tool-call handling

This modular architecture improves maintainability, testing, and fault tolerance.

## 6. Main Features

### Live Conversation

Ivan uses Gemini live audio for speech-based interaction and spoken responses.

### Motion Control

The robot controls eyes, jaw, head yaw, head pitch, and tilt using servos through a Maestro controller.

### Vision and Tracking

The camera system supports face detection, person fallback detection, target smoothing, and tracking behavior.

### OCR

The robot can read visible text, handwriting, numbers, and simple equations using Tesseract OCR.

### Memory

Ivan stores simple session facts such as names, likes, and favorites.

### Operating Modes

Ivan supports:

- `command` mode
- `tracking` mode
- `intro` mode

## 7. Testing and Results

The project includes automated tests for commands, memory, motion, OCR, runtime configuration, and session handling. The final system successfully demonstrated:

- live conversational speech
- synchronized servo-based motion
- camera-aware interaction
- tracking behavior
- local OCR
- session memory
- reliable local fallback commands

## 8. Challenges

Key challenges in the project included:

- coordinating real-time audio, camera, and motion
- preventing repeated actions from streaming transcripts
- managing conflicts between local commands and model actions
- handling missing hardware gracefully

These were addressed through modular design, transcript deduplication, suppression timing, and graceful degradation.

## 9. Conclusion

Ivan successfully integrates embedded hardware control with AI-assisted interaction. The project shows that voice, vision, OCR, memory, and physical motion can be combined into a single working robotic platform. It meets the main goals of the project and demonstrates meaningful embedded systems engineering.

## 10. Future Work

- Improve long-term memory
- Improve tracking accuracy
- Improve OCR robustness
- Add richer gestures and expressions
- Add a pinned dependency file
- Improve hardware packaging and reliability

## 11. References

1. Google Gemini API documentation
2. Python 3 documentation
3. OpenCV documentation
4. MediaPipe documentation
5. Tesseract OCR documentation
6. PyAudio documentation
7. Pololu Maestro documentation
8. Picamera2 documentation

## 12. Diagrams

### Diagram 1: High-Level System Flow

You can replace this section with a rendered figure in Word or Google Docs.

```text
User Speech + Camera Input
          |
          v
   Ivan Runtime System
          |
  -------------------------
  | Audio | Vision | OCR |
  | Memory | Commands    |
  -------------------------
          |
          v
 Gemini Live Session + Local Control
          |
          v
 Speech Output + Servo Movement
```

### Diagram 2: Software Module Layout

```text
main4_robot.py
      |
      v
robot_app.py
  |    |     |      |       |       |
  v    v     v      v       v       v
audio camera motion commands memory session
                    |
                    v
                 OCR/tools
```

### Diagram 3: Operating Modes

```text
            +----------------+
            |  Command Mode  |
            | Manual control |
            +----------------+
                    |
                    v
            +----------------+
            | Tracking Mode  |
            | Auto follow    |
            +----------------+
                    |
                    v
            +----------------+
            |   Intro Mode   |
            | Quiet/nonverbal|
            +----------------+
```
