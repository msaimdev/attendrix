import numpy as np

from app.face_engine import FaceEngine
from app.student import StudentManager


class CameraManager:
    """
    Handles face detection and face recognition.

    This class does NOT mark attendance.
    Attendance is handled by AttendanceSession.
    """

    RECOGNITION_THRESHOLD = 0.600

    def __init__(self):
        self.face_engine = FaceEngine()
        self.student_manager = StudentManager()

        self.recognition_threshold = (
            self.RECOGNITION_THRESHOLD
        )

    def recognize_face(self, frame):
        """
        Detect and recognize faces in a camera frame.

        Returns:
            List of recognized students.

        Attendance is NOT marked here.
        """

        faces = self.face_engine.detect_faces(frame)

        if len(faces) == 0:
            return []

        students = self.student_manager.get_all_students()

        results = []

        for face in faces:
            feature = self.face_engine.extract_feature(
                frame,
                face,
            )

            best_student = None
            best_score = -1.0

            for student in students:
                for stored_feature in student.get(
                    "features",
                    [],
                ):
                    stored_feature = np.asarray(
                        stored_feature,
                        dtype=np.float32,
                    ).reshape(1, -1)

                    score = self.face_engine.compare(
                        feature,
                        stored_feature,
                    )

                    if score > best_score:
                        best_score = score
                        best_student = student

            if best_student is not None:
                print(
                    f"Best match: {best_student['name']} "
                    f"| Score: {best_score:.3f} "
                    f"| Accepted: "
                    f"{best_score >= self.recognition_threshold}"
                )

            if (
                best_student is not None
                and best_score >= self.recognition_threshold
            ):
                results.append(
                    {
                        "student_id": best_student[
                            "student_id"
                        ],
                        "name": best_student["name"],
                        "class": best_student["class"],
                        "score": float(best_score),
                        "face": face,
                    }
                )

        return results