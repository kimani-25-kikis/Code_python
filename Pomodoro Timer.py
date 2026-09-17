import time

def countdown(minutes, label):
    total = minutes * 60
    while total > 0:
        m, s = divmod(total, 60)
        print(f"\r{label}  {m:02d}:{s:02d}", end="", flush=True)
        time.sleep(1)
        total -= 1
    print(f"\r{label}  Done!{' ' * 10}")
    print("\a", end="")

if __name__ == "__main__":
    work = int(input("Work minutes (25): ") or 25)
    brk  = int(input("Break minutes (5): ") or 5)
    rounds = int(input("Rounds (4): ") or 4)

    for i in range(1, rounds + 1):
        print(f"\n--- Round {i} ---")
        countdown(work, "Focus")
        if i < rounds:
            countdown(brk, "Break ")

    print("\nAll done!")