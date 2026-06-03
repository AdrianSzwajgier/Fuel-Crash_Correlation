import time
import requests


class InflationAPIGUS:
    BASE_URL = (
        "https://api-dbw.stat.gov.pl/api/1.1.0/variable/variable-data-section"
    )
    ID_ZMIENNA = "305"
    ID_PRZEKROJ = "736"

    MONTHS_MAPPING = {
        1: 247,
        2: 248,
        3: 249,
        4: 250,
        5: 251,
        6: 252,
        7: 253,
        8: 254,
        9: 255,
        10: 256,
        11: 257,
        12: 258,
    }

    def fetch_inflation_data(self, start_year=2010, end_year=2025):
        results = []

        for year in range(start_year, end_year + 1):
            for month_name, month_id in self.MONTHS_MAPPING.items():
                params = {
                    "id-zmienna": self.ID_ZMIENNA,
                    "id-przekroj": self.ID_PRZEKROJ,
                    "id-rok": year,
                    "id-okres": month_id,
                    "ile-na-stronie": 50,
                    "numer-strony": 0,
                    "lang": "pl",
                }

                try:
                    response = requests.get(
                        self.BASE_URL, params=params, timeout=10
                    )
                    response.raise_for_status()
                    dane_json = response.json()

                    value = None
                    if "data" in dane_json and len(dane_json["data"]) > 0:
                        value = dane_json["data"][0].get("wartosc")

                    results.append(
                        {
                            "year": year,
                            "month": month_name,
                            "value": value,
                        }
                    )
                    print(f"[INFO] Fetched inflation data: year - {year}, month - {month_name}, value: {value}")

                except requests.RequestException as e:
                    print(f"Błąd pobierania danych o inflacji z API GUS dla {year} - {month_name}: {e}")
                    results.append(
                        {"year": year, "month": month_name, "value": None}
                    )

                # Limit API GUS:
                time.sleep(0.2)

        return results
