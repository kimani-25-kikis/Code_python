import json, os
from datetime import date

FILE = "expenses.json"

def load():
    return json.load(open(FILE)) if os.path.exists(FILE) else []

def save(data):
    json.dump(data, open(FILE, "w"), indent=2)

def add(amount, note):
    data = load()
    data.append({"date": str(date.today()), "amount": amount, "note": note})
    save(data)
    print("Added.")

def summary():
    data = load()
    total = sum(e["amount"] for e in data)
    print(f"\n{len(data)} entries | Total: ${total:.2f}")
    for e in data[-5:]:
        print(f"  {e['date']}  ${e['amount']:.2f}  {e['note']}")

if __name__ == "__main__":
    while True:
        print("\n1) Add  2) Summary  3) Quit")
        c = input("> ").strip()
        if c == "1":
            add(float(input("Amount: ")), input("Note: "))
        elif c == "2":
            summary()
        elif c == "3":
            break