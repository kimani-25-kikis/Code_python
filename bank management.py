class BankAccount:
    """Base class for a bank account."""

    def __init__(self, account_number, owner, balance=0):
        self.account_number = account_number
        self.owner = owner
        self._balance = balance

    @property
    def balance(self):
        return self._balance

    def deposit(self, amount):
        if amount <= 0:
            print("Deposit amount must be positive.")
            return
        self._balance += amount
        print(f"${amount:.2f} deposited successfully.")

    def withdraw(self, amount):
        if amount <= 0:
            print("Withdrawal amount must be positive.")
            return

        if amount > self._balance:
            print("Insufficient funds.")
            return

        self._balance -= amount
        print(f"${amount:.2f} withdrawn successfully.")

    def display(self):
        print(f"\nAccount Number: {self.account_number}")
        print(f"Owner: {self.owner}")
        print(f"Balance: ${self._balance:.2f}")


class SavingsAccount(BankAccount):
    """Savings account that earns interest."""

    def add_interest(self, rate):
        interest = self._balance * (rate / 100)
        self._balance += interest
        print(f"Interest of ${interest:.2f} added.")


class CurrentAccount(BankAccount):
    """Current account with an overdraft limit."""

    def __init__(self, account_number, owner, balance=0, overdraft=200):
        super().__init__(account_number, owner, balance)
        self.overdraft = overdraft

    def withdraw(self, amount):
        if amount <= 0:
            print("Withdrawal amount must be positive.")
            return

        if amount > self._balance + self.overdraft:
            print("Overdraft limit exceeded.")
            return

        self._balance -= amount
        print(f"${amount:.2f} withdrawn successfully.")


class Bank:
    """Simple bank system."""

    def __init__(self):
        self.accounts = []

    def add_account(self, account):
        self.accounts.append(account)

    def find_account(self, account_number):
        for account in self.accounts:
            if account.account_number == account_number:
                return account
        return None

    def list_accounts(self):
        if not self.accounts:
            print("No accounts found.")
            return

        for account in self.accounts:
            account.display()


# ----------------------------
# Main Program
# ----------------------------

bank = Bank()

while True:
    print("\n===== BANK MANAGEMENT SYSTEM =====")
    print("1. Create Savings Account")
    print("2. Create Current Account")
    print("3. Deposit")
    print("4. Withdraw")
    print("5. Display Account")
    print("6. Add Interest")
    print("7. List All Accounts")
    print("8. Exit")

    choice = input("Choose an option: ")

    if choice == "1":
        number = input("Account Number: ")
        owner = input("Owner Name: ")
        balance = float(input("Initial Balance: "))
        bank.add_account(SavingsAccount(number, owner, balance))
        print("Savings account created.")

    elif choice == "2":
        number = input("Account Number: ")
        owner = input("Owner Name: ")
        balance = float(input("Initial Balance: "))
        bank.add_account(CurrentAccount(number, owner, balance))
        print("Current account created.")

    elif choice == "3":
        number = input("Account Number: ")
        account = bank.find_account(number)

        if account:
            amount = float(input("Deposit Amount: "))
            account.deposit(amount)
        else:
            print("Account not found.")

    elif choice == "4":
        number = input("Account Number: ")
        account = bank.find_account(number)

        if account:
            amount = float(input("Withdrawal Amount: "))
            account.withdraw(amount)
        else:
            print("Account not found.")

    elif choice == "5":
        number = input("Account Number: ")
        account = bank.find_account(number)

        if account:
            account.display()
        else:
            print("Account not found.")

    elif choice == "6":
        number = input("Account Number: ")
        account = bank.find_account(number)

        if isinstance(account, SavingsAccount):
            rate = float(input("Interest Rate (%): "))
            account.add_interest(rate)
        else:
            print("Interest is only available for Savings Accounts.")

    elif choice == "7":
        bank.list_accounts()

    elif choice == "8":
        print("Thank you for using the Bank Management System!")
        break

    else:
        print("Invalid option. Please try again.")