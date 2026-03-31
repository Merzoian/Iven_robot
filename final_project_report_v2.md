# Final Project Report V2

## Project Title

Ivan: A Conversational Robotic Head with Live AI, Vision, OCR, and Servo Control

## Student Information

- Student: Valentina
- Program: Computer Engineering
- Institution: Brigham Young University-Idaho
- Course: Advanced Embedded Systems
- Date: March 30, 2026

## Abstract

Ivan is a conversational robotic head developed for an Advanced Embedded Systems project. The system combines live voice interaction, camera awareness, servo-based motion, optical character recognition, and short session memory into a single embedded runtime. It uses Google Gemini for live audio interaction while also supporting deterministic local commands for movement, mode switching, and OCR. The project demonstrates how embedded hardware and AI services can be integrated into a responsive multimodal robotic platform.

## 1. Introduction

The purpose of this project was to build a robotic head that can interact with users in a more natural and intelligent way. Ivan can listen through a microphone, respond with speech, observe through a camera, read visible text, remember simple facts, and move its eyes, jaw, and head using servos. This project represents an embedded systems application that combines sensing, computation, communication, and actuation.

## 2. Objectives

- Build a conversational robotic head
- Integrate live audio and camera context using Gemini
- Control servos for expression and movement
- Support command, tracking, and intro modes
- Add OCR for reading text and simple equations
- Add short session memory
- Validate core functions with automated tests

## 3. System Overview

Ivan runs through `main4_robot.py`, which starts the main runtime in `robot_app.py`. The system loads configuration, initializes available hardware, opens audio and camera streams, connects to Gemini live audio, and handles transcripts, tool calls, OCR, motion control, and memory updates.

The project is organized into separate modules for motion, camera, audio, commands, OCR, memory, session handling, and runtime state. This modular structure improves maintainability and testing.

## 4. Main Features

### 4.1 Conversational Interaction

Ivan uses Gemini live audio to process user speech and generate spoken responses. It also supports tool calls so the model can trigger robot actions such as mode changes, movement, and OCR.

### 4.2 Servo Motion

The robot controls eyes, jaw, head yaw, head pitch, and head tilt through a Pololu Maestro servo controller. This allows the system to physically respond during interaction.

### 4.3 Camera and Tracking

The camera system supports visual awareness and tracking. It uses face detection, person detection fallback, target smoothing, and paced image uploads for model context.

### 4.4 OCR

Ivan can read visible text, handwriting, numbers, and simple equations using local Tesseract OCR. This allows the robot to respond to commands such as reading paper, worksheets, or screens.

### 4.5 Session Memory

The memory subsystem stores simple user facts such as names, likes, and favorites. This information is saved between sessions in a JSON file.

### 4.6 Local Voice Command Fallback

Important controls such as movement, tracking, mode switching, and OCR can also be handled locally. This improves reliability and responsiveness when immediate deterministic behavior is needed.

## 5. Operating Modes

Ivan supports three modes:

- `command` mode for direct movement commands
- `tracking` mode for automatic following behavior
- `intro` mode for quiet, nonverbal interaction

These modes allow the robot to adapt its behavior to different situations.

## 6. Testing

The `tests/` directory includes automated tests for commands, memory, motion, OCR, runtime loading, and session handling. This helped verify that the main software components behave correctly.

## 7. Challenges

The main engineering challenges included coordinating real-time audio, camera input, model responses, and servo motion; preventing repeated triggers from streaming transcripts; and keeping behavior stable when hardware such as the camera or servo controller was unavailable. These issues were addressed through modular design, transcript deduplication, local fallback control, and graceful degradation.

## 8. Results

The final system successfully demonstrated:

- live conversational audio
- servo-based robot motion
- camera-aware interaction
- face/person tracking
- local OCR
- short-term memory
- multiple operating modes
- automated test coverage

The project met its core goal of combining embedded hardware control with AI-assisted multimodal interaction.

## 9. Conclusion

Ivan is a successful embedded robotics project that integrates voice, vision, motion, OCR, and memory into one system. It demonstrates practical embedded systems engineering by coordinating multiple hardware and software subsystems in real time. The project shows how conversational AI can be combined with physical robotics to create a more interactive and capable platform.

## 10. Future Work

Future improvements could include better long-term memory, improved OCR accuracy, stronger tracking, richer gestures, a pinned dependency file, and improved hardware packaging.

## 11. References

1. Google Gemini API documentation
2. Python 3 documentation
3. OpenCV documentation
4. MediaPipe documentation
5. Tesseract OCR documentation
6. PyAudio documentation
7. Pololu Maestro documentation
8. Picamera2 documentation
