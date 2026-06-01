from traffic.models import Inflation, FuelPrice
from decimal import Decimal


class InflationService:

    @staticmethod
    def get_cumulative_index() -> dict:
        """
        Zwraca słownik {"YYYY-MM": cumulative_index} gdzie cumulative_index
        to skumulowany indeks CPI względem najwcześniejszego dostępnego miesiąca.
        Przykład: {"2024-01": 1.0, "2024-02": 1.003, "2024-03": 1.007, ...}
        """
        records = Inflation.objects.order_by("year", "month")
        if not records.exists():
            return {}

        cumulative = {}
        index = 1.0

        for r in records:
            index *= r.value / 100
            key = f"{r.year}-{r.month:02d}"
            cumulative[key] = round(index, 6)

        return cumulative

    @staticmethod
    def deflate_price(nominal_price: float, date_key: str, cumulative_index: dict) -> float | None:
        """
        Przelicza cenę nominalną na cenę realną (w wartości ostatniego okresu).
        date_key: "YYYY-MM"
        """
        if date_key not in cumulative_index:
            return None

        latest_index = max(cumulative_index.values())
        price_index = cumulative_index[date_key]

        return round(nominal_price * (latest_index / price_index), 4)
