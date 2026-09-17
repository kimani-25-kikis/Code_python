import json, os
from datetime import date, timedelta

FILE = "habits.json"

def load():
    return json.load(open(FILE)) if os.path.exists(FILE) else {}

def save(data):
    json.dump(data, open(FILE, "w"), indent=2)

def mark(name):
    data = load()
    today = str(date.today())
    data.setdefault(name, [])
    if today in data[name]:
        print(f"'{name}' already done today.")
    else:
        data[name].append(today)
        save(data)
        print(f"Marked '{name}' for {today}.")

def streak(dates):
    if not dates:
        return 0
    days = sorted({date.fromisoformat(d) for d in dates}, reverse=True)
    if days[0] != date.today() and days[0] != date.today() - timedelta(days=1):
        return 0
    count, expected = 1, days[0] - timedelta(days=1)
    for d in days[1:]:
        if d == expected:
            count += 1
            expected -= timedelta(days=1)
        else:
            break
    return count

def show():
    data = load()
    if not data:
        print("No habits yet.")
        return
    print()
    for name, dates in data.items():
        print(f"  {name:<15} streak: {streak(dates)}  total: {len(dates)}")

if __name__ == "__main__":
    while True:
        print("\n1) Mark  2) Show  3) Quit")
        c = input("> ").strip()
        if c == "1":
            mark(input("Habit name: ").strip())
        elif c == "2":
            show()
        elif c == "3":
            break