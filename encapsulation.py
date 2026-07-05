class Wallet:
   def __init__(self, balance):
       self.__balance = balance

   def deposit(self, amount):
       if amount > 0:
           self.__balance += amount

   def withdraw(self, amount):
       if 0 < amount <= self.__balance:
           self.__balance -= amount
  
   def get_balance(self):
       return self.__balance


acct_one = Wallet(100)
acct_one.deposit(50)
print(acct_one.get_balance()) 

acct_two = Wallet(450)
acct_two.withdraw(28)
print(acct_two.get_balance()) 

acct_two.deposit(150)
print(acct_two.get_balance()) 