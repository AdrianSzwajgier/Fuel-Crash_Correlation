import requests
import csv
from io import StringIO
from datetime import datetime


class FuelPriceScraper:
    FUEL_CSV_URL = "https://www.ewgt.com.pl/towary/wykresy/paliwa.csv.php"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def fetch_fuel_prices(self) -> list[dict]:
        response = self.session.get(self.FUEL_CSV_URL, timeout=10)
        response.raise_for_status()

        reader = csv.DictReader(StringIO(response.text))
        records = []

        for row in reader:
            try:
                records.append({
                    "date": datetime.strptime(row["Data"].strip(), "%Y-%m-%d").date(),
                    "diesel_price": float(row["Cena ON"].strip()),
                    "petrol_price": float(row["Cena E95"].strip()),
                })
            except (ValueError, KeyError) as e:
                print(f"[WARN] Skipping row {row}: {e}")

        return records


def main():
    scraper = FuelPriceScraper()
    prices = scraper.fetch_fuel_prices()
    print(f"[DONE] Fetched {len(prices)} records.")
    print(prices[:3])


main()