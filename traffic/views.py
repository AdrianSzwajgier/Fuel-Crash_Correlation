import re
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render
from scipy import stats

from Integracje.services.fuel_price_scraper import FuelPriceScraper
from Integracje.services.police_stat_scraper import PoliceStatScraper
from Integracje.services.police_pdf_parser import PolicePDFParser
from Integracje.services.sync_database import SyncDatabase
from traffic.models import AccidentRecord, FuelPrice


MONTH_NAMES_PL = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
    5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień",
    9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
}


# @login_required
def sync_database(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    year_from, year_to = 2010, 2025
    save_dir = Path(settings.MEDIA_ROOT) / "police-reports"

    scraper = PoliceStatScraper()

    print(f"[INFO] Fetching PDF URLs for years {year_from}–{year_to}...")
    pdf_list = scraper.get_pdf_urls(year_from, year_to)
    print(f"[INFO] Found {len(pdf_list)} reports.")

    print("[INFO] Starting download...")
    results = scraper.download_pdfs(pdf_list, save_dir)

    downloaded = sum(1 for r in results if r["downloaded"])
    skipped = len(results) - downloaded
    print(f"[DONE] Downloaded: {downloaded}, skipped: {skipped}.")

    pdf_files = list(save_dir.glob("*.pdf"))
    print(pdf_files, "###")

    parser = PolicePDFParser()
    all_records = []

    for filepath in sorted(pdf_files):
        year_match = re.search(r"(\d{4})", filepath.stem)
        if not year_match:
            continue
        year = int(year_match.group(1))
        records = parser.parse_pdf(filepath, year)
        all_records.extend(records)

    accidents_result = SyncDatabase.save_records(all_records)
    fuel_scraper = FuelPriceScraper()
    fuel_records = fuel_scraper.fetch_fuel_prices()
    fuel_result = SyncDatabase.save_fuel_prices(fuel_records)

    return JsonResponse({
        "status": "ok",
        "accidents": accidents_result,
        "fuel": fuel_result,
    })


def dashboard(request):
    return render(request, "traffic/dashboard.html")


def chart_data(request):
    # zakres dat z tabeli wypadków
    accidents = AccidentRecord.objects.order_by("year", "month").values(
        "year", "month", "accidents_total"
    )
    if not accidents:
        return JsonResponse({"data": []})

    first = accidents.first()
    last = accidents.last()
    date_from = datetime(first["year"], first["month"], 1).date()
    date_to = datetime(last["year"], last["month"], 1).date()

    # średnia cena paliw per miesiąc, w zakresie dat wypadków
    fuel_by_month = (
        FuelPrice.objects
        .filter(date__gte=date_from, date__lte=date_to)
        .annotate(month_start=TruncMonth("date"))
        .values("month_start")
        .annotate(avg_diesel=Avg("diesel_price"), avg_petrol=Avg("petrol_price"))
        .order_by("month_start")
    )

    fuel_map = {
        entry["month_start"].strftime("%Y-%m"): {
            "diesel": round(float(entry["avg_diesel"]), 2),
            "petrol": round(float(entry["avg_petrol"]), 2),
        }
        for entry in fuel_by_month
    }

    data = []
    for r in accidents:
        label = f"{r['year']}-{r['month']:02d}"
        fuel = fuel_map.get(label, {})
        data.append({
            "label": label,
            "accidents_total": r["accidents_total"],
            "avg_diesel": fuel.get("diesel"),
            "avg_petrol": fuel.get("petrol"),
        })

    return JsonResponse({"data": data})


def chart_data_by_month(request):
    accidents = AccidentRecord.objects.order_by("year", "month").values(
        "year", "month", "accidents_total"
    )
    if not accidents:
        return JsonResponse({"data": {}})

    first = accidents.first()
    last = accidents.last()
    date_from = datetime(first["year"], first["month"], 1).date()
    date_to = datetime(last["year"], last["month"], 1).date()

    fuel_by_month = (
        FuelPrice.objects
        .filter(date__gte=date_from, date__lte=date_to)
        .annotate(month_start=TruncMonth("date"))
        .values("month_start")
        .annotate(avg_diesel=Avg("diesel_price"))
        .order_by("month_start")
    )
    fuel_map = {
        entry["month_start"].strftime("%Y-%m"): round(float(entry["avg_diesel"]), 2)
        for entry in fuel_by_month
    }

    # grupuj po miesiącu
    by_month = {m: [] for m in range(1, 13)}
    for r in accidents:
        label = f"{r['year']}-{r['month']:02d}"
        by_month[r["month"]].append({
            "year": r["year"],
            "accidents_total": r["accidents_total"],
            "avg_diesel": fuel_map.get(label),
        })

    return JsonResponse({"data": by_month})


def correlation_data(request):
    accidents = AccidentRecord.objects.order_by("year", "month").values(
        "year", "month", "accidents_total"
    )
    if not accidents:
        return JsonResponse({"data": []})

    first = accidents.first()
    last = accidents.last()
    date_from = datetime(first["year"], first["month"], 1).date()
    date_to = datetime(last["year"], last["month"], 1).date()

    fuel_by_month = (
        FuelPrice.objects
        .filter(date__gte=date_from, date__lte=date_to)
        .annotate(month_start=TruncMonth("date"))
        .values("month_start")
        .annotate(avg_diesel=Avg("diesel_price"))
        .order_by("month_start")
    )
    fuel_map = {
        entry["month_start"].strftime("%Y-%m"): float(entry["avg_diesel"])
        for entry in fuel_by_month
    }

    results = []
    for month in range(1, 13):
        month_accidents = [
            r for r in accidents if r["month"] == month
        ]

        paired = [
            (r["accidents_total"], fuel_map[f"{r['year']}-{month:02d}"])
            for r in month_accidents
            if f"{r['year']}-{month:02d}" in fuel_map
        ]

        if len(paired) < 3:  # za mało danych żeby liczyć korelację
            continue

        accident_vals = [p[0] for p in paired]
        fuel_vals     = [p[1] for p in paired]

        r, p_value = stats.pearsonr(accident_vals, fuel_vals)

        results.append({
            "month": month,
            "month_name": MONTH_NAMES_PL[month],
            "correlation": round(r, 3),
            "p_value": round(p_value, 4),
            "n": len(paired),
            "significant": str(p_value < 0.05),
        })

    return JsonResponse({"data": results})
