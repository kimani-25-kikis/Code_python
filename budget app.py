class Category:
    def __init__(self, name):
        self.name = name
        self.ledger = []

    def deposit(self, amount, description=""):
        self.ledger.append({
            "amount": amount,
            "description": description
        })

    def withdraw(self, amount, description=""):
        if self.check_funds(amount):
            self.ledger.append({
                "amount": -amount,
                "description": description
            })
            return True
        return False

    def get_balance(self):
        return sum(item["amount"] for item in self.ledger)

    def transfer(self, amount, category):
        if self.check_funds(amount):
            self.withdraw(amount, f"Transfer to {category.name}")
            category.deposit(amount, f"Transfer from {self.name}")
            return True
        return False

    def check_funds(self, amount):
        return amount <= self.get_balance()

    def __str__(self):
        title = self.name.center(30, "*") + "\n"
        items = ""

        for entry in self.ledger:
            description = entry["description"][:23]
            amount = f"{entry['amount']:.2f}"[:7]
            items += f"{description:<23}{amount:>7}\n"

        total = f"Total: {self.get_balance():.2f}"
        return title + items + total


def create_spend_chart(categories):
    withdrawals = []

    for category in categories:
        spent = 0
        for entry in category.ledger:
            if entry["amount"] < 0:
                spent += -entry["amount"]
        withdrawals.append(spent)

    total_spent = sum(withdrawals)

    percentages = [
        int((spent / total_spent) * 100) // 10 * 10
        if total_spent > 0 else 0
        for spent in withdrawals
    ]

    chart = "Percentage spent by category\n"

    for percent in range(100, -1, -10):
        chart += f"{percent:>3}|"
        for value in percentages:
            if value >= percent:
                chart += " o "
            else:
                chart += "   "
        chart += " \n"

    chart += "    " + "-" * (len(categories) * 3 + 1) + "\n"

    max_length = max(len(category.name) for category in categories)

    for i in range(max_length):
        chart += "     "
        for category in categories:
            if i < len(category.name):
                chart += category.name[i] + "  "
            else:
                chart += "   "
        if i != max_length - 1:
            chart += "\n"

    return chart


# Example usage
food = Category("Food")
food.deposit(1000, "initial deposit")
food.withdraw(10.15, "groceries")
food.withdraw(15.89, "restaurant and more food for dessert")

clothing = Category("Clothing")
food.transfer(50, clothing)

auto = Category("Auto")
auto.deposit(1000)
auto.withdraw(200)

print(food)
print()
print(create_spend_chart([food, clothing, auto]))