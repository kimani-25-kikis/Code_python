# class Person: 
#     def __init__(self, name, age): 
#         self.name = name 
#         self.age = age 

# person = Person('John Doe', 30) 
 
# print(getattr(person, 'name'))  
# print(getattr(person, 'age'))  
# print(getattr(person, 'city', 'Embu'))

class Person: 
    def __init__(self, name, age): 
        self.name = name 
        self.age = age 

person = Person('John Doe', 30)

attr_name = input('Enter the attribute you want to see: ')
print(getattr(person, attr_name, 'Attribute not found'))