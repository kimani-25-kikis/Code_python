import time
import os
import yfinance as yf

TICKERS = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

def fetch():
    data = {}
    for t in TICKERS:
        try:
            info = yf.Ticker(t).fast_info
            data[t] = (info.last_price, info.previous_close)
        except Exception:
            data[t] = (None, None)
    return data

def render(data):
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{'Ticker':<8}{'Price':>12}{'Change':>12}{'%':>10}")
    print("-" * 42)
    for t, (price, prev) in data.items():
        if price and prev:
            change = price - prev
            pct = change / prev * 100
            color = "\033[92m" if change >= 0 else "\033[91m"
            print(f"{t:<8}{price:>12.2f}{color}{change:>+12.2f}{pct:>+9.2f}%\033[0m")
        else:
            print(f"{t:<8}{'N/A':>12}")
    print("\nRefreshing every 15s. Ctrl+C to quit.")

def main():
    while True:
        render(fetch())
        time.sleep(15)

if __name__ == "__main__":
    main()