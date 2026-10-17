import threading

import cv2


class ThreadedVideoCapture:
    """
    Drop-in replacement for cv2.VideoCapture that fixes the
    "slow motion" / growing-lag symptom seen with RTSP sources.

    THE PROBLEM THIS SOLVES
    ------------------------
    cv2.VideoCapture (via its FFmpeg backend) keeps an internal
    buffer of decoded frames. If your processing loop calls
    .read() slower than the camera is producing frames -- which
    is exactly what happens once face detection/recognition work
    is done per frame -- .read() keeps handing back the OLDEST
    buffered frame instead of the newest one. The backlog grows
    every time processing takes longer than one frame interval,
    so the video appears to run in slow motion and never catches
    back up.

    THE FIX
    -------
    A dedicated background thread does nothing but call
    .read() on the real VideoCapture as fast as possible and
    stash only the single most recent frame. Your existing code
    calls .read() on this wrapper exactly like before, but it
    always gets the latest available frame instead of the oldest
    queued one. Some frames get skipped entirely when processing
    is slow -- which is the correct trade-off for a live
    attendance/registration camera feed (you want "now", not
    "eventually, in order").

    Public interface (isOpened / read / release) mirrors
    cv2.VideoCapture on purpose, so it can replace
    `cv2.VideoCapture(camera_index)` with no other code changes.
    """

    # How long to wait for the very first frame during startup
    # before giving up on the "warm start" and letting isOpened()
    # / read() report the real state as it develops.
    _STARTUP_TIMEOUT_SECONDS = 5.0

    def __init__(self, source):
        if isinstance(source, str):
            # Explicit FFmpeg backend for network stream URLs
            # (RTSP etc). Local integer camera indexes should
            # keep using the platform default backend, so we
            # only force this for string sources.
            self._capture = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        else:
            self._capture = cv2.VideoCapture(source)

        # Ask the backend to keep as little internal buffer as
        # possible. Not all backends honor this (FFmpeg's RTSP
        # support often ignores it) -- that's exactly why the
        # draining thread below is the real fix, not this line.
        try:
            self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self._lock = threading.Lock()
        self._latest_frame = None
        self._latest_success = False
        self._stopped = False
        self._first_frame_event = threading.Event()

        self._thread = None

        if self._capture.isOpened():
            self._thread = threading.Thread(
                target=self._update,
                daemon=True,
            )
            self._thread.start()

            # Give the stream a short window to deliver its
            # first frame so that a caller doing
            # `open camera -> immediately read()` doesn't get a
            # spurious failure before the thread has had a
            # chance to run.
            self._first_frame_event.wait(
                self._STARTUP_TIMEOUT_SECONDS
            )

    def _update(self):
        while not self._stopped:
            success, frame = self._capture.read()

            with self._lock:
                self._latest_success = success
                self._latest_frame = frame

            if not success:
                # Stream dropped (unplugged, network loss, wrong
                # URL, etc). Stop hammering it in a tight loop;
                # read() will keep reporting failure to the
                # caller, which already treats that as
                # "camera stopped responding".
                self._first_frame_event.set()
                break

            self._first_frame_event.set()

    def isOpened(self):
        return self._capture.isOpened()

    def read(self):
        with self._lock:
            if self._latest_frame is None:
                return False, None

            # .copy() so the caller can freely draw on the frame
            # (rectangles, text overlays) without racing the
            # background thread that may overwrite
            # self._latest_frame at any moment.
            return self._latest_success, self._latest_frame.copy()

    def release(self):
        self._stopped = True

        if self._thread is not None:
            self._thread.join(timeout=2)

        self._capture.release()