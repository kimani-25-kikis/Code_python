class Walker:
    def walk(self):
        return 'I can walk on land'
class Swimmer:
    def swim(self):
        return 'I can swim on water'
class Amphibbian(Walker, Swimmer):
    def __init__(self, name):
        self.name = name
    def introduction(self):
        return f"I'm {self.name} the frog. {self.walk()} and {self.swim()}."
frog = Amphibbian("Freddy")

print(frog.introduction())