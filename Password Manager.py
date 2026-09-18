import json
import os
from cryptography.fernet import Fernet

KEY_FILE = "key.key"
DATA_FILE = "vault.json"

def get_key():
    if not os.path.exists(KEY_FILE):
        with open(KEY_FILE, "wb") as f:
            f.write(Fernet.generate_key())
    with open(KEY_FILE, "rb") as f:
        return f.read()

def load_vault():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "rb") as f:
        return json.loads(Fernet(get_key()).decrypt(f.read()).decode())

def save_vault(vault):
    with open(DATA_FILE, "wb") as f:
        f.write(Fernet(get_key()).encrypt(json.dumps(vault).encode()))

def main():
    vault = load_vault()
    while True:
        cmd = input("add/get/list/del/quit> ").strip()
        if cmd == "add":
            s = input("service: ")
            u = input("user: ")
            p = input("pass: ")
            vault[s] = {"user": u, "pass": p}
            save_vault(vault)
        elif cmd == "get":
            s = input("service: ")
            print(vault.get(s, "not found"))
        elif cmd == "list":
            print(list(vault.keys()))
        elif cmd == "del":
            vault.pop(input("service: "), None)
            save_vault(vault)
        elif cmd == "quit":
            break

if __name__ == "__main__":
    main()