import threading
import time

import cv2

from app.face_engine import FaceEngine
from app.student import StudentManager
from app.camera_stream import ThreadedVideoCapture

class RegistrationSession:
    """
    Manages a single, server-side camera session used to
    capture face samples for a new student registration
    through the web UI.

    The camera used is the same local camera the rest of the
    application uses (index configurable, default 0). Only one
    registration session is active at a time, which is fine
    for a single-admin local tool.

    Usage from the web layer:
        1. start()               -> opens the camera
        2. get_jpeg_frame() loop -> streamed to the browser as MJPEG,
                                     also opportunistically captures
                                     feature samples as a side effect
        3. status()               -> polled by the browser for progress
        4. save(name, class)      -> finalizes registration
           OR
           cancel()               -> aborts without saving
    """

    TARGET_SAMPLES = 10
    CAPTURE_INTERVAL_SECONDS = 0.5

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index

        self.face_engine = FaceEngine()
        self.student_manager = StudentManager()

        self.lock = threading.Lock()

        self.camera = None
        self.features = []
        self.last_capture_time = 0.0
        self.active = False

    # ============================================================
    # START
    # ============================================================

    def start(self):
        with self.lock:
            if self.active:
                raise RuntimeError(
                    "A registration session is already active. "
                    "Cancel it before starting a new one."
                )

            camera = ThreadedVideoCapture(self.camera_index)

            if not camera.isOpened():
                camera.release()
                raise RuntimeError(
                    "Could not open the camera. Make sure no other "
                    "process (e.g. an active attendance session) is "
                    "currently using it."
                )

            self.camera = camera
            self.features = []
            self.last_capture_time = 0.0
            self.active = True

    # ============================================================
    # FRAME (used by the MJPEG stream; also drives capture)
    # ============================================================

    def get_jpeg_frame(self):
        """
        Read one frame, run face detection, opportunistically
        capture a feature sample, draw an overlay showing capture
        progress, and return JPEG-encoded bytes for streaming.

        Returns None if the session isn't active or the camera
        can't produce a frame (the MJPEG generator should stop).
        """

        with self.lock:
            if not self.active or self.camera is None:
                return None

            success, frame = self.camera.read()

            if not success:
                # Camera stopped responding (unplugged, busy
                # with another process, driver error, etc).
                # Release it and mark the session inactive so
                # the frontend can detect this via status()
                # instead of silently hanging forever.
                self._release()
                return None

            faces = self.face_engine.detect_faces(frame)

            if len(faces) > 0:
                face = max(
                    faces,
                    key=lambda f: f[2] * f[3],
                )

                x, y, w, h = face[:4].astype(int)

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2,
                )

                current_time = time.time()

                if (
                    len(self.features) < self.TARGET_SAMPLES
                    and current_time - self.last_capture_time
                    >= self.CAPTURE_INTERVAL_SECONDS
                ):
                    feature = self.face_engine.extract_feature(
                        frame,
                        face,
                    )
                    self.features.append(feature)
                    self.last_capture_time = current_time

                cv2.putText(
                    frame,
                    f"Samples: {len(self.features)}/{self.TARGET_SAMPLES}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                )
            else:
                cv2.putText(
                    frame,
                    "No face detected",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )

            success, buffer = cv2.imencode(".jpg", frame)

            if not success:
                return None

            return buffer.tobytes()

    # ============================================================
    # STATUS
    # ============================================================

    def status(self):
        with self.lock:
            return {
                "active": self.active,
                "samples_captured": len(self.features),
                "target_samples": self.TARGET_SAMPLES,
                "ready": (
                    len(self.features) >= self.TARGET_SAMPLES
                ),
            }

    # ============================================================
    # SAVE
    # ============================================================

    def save(self, name: str, student_class: str):
        with self.lock:
            if not self.active:
                raise RuntimeError(
                    "No active registration session."
                )

            if len(self.features) < self.TARGET_SAMPLES:
                raise RuntimeError(
                    f"Not enough face samples captured "
                    f"({len(self.features)}/{self.TARGET_SAMPLES}). "
                    f"Keep the face visible in frame and try again."
                )

            student = self.student_manager.save_student(
                name=name,
                student_class=student_class,
                features=self.features,
            )

            self._release()

            return student

    # ============================================================
    # CANCEL
    # ============================================================

    def cancel(self):
        with self.lock:
            self._release()

    # ============================================================
    # INTERNAL
    # ============================================================

    def _release(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None

        self.features = []
        self.active = False