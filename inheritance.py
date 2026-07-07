class Animal:
    def __init__(self, name):
        self.name = name
    def sound(self):
        return f'{self.name} makes a sound'
class Dog(Animal):
    bark = 'woof! woof!! woof!!!'
    
    # def sound(self):
    #     return f'{self.name} barks {self.bark}'
    
    def sound(self):
        base = super().sound()
        return f'{base}, then {self.name} barks {self.bark}'
jack = Dog('Jack')

print(jack.sound())
# print(jack.bark)