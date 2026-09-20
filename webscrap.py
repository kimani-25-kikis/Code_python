import requests
from bs4 import BeautifulSoup

def get_weather(city):
    url = f"https://www.timeanddate.com/weather/{city}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    temperature = soup.select_one("div.bk-focus__qlook .h2")
    condition = soup.select_one("div.bk-focus__qlook p")
    location = soup.select_one("h1")

    return {
        "location": location.get_text(strip=True) if location else None,
        "temperature": temperature.get_text(strip=True) if temperature else None,
        "condition": condition.get_text(strip=True) if condition else None,
    }

if __name__ == "__main__":
    city = "kenya/nairobi"
    weather = get_weather(city)
    for key, value in weather.items():
        print(f"{key}: {value}")