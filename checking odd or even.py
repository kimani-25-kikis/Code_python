class Check:
    def __init__(self,number):
        self.number = number
    
    def check_even_or_odd(self):
        if self.number % 2 == 0:
            return 'Even'
        else:
            return 'Odd'
test = Check(5)
print(test.check_even_or_odd())