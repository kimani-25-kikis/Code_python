students = {
    "Alice": {
        "Math": 85,
        "Science": 90,
        "English": 88
    },
    "Bob": {
        "Math": 78,
        "Science": 82,
        "English": 80
    },
    "Charlie": {
        "Math": 92,
        "Science": 95,
        "English": 91
    }
}

print("STUDENT REPORT")
print("-" * 40)

for student, grades in students.items():

    print(f"\nStudent: {student}")

    total = 0

    for subject, score in grades.items():
        print(f"{subject}: {score}")
        total += score

    average = total / len(grades)

    print(f"Average: {average:.2f}")

    if average >= 90:
        print("Grade: A")
    elif average >= 80:
        print("Grade: B")
    else:
        print("Grade: C")