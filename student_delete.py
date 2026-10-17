
from app.student import StudentManager


def main():
    student_manager = StudentManager()

    print("========================================")
    print("         DELETE STUDENT")
    print("========================================")
    print()

    student_id = input("Enter Student ID: ").strip()

    if not student_id:
        print("ERROR: Student ID cannot be empty.")
        return

    student = student_manager.load_student(student_id)

    if student is None:
        print(f"ERROR: Student '{student_id}' was not found.")
        return

    print()
    print("Student found:")
    print(f"Name      : {student['name']}")
    print(f"Class     : {student['class']}")
    print(f"Student ID: {student['student_id']}")
    print()

    confirmation = input(
        "Are you sure you want to delete this student? (yes/no): "
    ).strip().lower()

    if confirmation != "yes":
        print()
        print("Deletion cancelled.")
        return

    deleted = student_manager.delete_student(student_id)

    if not deleted:
        print()
        print("ERROR: Student could not be deleted.")
        return

    print()
    print("========================================")
    print("       STUDENT DELETED")
    print("========================================")
    print()
    print(f"Name : {student['name']}")
    print(f"Class: {student['class']}")
    print()


if __name__ == "__main__":
    main()
