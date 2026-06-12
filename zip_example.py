students = ["Alice", "Bob", "Charlie", "Diana"]
math_scores = [85, 92, 78, 95]
science_scores = [88, 90, 82, 97]

print("STUDENT PERFORMANCE REPORT")
print("-" * 40)

for rank, (student, math, science) in enumerate(
    zip(students, math_scores, science_scores),
    start=1
):
    average = (math + science) / 2

    if average >= 90:
        grade = "A"
    elif average >= 80:
        grade = "B"
    else:
        grade = "C"

    print(
        f"{rank}. {student:<10} "
        f"Math: {math}  Science: {science}  "
        f"Average: {average:.1f}  Grade: {grade}"
    )