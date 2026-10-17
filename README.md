# Face Attendance System

A local, camera-based school attendance system built with Python, FastAPI, OpenCV, SQLAlchemy, Alembic, and SQLite.

This repository is a public portfolio presentation of the project. It is not a ready-to-deploy school installation package.

## Project Overview

The system is designed for a single Windows school computer connected to one entrance camera. It is not a LAN-based, multi-computer attendance system.

Core design goals include:

- Face-based student attendance using YuNet face detection and SFace feature extraction.
- Student registration with face samples.
- Attendance records and history stored locally.
- School calendar and attendance-session rules.
- Student leave handling and attendance reporting.
- Local operation without requiring continuous internet access.
- Optional daily attendance email when internet access is available.

Actual behavior depends on the application's configuration and deployment environment.

## Architecture

- **Application:** Python and FastAPI
- **Database:** SQLite
- **Database migrations:** Alembic
- **ORM:** SQLAlchemy
- **Face processing:** OpenCV, YuNet, and SFace
- **Web interface:** HTML templates and static assets
- **Camera:** One camera connected to the school PC
- **Operating environment:** Windows

The application is intended to run locally on the school computer. It is not designed as a multi-PC LAN service.

## Face Recognition Models

The application currently expects these model files:

- `models/yunet/face_detection_yunet_2026may.onnx`
- `models/sface/face_recognition_sface_2021dec.onnx`

The model binaries are intentionally not included in this repository. Obtain them from their authoritative upstream sources and review their applicable licenses and notices before use.

Upstream project: https://github.com/opencv/opencv_zoo

The application will not initialize its face-processing engine until the required files are present at the expected paths.

## Setup Overview

This repository is a development/portfolio copy, not the original school deployment package.

1. Install a compatible Python version for the pinned dependencies.
2. Create and activate a virtual environment.
3. Install the dependencies listed in `requirements.txt`.
4. Obtain the required model files from approved sources and place them at the paths listed above.
5. Review the application's configuration requirements before running it.
6. Initialize the local database using the project's intended migration/setup process.
7. Configure and test the camera locally before any school use.

Detailed, verified setup instructions still need to be completed. Do not assume that a fresh clone is immediately ready for production.

## Privacy and Security

Face images, face embeddings, student records, and attendance histories are sensitive information.

- Keep real student data and production databases out of source control.
- Never commit `.env` files, camera credentials, passwords, or private keys.
- Restrict access to the school computer and its local records.
- Obtain the appropriate permissions and follow applicable privacy and data-protection requirements before collecting or processing student biometric data.
- Test camera behavior, attendance accuracy, and recovery procedures before relying on the system in a school.

## Current Scope

This project targets a single-PC school installation with one entrance camera. Internet connectivity is optional for normal local attendance processing; email functionality requires internet access.

This repository does not claim that the software is suitable for every camera, computer, school policy, or deployment environment.

## License and Reuse

See `LICENSE` for the terms governing this project's original code.

Third-party dependencies, model files, and other external components remain subject to their own licenses and terms.
