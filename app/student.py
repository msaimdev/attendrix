import uuid

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Student


class StudentManager:
    """
    SQLite-backed student manager.

    The public interface intentionally remains compatible
    with the original JSON-based MVP StudentManager.
    """

    # ============================================================
    # ID
    # ============================================================

    def generate_student_id(self):
        """
        Generate a unique internal student ID.
        """
        return str(uuid.uuid4())

    # ============================================================
    # SAVE STUDENT
    # ============================================================

    def save_student(
        self,
        name,
        student_class,
        features,
        student_id=None,
    ):
        """
        Save a student to SQLite.

        If no student_id is provided, generate one automatically.

        Returns a dictionary compatible with the original
        JSON-based StudentManager interface.
        """

        if student_id is None:
            student_id = self.generate_student_id()

        db = SessionLocal()

        try:
            existing = db.scalar(
                select(Student).where(
                    Student.id == student_id
                )
            )

            if existing is not None:
                raise ValueError(
                    f"Student '{student_id}' already exists."
                )

            face_features = [
                feature.flatten().tolist()
                for feature in features
            ]

            student = Student(
                id=student_id,
                name=name,
                student_class=student_class,
                face_features=face_features,
                is_active=True,
            )

            db.add(student)
            db.commit()
            db.refresh(student)

            return {
                "student_id": student.id,
                "name": student.name,
                "class": student.student_class,
                "features": student.face_features,
            }

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    # ============================================================
    # LOAD STUDENT
    # ============================================================

    def load_student(self, student_id):
        """
        Load one active student from SQLite.

        Returns None if the student does not exist or is inactive.

        The returned dictionary keeps the original format.
        """

        db = SessionLocal()

        try:
            student = db.scalar(
                select(Student).where(
                    Student.id == student_id,
                    Student.is_active.is_(True),
                )
            )

            if student is None:
                return None

            return {
                "student_id": student.id,
                "name": student.name,
                "class": student.student_class,
                "features": student.face_features,
            }

        finally:
            db.close()

    # ============================================================
    # GET ALL ACTIVE STUDENTS
    # ============================================================

    def get_all_students(self):
        """
        Load all active students from SQLite.

        Returns dictionaries compatible with the original
        JSON-based StudentManager interface.
        """

        db = SessionLocal()

        try:
            students = db.scalars(
                select(Student)
                .where(
                    Student.is_active.is_(True)
                )
                .order_by(Student.name)
            ).all()

            return [
                {
                    "student_id": student.id,
                    "name": student.name,
                    "class": student.student_class,
                    "features": student.face_features,
                }
                for student in students
            ]

        finally:
            db.close()

    # ============================================================
    # DELETE / DEACTIVATE STUDENT
    # ============================================================

    def delete_student(self, student_id):
        """
        Deactivate a student in SQLite.

        The database row is intentionally preserved so historical
        attendance records remain available.

        Returns:
            True  -> student was found and deactivated
            False -> student was not found
        """

        db = SessionLocal()

        try:
            student = db.scalar(
                select(Student).where(
                    Student.id == student_id,
                    Student.is_active.is_(True),
                )
            )

            if student is None:
                return False

            student.is_active = False

            db.commit()

            return True

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()