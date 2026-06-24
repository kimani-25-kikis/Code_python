class Dog():
    def __init__(self, name, age):
        self.name =name
        self.age = age
    def barks(self):
        # print(f'{self.name.upper()} {self.age}')
        print(f'{self.name.upper()} {self.age}')
dog_1= Dog("Jack", 12)
dog_2= Dog("poppy", 10)
dog_1.barks()
dog_2.barks()