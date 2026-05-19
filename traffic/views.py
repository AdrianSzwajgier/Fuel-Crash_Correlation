from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from pathlib import Path

from django.shortcuts import render

from Integracje.services.police_stat_scraper import main
from Integracje.services.police_pdf_parser import PolicePDFParser
from Integracje.services.sync_database import SyncDatabase
import re

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

    result = SyncDatabase.save_records(all_records)
    return JsonResponse({"status": "ok", **result})


def dashboard(request):
    return render(request, "traffic/dashboard.html")