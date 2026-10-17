
from app.student import StudentManager


def main():
    student_manager = StudentManager()

    students = student_manager.get_all_students()

    print("========================================")
    print("        REGISTERED STUDENTS")
    print("========================================")
    print()

    if not students:
        print("No students are registered.")
    else:
        print(f"Total students: {len(students)}")
        print()

        for index, student in enumerate(students, start=1):
            print(f"Student #{index}")
            print(f"Name      : {student['name']}")
            print(f"Class     : {student['class']}")
            print(f"Student ID: {student['student_id']}")
            print("----------------------------------------")

    print()
    print("========================================")


if __name__ == "__main__":
    main()
