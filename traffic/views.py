import json
import re
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from xml.etree.ElementTree import fromstring

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash, logout
from django import forms as django_forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg
from django.db.models.functions import TruncMonth
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from scipy import stats

from Integracje.services.fuel_price_scraper import FuelPriceScraper
from Integracje.services.police_stat_scraper import PoliceStatScraper
from Integracje.services.police_pdf_parser import PolicePDFParser
from Integracje.services.sync_database import SyncDatabase
from Integracje.services.inflation_api import InflationAPIGUS
from traffic.models import AccidentRecord, FuelPrice, Inflation

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


def used_data(request):
    return render(request, 'web/used_data.html')


def about(request):
    return render(request, 'web/about.html')


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
        .annotate(avg_diesel=Avg("diesel_price"), avg_petrol=Avg("petrol_price"))
        .order_by("month_start")
    )
    fuel_map = {
        entry["month_start"].strftime("%Y-%m"): {
            "avg_diesel": round(float(entry["avg_diesel"]), 2),
            "avg_petrol": round(float(entry["avg_petrol"]), 2),
        }
        for entry in fuel_by_month
    }

    by_month = {m: [] for m in range(1, 13)}
    for r in accidents:
        label = f"{r['year']}-{r['month']:02d}"
        fuel = fuel_map.get(label, {})
        by_month[r["month"]].append({
            "year": r["year"],
            "accidents_total": r["accidents_total"],
            "avg_diesel": fuel.get("avg_diesel"),
            "avg_petrol": fuel.get("avg_petrol"),
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

        if len(paired) < 3:  # za mało danych, żeby liczyć korelację
            continue

        accident_vals = [p[0] for p in paired]
        fuel_vals = [p[1] for p in paired]

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


def inflation_data(request):
    # np. /gus/inflation/?start=2024&end=2025
    try:
        start = int(request.GET.get('start', 2024))
        end = int(request.GET.get('end', 2024))
    except ValueError:
        start = 2024
        end = 2024

    if start > end:
        start, end = end, start

    # OCHRONA PRZED TIMEOUTEM: Blokujemy zapytania większe niż 2 lata
    if end - start > 2:
        return JsonResponse({
            "error": "Zbyt duży zakres lat. Maksymalny dozwolony zakres dla pobierania danych na żywo to 2 lata."
        }, status=400)

    service = InflationAPIGUS()
    results = service.fetch_inflation_data(start_year=start, end_year=end)

    # Zapis do bazy danych:
    for item in results:
        Inflation.objects.update_or_create(
            year=item['year'],
            month=item['month'],
            defaults={'value': item['value']}
        )

    return JsonResponse({"data": results}, json_dumps_params={'ensure_ascii': False})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Automatyczne logowanie po rejestracji:
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required(login_url='login')
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Twój profil został pomyślnie zaktualizowany!")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'user/profile.html', {'form': form})


class ProfileUpdateForm(django_forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise django_forms.ValidationError("Użytkownik o takim loginie już istnieje.")
        return username


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Utrzymuje sesję zalogowanego użytkownika po zmianie hasła:
            update_session_auth_hash(request, user)
            messages.success(request, 'Twoje hasło zostało pomyślnie zmienione!')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'user/passwd_change.html', {'form': form})


def log_out(request):
    if request.method == 'POST':
        logout(request)
    return redirect('dashboard')


def export_json(request):
    accident_records = list(AccidentRecord.objects.values(
        "year", "month", "accidents_total", "accidents_pct",
        "fatalities_total", "fatalities_pct", "injured_total", "injured_pct"
    ))
    fuel_prices = [
        {
            "date": str(r["date"]),
            "diesel_price": str(r["diesel_price"]),
            "petrol_price": str(r["petrol_price"]),
        }
        for r in FuelPrice.objects.values("date", "diesel_price", "petrol_price")
    ]
    inflation = list(Inflation.objects.values("year", "month", "value"))

    payload = {
        "exported_at": str(date.today()),
        "accident_records": accident_records,
        "fuel_prices": fuel_prices,
        "inflation": inflation,
    }

    response = HttpResponse(
        json.dumps(payload, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = 'attachment; filename="export.json"'
    return response


def export_xml(request):
    root = Element("export", exported_at=str(date.today()))

    # AccidentRecord
    accidents_el = SubElement(root, "accident_records")
    for r in AccidentRecord.objects.all():
        SubElement(accidents_el, "record",
                   year=str(r.year),
                   month=str(r.month),
                   accidents_total=str(r.accidents_total),
                   accidents_pct=str(r.accidents_pct),
                   fatalities_total=str(r.fatalities_total),
                   fatalities_pct=str(r.fatalities_pct),
                   injured_total=str(r.injured_total),
                   injured_pct=str(r.injured_pct),
                   )

    # FuelPrice
    fuel_el = SubElement(root, "fuel_prices")
    for r in FuelPrice.objects.all():
        SubElement(fuel_el, "record",
                   date=str(r.date),
                   diesel_price=str(r.diesel_price),
                   petrol_price=str(r.petrol_price),
                   )

    # Inflation
    inflation_el = SubElement(root, "inflation")
    for r in Inflation.objects.all():
        SubElement(inflation_el, "record",
                   year=str(r.year),
                   month=str(r.month),
                   value=str(r.value),
                   )

    pretty_xml = parseString(tostring(root, encoding="unicode")).toprettyxml(indent="  ")

    response = HttpResponse(pretty_xml, content_type="application/xml; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="export.xml"'
    return response


def import_json(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        payload = json.loads(request.FILES["file"].read().decode("utf-8"))
    except (KeyError, json.JSONDecodeError) as e:
        return JsonResponse({"error": f"Invalid JSON file: {e}"}, status=400)

    try:
        result = _import_payload(payload)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "ok", **result})


def import_xml(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        root = fromstring(request.FILES["file"].read().decode("utf-8"))
    except (KeyError, Exception) as e:
        return JsonResponse({"error": f"Invalid XML file: {e}"}, status=400)

    payload = {
        "accident_records": [
            {k: v for k, v in record.attrib.items()}
            for record in root.findall("accident_records/record")
        ],
        "fuel_prices": [
            {k: v for k, v in record.attrib.items()}
            for record in root.findall("fuel_prices/record")
        ],
        "inflation": [
            {k: v for k, v in record.attrib.items()}
            for record in root.findall("inflation/record")
        ],
    }

    try:
        result = _import_payload(payload)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "ok", **result})


@transaction.atomic
def _import_payload(payload: dict) -> dict:
    accidents_created = accidents_skipped = 0
    fuel_created = fuel_skipped = 0
    inflation_created = inflation_skipped = 0

    for r in payload.get("accident_records", []):
        _, created = AccidentRecord.objects.get_or_create(
            year=int(r["year"]),
            month=int(r["month"]),
            defaults={
                "accidents_total": int(r["accidents_total"]),
                "accidents_pct": float(r["accidents_pct"]),
                "fatalities_total": int(r["fatalities_total"]),
                "fatalities_pct": float(r["fatalities_pct"]),
                "injured_total": int(r["injured_total"]),
                "injured_pct": float(r["injured_pct"]),
            }
        )
        if created:
            accidents_created += 1
        else:
            accidents_skipped += 1

    for r in payload.get("fuel_prices", []):
        _, created = FuelPrice.objects.get_or_create(
            date=r["date"],
            defaults={
                "diesel_price": Decimal(r["diesel_price"]),
                "petrol_price": Decimal(r["petrol_price"]),
            }
        )
        if created:
            fuel_created += 1
        else:
            fuel_skipped += 1

    for r in payload.get("inflation", []):
        _, created = Inflation.objects.get_or_create(
            year=int(r["year"]),
            month=int(r["month"]),
            defaults={"value": float(r["value"])}
        )
        if created:
            inflation_created += 1
        else:
            inflation_skipped += 1

    return {
        "created": accidents_created + fuel_created + inflation_created,
        "skipped": accidents_skipped + fuel_skipped + inflation_skipped,
        "accidents": {"created": accidents_created, "skipped": accidents_skipped},
        "fuel": {"created": fuel_created, "skipped": fuel_skipped},
        "inflation": {"created": inflation_created, "skipped": inflation_skipped},
    }


def clear_database(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    AccidentRecord.objects.all().delete()
    FuelPrice.objects.all().delete()
    Inflation.objects.all().delete()

    return JsonResponse({"status": "ok"})
