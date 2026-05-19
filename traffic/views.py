import re
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render

from Integracje.services.fuel_price_scraper import FuelPriceScraper
from Integracje.services.police_stat_scraper import main
from Integracje.services.police_pdf_parser import PolicePDFParser
from Integracje.services.sync_database import SyncDatabase
from traffic.models import AccidentRecord, FuelPrice


# @login_required
def sync_database(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    save_dir = Path(settings.MEDIA_ROOT) / "police-reports"
    main(save_dir)
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