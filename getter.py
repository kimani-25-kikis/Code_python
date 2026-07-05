class Circle:
    def __init__(self, radius):
        self._radius = radius
    @property
    def radius(self):
        return self._radius
    @property
    def area(self):
        return 3.14 * (self._radius ** 2)
my_circle = Circle(3)
print(my_circle.radius)
print(my_circle.area)