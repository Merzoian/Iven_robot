# Ivan Video Presentation Script

## Video Goal

Present the Ivan project clearly in a short final-project video by showing the robot, explaining the system, and demonstrating the main features.

Recommended video length: 5 to 8 minutes

## Video Structure

1. Introduction
2. Project goal
3. Hardware and software overview
4. Code architecture
5. Live demo
6. Challenges and solutions
7. Testing
8. Conclusion

## Word-for-Word Script

Hello, my name is Valentina, and this is my final project for Advanced Embedded Systems.

My project is called Ivan. Ivan is a conversational robotic head that combines live AI audio, camera awareness, OCR, tracking, servo motion, and short-term memory into one embedded system.

The goal of this project was to build a robot that can do more than just move or play pre-recorded audio. I wanted to create a system that could listen to a user, respond naturally, observe its environment with a camera, read visible text, remember simple facts, and physically move its head and eyes using servos.

This project is an embedded systems project because it combines sensing, processing, communication, and actuation. Ivan uses a microphone for audio input, a speaker for audio output, a camera for visual input, and a Pololu Maestro servo controller to drive the robot’s movement.

You can see here the main hardware and software components of the project. The system runs in Python and is organized into separate modules for audio, camera, motion, commands, OCR, memory, and session handling. The main program starts in `main4_robot.py`, which launches the runtime system.

The robot also connects to Gemini live audio, which allows it to process speech and respond conversationally. In addition to that, I implemented local fallback commands so that important functions like movement, tracking, and OCR can still respond quickly and reliably.

Now I’m going to demonstrate the main features of the system.

First is command mode. In command mode, I can directly tell Ivan how to move.

At this point, demonstrate commands such as:

- look left
- look right
- center
- tilt left
- tilt right

While showing it, say:

In this mode, the robot responds to direct movement commands. This is useful for manual interaction and testing.

Next is tracking mode. In tracking mode, Ivan can automatically follow a detected face or person.

At this point, demonstrate the tracking behavior.

While showing it, say:

This feature uses the camera system along with detection and tracking logic to keep the robot oriented toward a target.

Another mode is intro mode. Intro mode is a quiet, nonverbal mode. In this mode, spoken output is suppressed, but the robot can still use movement and simple gestures.

At this point, show intro mode behavior.

While showing it, say:

This mode is useful for demonstrations where I want the robot to stay expressive without speaking.

Next, I will demonstrate OCR. OCR stands for optical character recognition. I added this so Ivan can read visible text, handwriting, numbers, and simple equations.

At this point, hold up paper or a screen and trigger the OCR feature.

While showing it, say:

This feature uses local Tesseract OCR. It allows the robot to read information from a worksheet, paper, whiteboard, or screen.

Another feature I added is short session memory. Ivan can remember simple facts such as a name, likes, or favorites.

At this point, demonstrate a short memory example such as:

- My name is Valentina.
- What is my name?

While showing it, say:

This memory system is simple, but it helps the robot create a more personalized interaction.

One of the most important parts of this project was the software design. The program is modular, which means different responsibilities are separated into different files. For example, there are separate modules for motion control, audio streaming, camera processing, OCR, memory, and command handling. This made the project easier to test and maintain.

One of the biggest challenges in this project was coordinating real-time audio, camera input, AI responses, and servo movement. These systems all operate at different speeds, and if they are not synchronized carefully, the robot can behave unpredictably.

To solve this, I used a modular runtime design, local fallback commands, transcript deduplication, and behavior suppression windows after manual commands. I also made the system degrade gracefully if some hardware, such as the camera or servo controller, is unavailable.

I also included automated tests for key parts of the project, including commands, memory, motion, OCR, runtime loading, and session handling. This helped verify that the software behaves correctly beyond just live demonstration.

In conclusion, Ivan successfully combines embedded hardware control with conversational AI. The robot can listen, speak, see, read text, remember simple facts, and move physically. This project demonstrates how embedded systems can integrate modern AI with real-time robotics.

In the future, I would like to improve long-term memory, tracking accuracy, OCR reliability, gesture quality, and the overall hardware packaging.

Thank you for watching my final project presentation.

## Demo Checklist

- Show yourself and the robot
- Show the hardware setup
- Show the repository briefly
- Demo command mode
- Demo tracking mode
- Demo intro mode
- Demo OCR
- Demo memory
- Mention testing
- End with conclusion and future work

## Recording Tips

- Speak slowly and clearly
- Pause during demos so the robot has time to respond
- Keep code walkthroughs short
- Focus more on showing the system working than on reading technical details
- Keep the final video around 5 to 8 minutes
