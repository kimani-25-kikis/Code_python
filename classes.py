# class Dog():
#     def __init__(self, name, age):
#         self.name =name
#         self.age = age
#     def barks(self):
#         # print(f'{self.name.upper()} {self.age}')
#         print(f'{self.name.upper()} {self.age}')
# dog_1= Dog("Jack", 12)
# dog_2= Dog("poppy", 10)
# dog_1.barks()
# dog_2.barks()

# class Dog:  
#     def __init__(self, name):  
#         self.name = name

#     def bark(self):  
#         print(f"{self.name} says Woof!")  

# my_dog = Dog("Rex")
# # print(my_dog.bark())
# my_dog.bark()

class Dog():
    species = "Brown headed dog"
    
    def __init__(self, name):
        self.name =name
    def bark(self):
        print(f'{self.name}')
# print(Dog.species)

dog1 = Dog('Jack')
dog1.bark()
print(dog1.species)