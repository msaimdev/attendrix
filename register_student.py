import cv2
import time

from app.face_engine import FaceEngine
from app.student import StudentManager


engine = FaceEngine()
student_manager = StudentManager()


print("========================================")
print("        STUDENT REGISTRATION")
print("========================================")
print()

name = input("Student name: ").strip()
student_class = input("Class: ").strip()

if not name:
    print("ERROR: Student name cannot be empty.")
    exit()

if not student_class:
    print("ERROR: Class cannot be empty.")
    exit()




print()
print("Registration information:")
print(f"Name       : {name}")
print(f"Class      : {student_class}")
print()

input("Press ENTER to open the camera...")


camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera.")
    exit()


features = []

last_capture_time = 0
capture_interval = 0.5

target_samples = 10


print()
print("========================================")
print("Look directly at the camera.")
print("Move your head slightly between samples.")
print(f"Capturing {target_samples} face samples...")
print("Press Q to cancel.")
print("========================================")
print()


while len(features) < target_samples:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera frame.")
        break

    faces = engine.detect_faces(frame)

    if len(faces) > 0:

        # Use the largest detected face.
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
            current_time - last_capture_time
            >= capture_interval
        ):

            feature = engine.extract_feature(
                frame,
                face,
            )

            features.append(feature)

            last_capture_time = current_time

            print(
                f"Captured sample "
                f"{len(features)}/{target_samples}"
            )

        cv2.putText(
            frame,
            f"Samples: {len(features)}/{target_samples}",
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

    cv2.imshow(
        "Student Registration",
        frame,
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        print("Registration cancelled.")
        camera.release()
        cv2.destroyAllWindows()
        exit()


camera.release()
cv2.destroyAllWindows()


if len(features) < target_samples:
    print("Registration failed.")
    exit()


student = student_manager.save_student(
    name=name,
    student_class=student_class,
    features=features,
)

print()
print("========================================")
print("       REGISTRATION SUCCESSFUL")
print("========================================")
print()
print(f"Student ID : {student['student_id']}")
print(f"Name       : {student['name']}")
print(f"Class      : {student['class']}")
print(f"Face samples: {len(features)}")
print()
print(
    f"Saved to: data/students/{student['student_id']}.json"
)