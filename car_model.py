
class Car():
    engine = 'Petrol Engine'
    windscreen = 'Tinted'
    
    def __init__(self, name, year, color):
        self.name = name
        self.year = year
        self.color = color
    def model(self):
        print(f'Vehicle:{self.name} was made in: {self.year} and is:{self.color} in color')
car_1 = Car('Toyota', 2016, 'Red')
car_2 = Car('Mazda', 2019,'Blue')
car_3 = Car('Mercedez', 2025,'White')

# print(car_1.model())
# print(car_1.engine)
car_1.model()