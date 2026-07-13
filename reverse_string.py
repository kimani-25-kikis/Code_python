class Reverse:
    def __init__(self, string:str):
        self.string = string
    def reverse_string(self):
        return self.string[::-1]
str= Reverse('Joshua')
print(str.reverse_string())