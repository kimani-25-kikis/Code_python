# class Wallet:
#    def __init__(self, balance):
#        self.__balance = balance

#    def deposit(self, amount):
#        if amount > 0:
#            self.__balance += amount

#    def withdraw(self, amount):
#        if 0 < amount <= self.__balance:
#            self.__balance -= amount
  
#    def get_balance(self):
#        return self.__balance


# acct_one = Wallet(100)
# acct_one.deposit(50)
# print(acct_one.get_balance()) # 150

# acct_two = Wallet(450)
# acct_two.withdraw(28)
# print(acct_two.get_balance()) # 422

# acct_two.deposit(150)
# print(acct_two.get_balance()) # 572


class Wallet:
   def __init__(self):
       self.__balance = 0

   def __validate(self, amount):
       if amount < 0:
           raise ValueError('Amount must be positive')

   def deposit(self, amount):
       self.__validate(amount)
       self.__balance += amount

   def withdraw(self, amount):
       self.__validate(amount)
       if amount > self.__balance:
           raise ValueError('Insufficient funds')
       self.__balance -= amount

   def get_balance(self):
       return self.__balance

acct_one = Wallet()
acct_one.deposit(3)
print(acct_one.get_balance()) # 3

acct_one.deposit(50)
print(acct_one.get_balance()) # 53

acct_one.deposit(-4)  
acct_one.withdraw(-8) 
acct_one.withdraw(58)