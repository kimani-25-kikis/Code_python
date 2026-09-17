import sqlite3, string, secrets, sys

DB = "shortener.db"
ALPHABET = string.ascii_letters + string.digits

def init():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS links (code TEXT PRIMARY KEY, url TEXT)")
    con.commit()
    return con

def shorten(con, url):
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        try:
            con.execute("INSERT INTO links VALUES (?, ?)", (code, url))
            con.commit()
            return code
        except sqlite3.IntegrityError:
            continue

def resolve(con, code):
    row = con.execute("SELECT url FROM links WHERE code = ?", (code,)).fetchone()
    return row[0] if row else None

def listing(con):
    for code, url in con.execute("SELECT code, url FROM links ORDER BY rowid DESC LIMIT 20"):
        print(f"  {code}  ->  {url}")

if __name__ == "__main__":
    con = init()
    if len(sys.argv) < 2:
        print("Usage: python shortener.py <url> | -l | -r <code>")
        sys.exit()
    arg = sys.argv[1]
    if arg == "-l":
        listing(con)
    elif arg == "-r":
        url = resolve(con, sys.argv[2])
        print(url or "Not found.")
    else:
        code = shorten(con, arg)
        print(f"Short code: {code}")