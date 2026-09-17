import secrets
import string

def generate(length=16, symbols=True):
    chars = string.ascii_letters + string.digits
    if symbols:
        chars += "!@#$%^&*()-_=+"
    return "".join(secrets.choice(chars) for _ in range(length))

def strength(pw):
    score = 0
    if len(pw) >= 12: score += 1
    if any(c.islower() for c in pw): score += 1
    if any(c.isupper() for c in pw): score += 1
    if any(c.isdigit() for c in pw): score += 1
    if any(c in "!@#$%^&*()-_=+" for c in pw): score += 1
    return ["Very Weak","Weak","Okay","Good","Strong","Very Strong"][score]

if __name__ == "__main__":
    n = int(input("Length (default 16): ") or 16)
    pw = generate(n)
    print(f"\nPassword: {pw}")
    print(f"Strength: {strength(pw)}")