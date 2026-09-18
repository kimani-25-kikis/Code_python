import time
from plyer import notification

WORK = 25 * 60
BREAK = 5 * 60

def notify(title, msg):
    notification.notify(title=title, message=msg, timeout=10)

def countdown(seconds, label):
    while seconds:
        m, s = divmod(seconds, 60)
        print(f"\r{label}: {m:02d}:{s:02d}", end="")
        time.sleep(1)
        seconds -= 1
    print()

def main():
    cycle = 0
    while True:
        cycle += 1
        notify("Pomodoro", f"Cycle {cycle}: Start working!")
        countdown(WORK, "Work")
        notify("Pomodoro", "Break time!")
        countdown(BREAK, "Break")

if __name__ == "__main__":
    main()