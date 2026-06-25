class Student:
    # Class attributes (shared by all students)
    school_name = "Greenwood High School"
    total_students = 0

    def __init__(self, name, grade):
        # Instance attributes (unique to each student)
        self.name = name
        self.grade = grade

        # Update class attribute
        Student.total_students += 1

    def display_info(self):
        print(f"Name: {self.name}")
        print(f"Grade: {self.grade}")
        print(f"School: {Student.school_name}")
        print("-" * 30)


# Create students
student1 = Student("Joshua", "A")
student2 = Student("Mary", "B")
student3 = Student("John", "A+")

# Display information
student1.display_info()
student2.display_info()
student3.display_info()

# Access class attributes
print("School Name:", Student.school_name)
print("Total Students:", Student.total_students)