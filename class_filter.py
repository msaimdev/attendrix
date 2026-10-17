from app.student import StudentManager


def main():
    student_manager = StudentManager()

    students = student_manager.get_all_students()

    print()
    print("=" * 40)
    print("            CLASS FILTER")
    print("=" * 40)
    print()

    if not students:
        print("No students are registered.")
        print()
        return

    classes = sorted(
        {
            student["class"]
            for student in students
        }
    )

    print("Available Classes:")
    print()
    print("0. All Classes")

    for index, student_class in enumerate(classes, start=1):
        print(f"{index}. {student_class}")

    print()

    while True:
        choice = input("Select class: ").strip()

        if not choice.isdigit():
            print("Please enter a valid number.")
            continue

        choice = int(choice)

        if 0 <= choice <= len(classes):
            break

        print("Invalid class selection.")

    if choice == 0:
        filtered_students = students
        selected_class = "All Classes"
    else:
        selected_class = classes[choice - 1]

        filtered_students = [
            student
            for student in students
            if student["class"] == selected_class
        ]

    print()
    print("-" * 40)
    print(f"Students in {selected_class}")
    print("-" * 40)
    print()

    print(f"{'Name':<20}{'Class':<10}")
    print("-" * 40)

    for student in filtered_students:
        print(
            f"{student['name']:<20}"
            f"{student['class']:<10}"
        )

    print("-" * 40)
    print(f"Total: {len(filtered_students)}")
    print()


if __name__ == "__main__":
    main()